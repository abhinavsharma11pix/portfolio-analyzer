import logging
from typing import List, Dict, Optional
from app.data.price_engine import fetch_prices_parallel
from app.core.scheduler import update_tracked_symbols

logger = logging.getLogger(__name__)


def _is_us_stock(symbol: str) -> bool:
    return not symbol.endswith(".NS") and not symbol.endswith(".BO")


def get_currency(symbol: str) -> str:
    return "USD" if _is_us_stock(symbol) else "INR"


def enrich_portfolio(holdings: List[Dict]) -> Dict:
    """Enrich holdings with live prices using parallel fetching."""
    symbols = [h["symbol"] for h in holdings]

    # Update scheduler
    try:
        update_tracked_symbols(symbols)
    except Exception:
        pass

    # Fetch all prices in parallel — returns {symbol: {price, source, currency, stale}}
    price_data = fetch_prices_parallel(symbols)

    enriched = []
    total_invested_inr = 0.0
    total_current_inr  = 0.0
    total_invested_usd = 0.0
    total_current_usd  = 0.0

    for holding in holdings:
        symbol    = holding["symbol"]
        qty       = float(holding["quantity"])
        avg_price = float(holding["avg_buy_price"])
        currency  = get_currency(symbol)

        # ✅ Extract just the price float from the rich dict
        raw = price_data.get(symbol, {})
        if isinstance(raw, dict):
            current_price = raw.get("price")
        else:
            current_price = raw  # fallback if plain float

        # Ensure it's a valid number
        if current_price is not None:
            try:
                current_price = float(current_price)
            except (TypeError, ValueError):
                current_price = None

        invested = round(qty * avg_price, 2)

        if current_price and current_price > 0:
            current_value = round(qty * current_price, 2)
            pnl           = round(current_value - invested, 2)
            pnl_pct       = round((pnl / invested) * 100, 2) if invested else 0
        else:
            current_value = None
            pnl           = None
            pnl_pct       = None

        if currency == "INR":
            total_invested_inr += invested
            total_current_inr  += current_value or invested
        else:
            total_invested_usd += invested
            total_current_usd  += current_value or invested

        enriched.append({
            **holding,
            "symbol":        symbol,
            "current_price": current_price,
            "currency":      currency,
            "invested_value": invested,
            "current_value": current_value,
            "pnl":           pnl,
            "pnl_pct":       pnl_pct,
        })

    total_pnl_inr     = round(total_current_inr - total_invested_inr, 2)
    total_pnl_usd     = round(total_current_usd - total_invested_usd, 2)
    total_pnl_pct_inr = round((total_pnl_inr / total_invested_inr * 100), 2) if total_invested_inr else 0
    total_pnl_pct_usd = round((total_pnl_usd / total_invested_usd * 100), 2) if total_invested_usd else 0

    return {
        "holdings": enriched,
        "summary": {
            "inr": {
                "total_invested":      round(total_invested_inr, 2),
                "total_current_value": round(total_current_inr, 2),
                "total_pnl":           total_pnl_inr,
                "total_pnl_pct":       total_pnl_pct_inr,
            },
            "usd": {
                "total_invested":      round(total_invested_usd, 2),
                "total_current_value": round(total_current_usd, 2),
                "total_pnl":           total_pnl_usd,
                "total_pnl_pct":       total_pnl_pct_usd,
            },
        },
    }