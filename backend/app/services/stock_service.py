import logging
from typing import List, Dict, Optional
from app.market_data.price_engine import fetch_prices_parallel
from app.cache.symbol_cache import is_delisted, get_currency

logger = logging.getLogger(__name__)


def _safe_float(v, default: float = 0.0) -> float:
    try:
        r = float(v)
        return r if r == r else default
    except (TypeError, ValueError):
        return default


def enrich_portfolio(holdings: List[Dict]) -> Dict:
    if not holdings:
        return {"holdings": [], "summary": _empty_summary()}

    symbols    = [h["symbol"] for h in holdings]
    price_data = fetch_prices_parallel(symbols)

    enriched = []
    totals   = {
        "INR": {"invested": 0.0, "current": 0.0},
        "USD": {"invested": 0.0, "current": 0.0},
    }

    for h in holdings:
        sym       = h["symbol"]
        qty       = _safe_float(h.get("quantity"), 0)
        avg_price = _safe_float(h.get("avg_buy_price"), 0)
        currency  = get_currency(sym)

        raw   = price_data.get(sym, {})
        price = _safe_float(raw.get("price") if isinstance(raw, dict) else raw)
        inv   = round(qty * avg_price, 2)

        if price > 0:
            cur_val = round(qty * price, 2)
            pnl     = round(cur_val - inv, 2)
            pnl_pct = round((pnl / inv) * 100, 2) if inv else 0
        else:
            cur_val = None
            pnl     = None
            pnl_pct = None

        totals[currency]["invested"] += inv
        totals[currency]["current"]  += cur_val or inv

        from app.cache.store import set as cache_set, TTL_PRICE
        if price:
            cache_set(f"price:{sym}", price, TTL_PRICE)

        enriched.append({
            **h,
            "symbol":         sym,
            "current_price":  price or None,
            "currency":       currency,
            "invested_value": inv,
            "current_value":  cur_val,
            "pnl":            pnl,
            "pnl_pct":        pnl_pct,
        })

    def _summary(t: dict) -> dict:
        inv = t["invested"]
        cur = t["current"]
        p   = round(cur - inv, 2)
        pct = round((p / inv * 100), 2) if inv else 0
        return {
            "total_invested":      round(inv, 2),
            "total_current_value": round(cur, 2),
            "total_pnl":           p,
            "total_pnl_pct":       pct,
        }

    return {
        "holdings": enriched,
        "summary": {
            "inr": _summary(totals["INR"]),
            "usd": _summary(totals["USD"]),
        },
    }


def _empty_summary() -> dict:
    z = {"total_invested": 0, "total_current_value": 0, "total_pnl": 0, "total_pnl_pct": 0}
    return {"inr": z, "usd": z}