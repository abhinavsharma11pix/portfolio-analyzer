import logging
import yfinance as yf
import pandas as pd
from typing import List, Dict

logger = logging.getLogger(__name__)

# Simple in-memory cache {symbol: (price, timestamp)}
_price_cache: Dict[str, tuple] = {}
CACHE_TTL_SECONDS = 300  # 5 minutes


def _is_us_stock(symbol: str) -> bool:
    return not symbol.endswith(".NS") and not symbol.endswith(".BO")


def fetch_stock_prices(symbols: List[str]) -> Dict[str, float]:
    """Fetch current prices with in-memory caching."""
    import time
    now = time.time()
    prices = {}
    to_fetch = []

    for symbol in symbols:
        cached = _price_cache.get(symbol)
        if cached and (now - cached[1]) < CACHE_TTL_SECONDS:
            prices[symbol] = cached[0]
        else:
            to_fetch.append(symbol)

    for symbol in to_fetch:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.fast_info
            price = round(float(info.last_price), 2)
            prices[symbol] = price
            _price_cache[symbol] = (price, now)
        except Exception as e:
            logger.warning(f"Could not fetch price for {symbol}: {e}")
            prices[symbol] = None

    return prices


def get_currency(symbol: str) -> str:
    return "USD" if _is_us_stock(symbol) else "INR"


def enrich_portfolio(holdings: List[Dict]) -> Dict:
    """Add live prices and calculate P&L. Keeps currencies separate in summary."""
    symbols = [h["symbol"] for h in holdings]
    prices = fetch_stock_prices(symbols)

    enriched = []
    total_invested_inr = 0.0
    total_current_inr = 0.0
    total_invested_usd = 0.0
    total_current_usd = 0.0

    for holding in holdings:
        symbol = holding["symbol"]
        qty = float(holding["quantity"])
        avg_price = float(holding["avg_buy_price"])
        current_price = prices.get(symbol)
        currency = get_currency(symbol)

        invested = round(qty * avg_price, 2)

        if current_price and current_price > 0:
            current_value = round(qty * current_price, 2)
            pnl = round(current_value - invested, 2)
            pnl_pct = round((pnl / invested) * 100, 2) if invested else 0
        else:
            current_value = None
            pnl = None
            pnl_pct = None

        # Separate currency tracking
        if currency == "INR":
            total_invested_inr += invested
            total_current_inr += current_value or invested
        else:
            total_invested_usd += invested
            total_current_usd += current_value or invested

        enriched.append({
            **holding,
            "symbol": symbol,
            "current_price": current_price,
            "currency": currency,
            "invested_value": invested,
            "current_value": current_value,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
        })

    total_pnl_inr = round(total_current_inr - total_invested_inr, 2)
    total_pnl_usd = round(total_current_usd - total_invested_usd, 2)
    total_pnl_pct_inr = round((total_pnl_inr / total_invested_inr * 100), 2) if total_invested_inr else 0
    total_pnl_pct_usd = round((total_pnl_usd / total_invested_usd * 100), 2) if total_invested_usd else 0

    return {
        "holdings": enriched,
        "summary": {
            "inr": {
                "total_invested": round(total_invested_inr, 2),
                "total_current_value": round(total_current_inr, 2),
                "total_pnl": total_pnl_inr,
                "total_pnl_pct": total_pnl_pct_inr,
            },
            "usd": {
                "total_invested": round(total_invested_usd, 2),
                "total_current_value": round(total_current_usd, 2),
                "total_pnl": total_pnl_usd,
                "total_pnl_pct": total_pnl_pct_usd,
            }
        }
    }