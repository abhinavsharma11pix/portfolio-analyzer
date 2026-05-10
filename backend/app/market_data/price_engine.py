"""
Production price engine:
- Per-symbol 7s timeout
- Circuit breaker (stops hammering bad symbols)
- NSE → BSE auto-fallback
- Persistent delisted cache
- Parallel ThreadPoolExecutor
- Single-session yfinance
"""
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple

import yfinance as yf

from app.cache import store as cache
from app.cache.symbol_cache import (
    is_delisted, mark_delisted, mark_valid,
    get_currency, nse_to_bse
)

logger       = logging.getLogger(__name__)
MAX_WORKERS  = 12
FETCH_TIMEOUT = 7


def _is_indian(symbol: str) -> bool:
    return symbol.endswith(".NS") or symbol.endswith(".BO")


def _yf_price(symbol: str) -> Optional[float]:
    """Single yfinance price fetch — fast_info first, history fallback."""
    try:
        t     = yf.Ticker(symbol)
        price = getattr(t.fast_info, "last_price", None)
        if price and float(price) > 0:
            return float(price)
        # Fallback to recent history
        h = t.history(period="5d", timeout=5)
        if not h.empty:
            return float(h["Close"].iloc[-1])
    except Exception:
        pass
    return None


def _fetch_one(symbol: str) -> Tuple[str, Optional[float], str, bool]:
    """
    Returns (symbol_used, price, source, stale).
    Auto-tries BSE if NSE fails for Indian stocks.
    """
    # L1/L2 cache check
    cached = cache.get(f"price:{symbol}", cache.TTL_PRICE)
    if cached is not None:
        return symbol, cached, "cache", False

    # Skip known-delisted
    if is_delisted(symbol):
        return symbol, None, "delisted", True

    currency = get_currency(symbol)
    price    = _yf_price(symbol)

    # BSE fallback for NSE misses
    if not price and symbol.endswith(".NS"):
        bse = nse_to_bse(symbol)
        if not is_delisted(bse):
            price = _yf_price(bse)
            if price:
                logger.info(f"BSE fallback: {symbol} → {bse}")
                symbol   = bse
                currency = "INR"

    if price and price > 0:
        cache.set(f"price:{symbol}", price, cache.TTL_PRICE)
        mark_valid(symbol, "BSE" if symbol.endswith(".BO") else "NSE", currency)
        return symbol, price, "yfinance", False

    # Mark delisted after all sources fail
    mark_delisted(symbol)
    return symbol, None, "unavailable", True


def fetch_prices_parallel(
    symbols: List[str],
    has_active_connections: bool = False,
) -> Dict[str, Dict]:
    """Parallel price fetch with per-symbol timeout."""
    if not symbols:
        return {}

    results:  Dict[str, Dict] = {}
    to_fetch: List[str]       = []

    # Batch cache + quarantine check
    for sym in symbols:
        cached = cache.get(f"price:{sym}", cache.TTL_PRICE)
        if cached is not None:
            results[sym] = {
                "price": cached, "source": "cache",
                "currency": get_currency(sym), "stale": False,
            }
        elif is_delisted(sym):
            results[sym] = {
                "price": None, "source": "delisted",
                "currency": get_currency(sym), "stale": True,
            }
        else:
            to_fetch.append(sym)

    if not to_fetch:
        return results

    logger.info(f"Fetching {len(to_fetch)} prices ({len(results)} cached)")
    t0 = time.monotonic()

    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(to_fetch))) as ex:
        futures = {ex.submit(_fetch_one, sym): sym for sym in to_fetch}
        for future in as_completed(futures, timeout=FETCH_TIMEOUT * 2):
            orig = futures[future]
            try:
                used_sym, price, source, stale = future.result(timeout=FETCH_TIMEOUT)
                results[orig] = {
                    "price":    price,
                    "source":   source,
                    "currency": get_currency(used_sym),
                    "stale":    stale,
                }
            except Exception as e:
                logger.warning(f"Price fetch error {orig}: {e}")
                results[orig] = {
                    "price": None, "source": "error",
                    "currency": get_currency(orig), "stale": True,
                }

    elapsed = round(time.monotonic() - t0, 2)
    fetched = sum(1 for v in results.values() if v.get("price"))
    logger.info(f"Price fetch: {fetched}/{len(symbols)} in {elapsed}s")
    return results