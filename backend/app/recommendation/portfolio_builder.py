"""
Portfolio weight allocation with WHOLE SHARE enforcement.
India rule: only whole number shares can be purchased.

Algorithm:
1. Score and select stocks
2. Fetch real current prices for all candidates
3. Allocate weights (inverse-vol + score blend)
4. Convert weights → whole shares (floor division)
5. Remove stocks where 0 shares affordable
6. Redistribute remaining capital iteratively
7. Return exact: symbol, shares, price_per_share, total_cost
"""
import logging
import numpy as np
import yfinance as yf
from typing import Dict, List, Tuple, Optional
from app.cache import store as cache

logger = logging.getLogger(__name__)


# ── Price fetching ────────────────────────────────────────────

def fetch_prices_for_stocks(symbols: List[str]) -> Dict[str, float]:
    """
    Batch fetch current prices for a list of symbols.
    Returns {symbol: price}. Missing = 0.
    """
    prices: Dict[str, float] = {}
    uncached: List[str]      = []

    # Check cache first
    for sym in symbols:
        key    = f"price_check:{sym}"
        cached = cache.get(key, 3600, disk=True)
        if cached and float(cached) > 0:
            prices[sym] = float(cached)
        else:
            uncached.append(sym)

    if not uncached:
        return prices

    # Batch yfinance download
    try:
        import yfinance as yf
        raw = yf.download(
            uncached, period="5d",
            auto_adjust=True, progress=False,
            timeout=20, threads=True,
        )
        if not raw.empty:
            if len(uncached) == 1:
                col = "Close" if "Close" in raw.columns else raw.columns[0]
                p   = float(raw[col].dropna().iloc[-1])
                if p > 0:
                    prices[uncached[0]] = p
                    cache.set(f"price_check:{uncached[0]}", p, 3600, disk=True)
            else:
                import pandas as pd
                if isinstance(raw.columns, pd.MultiIndex):
                    close = raw["Close"] if "Close" in raw.columns.get_level_values(0) else raw.xs("Close", axis=1, level=1)
                else:
                    close = raw["Close"] if "Close" in raw.columns else raw

                for sym in uncached:
                    if sym in close.columns:
                        series = close[sym].dropna()
                        if not series.empty:
                            p = float(series.iloc[-1])
                            if p > 0:
                                prices[sym]                        = p
                                cache.set(f"price_check:{sym}", p, 3600, disk=True)
    except Exception as e:
        logger.warning(f"Batch price fetch failed: {e}")
        # Individual fallback
        for sym in uncached:
            if sym not in prices:
                try:
                    t = yf.Ticker(sym)
                    p = getattr(t.fast_info, "last_price", None)
                    if not p or p <= 0:
                        hist = t.history(period="5d", timeout=8)
                        p    = float(hist["Close"].iloc[-1]) if not hist.empty else 0
                    if p and p > 0:
                        prices[sym] = float(p)
                        cache.set(f"price_check:{sym}", float(p), 3600, disk=True)
                except Exception:
                    pass

    return prices


# ── Weight allocation ─────────────────────────────────────────

def allocate_weights(
    stocks:     List[Dict],
    max_single: float = 0.25,
    max_sector: float = 0.40,
) -> np.ndarray:
    """Inverse-vol + score blend with concentration limits."""
    n = len(stocks)
    if n == 0:
        return np.array([])

    vols   = np.array([max(1.0, s.get("volatility", 20.0)) for s in stocks])
    scores = np.array([max(1.0, s.get("composite_score", 50.0)) for s in stocks])

    inv_vol    = 1.0 / vols
    score_norm = scores / scores.sum()
    raw        = 0.60 * inv_vol / inv_vol.sum() + 0.40 * score_norm

    raw = np.minimum(raw, max_single)
    raw = raw / raw.sum()

    # Sector cap
    sectors: Dict[str, List[int]] = {}
    for i, s in enumerate(stocks):
        sectors.setdefault(s.get("sector", "Other"), []).append(i)
    for idxs in sectors.values():
        total = raw[idxs].sum()
        if total > max_sector:
            raw[idxs] *= max_sector / total

    return raw / raw.sum()


# ── Whole-share allocation ────────────────────────────────────

def allocate_whole_shares(
    stocks:  List[Dict],
    weights: np.ndarray,
    amount:  float,
    prices:  Dict[str, float],
) -> Tuple[List[Dict], float]:
    """
    Convert weight allocations to whole share counts.

    Algorithm:
    1. Compute target Rs amount per stock
    2. Floor divide by share price → whole shares
    3. Remove stocks with 0 shares (unaffordable)
    4. Calculate actual spend and remaining cash
    5. Redistribute remaining cash to buy more shares
       of existing stocks (largest remainder first)

    Returns (enriched_stocks, total_spent)
    """
    if not stocks:
        return [], 0.0

    # Step 1: Initial whole share allocation
    allocations = []
    for i, stock in enumerate(stocks):
        sym   = stock["symbol"]
        price = prices.get(sym, 0)
        if price <= 0:
            # No price — skip
            allocations.append({
                "stock":  stock,
                "price":  0,
                "shares": 0,
                "weight": float(weights[i]),
            })
            continue

        target_amount = float(weights[i]) * amount
        shares        = int(target_amount / price)   # whole shares only

        allocations.append({
            "stock":     stock,
            "price":     price,
            "shares":    shares,
            "weight":    float(weights[i]),
            "remainder": target_amount - (shares * price),
        })

    # Step 2: Remove unaffordable (0 shares, price > 0)
    affordable = [a for a in allocations if a["shares"] > 0 or a["price"] == 0]
    removed    = [a["stock"]["symbol"] for a in allocations
                  if a["shares"] == 0 and a["price"] > 0]

    if removed:
        logger.info(f"Removed {len(removed)} unaffordable stocks: {removed}")

    if not affordable:
        return [], 0.0

    # Step 3: Calculate total spent and remaining cash
    total_spent    = sum(a["shares"] * a["price"] for a in affordable if a["price"] > 0)
    remaining_cash = amount - total_spent

    # Step 4: Redistribute remaining cash
    # Try to buy 1 more share of the cheapest stocks first
    # Sort affordable stocks by price ascending for remainder distribution
    if remaining_cash > 0:
        buyable = sorted(
            [a for a in affordable if a["price"] > 0],
            key=lambda x: x["price"]
        )
        for a in buyable:
            if remaining_cash <= 0:
                break
            extra_shares = int(remaining_cash / a["price"])
            if extra_shares > 0:
                a["shares"]   += extra_shares
                cost           = extra_shares * a["price"]
                total_spent   += cost
                remaining_cash -= cost

    # Step 5: Recalculate final spent
    total_spent = sum(a["shares"] * a["price"] for a in affordable if a["price"] > 0)

    # Step 6: Enrich stock dicts
    result = []
    for a in affordable:
        if a["shares"] == 0 and a["price"] == 0:
            continue   # skip no-price stocks

        s = dict(a["stock"])
        s["shares_to_buy"]   = a["shares"]
        s["price_per_share"] = round(a["price"], 2)
        s["total_cost"]      = round(a["shares"] * a["price"], 2)
        s["actual_alloc"]    = s["total_cost"]
        result.append(s)

    return result, round(total_spent, 2)


# ── Portfolio metrics ─────────────────────────────────────────

def compute_portfolio_metrics(
    stocks:  List[Dict],
    weights: np.ndarray,
    amount:  float,
) -> Dict:
    if not stocks or len(weights) == 0:
        return {
            "expected_return": 0, "expected_volatility": 0,
            "portfolio_score": 50, "diversification_score": 50,
            "weighted_sharpe": 0, "weighted_sortino": 0,
            "weighted_beta": 1.0, "weighted_drawdown": 0,
            "n_stocks": 0, "n_sectors": 0,
            "score_breakdown": {},
        }

    w = np.array(weights)

    sharpes   = np.array([s.get("sharpe", 0)          for s in stocks])
    sortinos  = np.array([s.get("sortino", 0)          for s in stocks])
    vols      = np.array([s.get("volatility", 20)      for s in stocks])
    moms      = np.array([s.get("momentum_1y", 0)      for s in stocks])
    drawdowns = np.array([s.get("max_drawdown", -20)   for s in stocks])
    betas     = np.array([s.get("beta", 1.0)           for s in stocks])

    w_sharpe  = float(w @ sharpes)
    w_sortino = float(w @ sortinos)
    w_vol     = float(w @ vols)
    w_mom     = float(w @ moms)
    w_dd      = float(w @ drawdowns)
    w_beta    = float(w @ betas)

    n_stocks  = len(stocks)
    n_sectors = len({s.get("sector", "Other") for s in stocks})

    div_factor = max(0.70, 0.95 - 0.03 * min(n_sectors, 8))
    adj_vol    = w_vol * div_factor

    sharpe_pts = min(30, max(0, (w_sharpe + 0.5) / 2.5 * 30))
    mom_pts    = min(25, max(0, (w_mom + 10) / 60 * 25))
    dd_pts     = min(20, max(0, (w_dd + 50) / 50 * 20))
    div_pts    = min(15, (n_sectors / 6) * 15)
    vol_pts    = min(10, max(0, (1 - min(w_vol / 40, 1)) * 10))

    port_score = max(20, min(95, round(sharpe_pts + mom_pts + dd_pts + div_pts + vol_pts)))

    sector_weights: Dict[str, float] = {}
    for s, wi in zip(stocks, w):
        sec = s.get("sector", "Other")
        sector_weights[sec] = sector_weights.get(sec, 0) + float(wi)
    max_sec   = max(sector_weights.values()) if sector_weights else 1.0
    div_score = int(min(100, max(0,
        (n_stocks / 12) * 40 + (n_sectors / 7) * 35 + ((100 - max_sec * 100) * 0.25)
    )))

    return {
        "expected_return":       round(w_mom, 2),
        "expected_volatility":   round(adj_vol, 1),
        "portfolio_score":       port_score,
        "diversification_score": div_score,
        "weighted_sharpe":       round(w_sharpe, 3),
        "weighted_sortino":      round(w_sortino, 3),
        "weighted_beta":         round(w_beta, 3),
        "weighted_drawdown":     round(w_dd, 2),
        "n_stocks":              n_stocks,
        "n_sectors":             n_sectors,
        "score_breakdown": {
            "risk_adjusted_return": round(sharpe_pts, 1),
            "momentum":             round(mom_pts, 1),
            "drawdown_protection":  round(dd_pts, 1),
            "diversification":      round(div_pts, 1),
            "volatility_stability": round(vol_pts, 1),
        },
    }


# ── Main entry ────────────────────────────────────────────────

def build_final_portfolio(
    scored_stocks: List[Dict],
    amount:        float,
    n_stocks:      int,
    profile:       Dict,
) -> Tuple[List[Dict], np.ndarray, Dict]:
    """
    Full pipeline:
    1. Select top N scored stocks
    2. Compute weights
    3. Fetch real prices
    4. Convert to whole shares
    5. Compute portfolio metrics
    """
    from app.recommendation.scorer import select_top_n

    max_sector = profile.get("max_sector", 0.40)
    max_single = profile.get("max_single_stock", 0.25)

    # Select candidates
    selected = select_top_n(scored_stocks, n_stocks * 2, max_sector)  # 2x buffer for removals
    if not selected:
        return [], np.array([]), {}

    # Compute initial weights
    weights = allocate_weights(selected, max_single, max_sector)

    # Fetch real prices for ALL candidates in one batch call
    symbols = [s["symbol"] for s in selected]
    prices  = fetch_prices_for_stocks(symbols)
    logger.info(f"Fetched prices for {len(prices)}/{len(symbols)} stocks")

    # Convert to whole shares — iterative loop
    # We might need to retry if too many stocks get removed
    max_retries  = 3
    final_stocks = []
    total_spent  = 0.0

    for attempt in range(max_retries):
        final_stocks, total_spent = allocate_whole_shares(
            selected[:n_stocks + attempt],
            weights[:n_stocks + attempt] / weights[:n_stocks + attempt].sum(),
            amount,
            prices,
        )
        if len(final_stocks) >= max(3, n_stocks // 2):
            break
        logger.info(f"Retry {attempt+1}: only {len(final_stocks)} affordable stocks")

    if not final_stocks:
        return [], np.array([]), {}

    # Trim to n_stocks
    final_stocks = final_stocks[:n_stocks]

    # Recompute weights from actual costs
    total_cost = sum(s.get("total_cost", 0) for s in final_stocks)
    if total_cost > 0:
        final_weights = np.array([
            s.get("total_cost", 0) / total_cost
            for s in final_stocks
        ])
    else:
        final_weights = np.ones(len(final_stocks)) / len(final_stocks)

    metrics = compute_portfolio_metrics(final_stocks, final_weights, amount)
    metrics["total_invested"] = round(total_spent, 2)
    metrics["uninvested_cash"] = round(amount - total_spent, 2)

    return final_stocks, final_weights, metrics


# Backwards-compatible export
def enforce_affordability(
    stocks:  List[Dict],
    weights: np.ndarray,
    amount:  float,
) -> Tuple:
    """Legacy compatibility — wraps whole-share logic."""
    symbols = [s["symbol"] for s in stocks]
    prices  = fetch_prices_for_stocks(symbols)

    enriched, total_spent = allocate_whole_shares(stocks, weights, amount, prices)
    removed = [s["symbol"] for s in stocks if s["symbol"] not in {e["symbol"] for e in enriched}]

    if not enriched:
        return stocks, weights, removed

    new_weights = np.array([s.get("total_cost", 0) for s in enriched])
    total = new_weights.sum()
    if total > 0:
        new_weights = new_weights / total

    return enriched, new_weights, removed