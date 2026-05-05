import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple

import yfinance as yf

from app.core import cache as price_cache
from app.core.market_calendar import get_refresh_interval
from app.data.nse_scraper import fetch_nse_price
from app.db.repositories import PriceCacheRepository

logger = logging.getLogger(__name__)
price_repo = PriceCacheRepository()


def _is_indian(symbol: str) -> bool:
    return symbol.endswith(".NS") or symbol.endswith(".BO")


def _fetch_yfinance(symbol: str) -> Optional[float]:
    """yfinance with 3 retries."""
    for attempt in range(3):
        try:
            price = float(yf.Ticker(symbol).fast_info.last_price)
            if price > 0:
                return price
        except Exception:
            if attempt < 2:
                time.sleep(0.5)
    return None


def fetch_price(symbol: str) -> Tuple[Optional[float], str]:
    """
    Full 4-layer price fetcher.
    Returns (price, source_used)

    Layer 1: Memory cache
    Layer 2: NSE scraper (Indian only)
    Layer 3: yfinance
    Layer 4: Stale DB value (last known)
    """
    # L1: Memory cache
    cached = price_cache.get_price(symbol)
    if cached:
        return cached, "cache"

    price = None
    source = "unknown"

    # L2: NSE (Indian stocks only)
    if _is_indian(symbol):
        price = fetch_nse_price(symbol)
        if price:
            source = "nse"

    # L3: yfinance fallback
    if not price:
        price = _fetch_yfinance(symbol)
        if price:
            source = "yfinance"

    # L4: Stale DB value
    if not price:
        stale = price_repo.get_price(symbol, max_age_seconds=86400)
        if stale:
            logger.warning(f"Using stale price for {symbol}")
            return stale, "stale"

    # Cache fresh price
    if price:
        currency = "INR" if _is_indian(symbol) else "USD"
        price_cache.set_price(symbol, price, currency)

    return price, source


def fetch_prices_parallel(
    symbols: List[str],
    has_active_connections: bool = False
) -> Dict[str, Dict]:
    """
    Fetch all prices in parallel.
    Returns rich dict: {symbol: {price, source, currency, stale}}
    """
    results: Dict[str, Dict] = {}
    to_fetch = []

    # Separate cached vs stale
    ttl = get_refresh_interval(has_active_connections)
    for symbol in symbols:
        cached = price_cache.get_price(symbol)
        if cached:
            results[symbol] = {
                "price":    cached,
                "source":   "cache",
                "currency": "INR" if _is_indian(symbol) else "USD",
                "stale":    False,
            }
        else:
            to_fetch.append(symbol)

    if not to_fetch:
        return results

    logger.info(
        f"Fetching {len(to_fetch)} prices "
        f"({len(results)} from cache)"
    )

    with ThreadPoolExecutor(
        max_workers=min(10, len(to_fetch))
    ) as executor:
        future_map = {
            executor.submit(fetch_price, sym): sym
            for sym in to_fetch
        }
        for future in as_completed(future_map):
            sym = future_map[future]
            try:
                price, source = future.result(timeout=15)
                results[sym] = {
                    "price":    price,
                    "source":   source,
                    "currency": "INR" if _is_indian(sym) else "USD",
                    "stale":    source == "stale",
                }
            except Exception as e:
                logger.warning(f"Fetch failed {sym}: {e}")
                results[sym] = {
                    "price":    None,
                    "source":   "error",
                    "currency": "INR" if _is_indian(sym) else "USD",
                    "stale":    True,
                }

    return results