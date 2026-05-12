"""
Portfolio weight allocation using inverse-volatility + score weighting.
Computes real expected return, volatility, and portfolio score.
"""
import logging
import numpy as np
import pandas as pd
import yfinance as yf
from typing import Dict, List, Tuple
from app.cache import store as cache

logger = logging.getLogger(__name__)


def allocate_weights(
    stocks:         List[Dict],
    max_single:     float = 0.25,
    max_sector:     float = 0.40,
) -> np.ndarray:
    """
    Risk-adjusted weight allocation:
    1. Inverse-volatility base weights
    2. Adjust by composite score (better stocks get more)
    3. Apply concentration constraints
    4. Normalize to sum = 1
    """
    n     = len(stocks)
    if n == 0:
        return np.array([])

    vols   = np.array([max(1.0, s.get("volatility", 20.0)) for s in stocks])
    scores = np.array([max(1.0, s.get("composite_score", 50.0)) for s in stocks])

    # Inverse vol * score blend
    inv_vol    = 1.0 / vols
    score_norm = scores / scores.sum()
    raw        = (0.6 * inv_vol / inv_vol.sum()) + (0.4 * score_norm)

    # Apply max single-stock constraint
    raw = np.minimum(raw, max_single)
    raw = raw / raw.sum()

    # Apply sector constraint
    sectors      = [s.get("sector", "Other") for s in stocks]
    sector_map   = {}
    for i, sec in enumerate(sectors):
        sector_map.setdefault(sec, []).append(i)

    for indices in sector_map.values():
        sec_total = raw[indices].sum()
        if sec_total > max_sector:
            raw[indices] = raw[indices] * (max_sector / sec_total)

    raw = raw / raw.sum()
    return raw


def compute_portfolio_metrics(
    stocks:  List[Dict],
    weights: np.ndarray,
    amount:  float,
) -> Dict:
    """
    Compute real expected return, volatility, and correlation-adjusted metrics.
    Uses weighted averages of real stock metrics.
    """
    if not stocks or len(weights) == 0:
        return {"expected_return": 0, "expected_volatility": 0, "portfolio_score": 50}

    w = np.array(weights)

    # Weighted metrics
    sharpes    = np.array([s.get("sharpe", 0)         for s in stocks])
    sortinos   = np.array([s.get("sortino", 0)        for s in stocks])
    vols       = np.array([s.get("volatility", 20)    for s in stocks])
    moms       = np.array([s.get("momentum_1y", 0)    for s in stocks])
    drawdowns  = np.array([s.get("max_drawdown", -20) for s in stocks])
    betas      = np.array([s.get("beta", 1.0)         for s in stocks])
    composites = np.array([s.get("composite_score",50) for s in stocks])

    w_sharpe   = float(w @ sharpes)
    w_sortino  = float(w @ sortinos)
    w_vol      = float(w @ vols)
    w_mom      = float(w @ moms)
    w_dd       = float(w @ drawdowns)
    w_beta     = float(w @ betas)
    w_score    = float(w @ composites)

    # Diversification benefit approximation
    # Portfolio vol < weighted avg vol due to correlation < 1
    n_stocks   = len(stocks)
    n_sectors  = len({s.get("sector") for s in stocks})
    div_factor = 0.85 - (0.05 * min(n_sectors, 6))  # more sectors = more diversification
    adj_vol    = w_vol * div_factor

    # ── Portfolio score (0–100) — based on REAL metrics ──────
    # Components:
    # 1. Risk-adjusted return (Sharpe): 30 pts max
    # 2. Momentum (1Y): 25 pts max
    # 3. Drawdown protection: 20 pts max
    # 4. Diversification: 15 pts max
    # 5. Consistency (vol-adjusted): 10 pts max

    sharpe_pts = min(30, max(0, (w_sharpe + 0.5) / 2.5 * 30))
    mom_pts    = min(25, max(0, (w_mom + 10) / 60 * 25))
    dd_pts     = min(20, max(0, (w_dd + 50) / 50 * 20))   # -50% → 0, 0% → 20
    div_pts    = min(15, (n_sectors / 6) * 15)
    vol_pts    = min(10, max(0, (1 - min(w_vol / 40, 1)) * 10))

    port_score = round(sharpe_pts + mom_pts + dd_pts + div_pts + vol_pts)
    port_score = max(20, min(95, port_score))  # realistic range

    # Diversification score
    sector_weights: Dict[str, float] = {}
    for s, wi in zip(stocks, w):
        sec = s.get("sector", "Other")
        sector_weights[sec] = sector_weights.get(sec, 0) + float(wi)

    max_sec     = max(sector_weights.values()) if sector_weights else 1.0
    conc_pen    = max_sec * 100  # higher concentration = penalty
    div_score   = int(min(100, max(0,
        (n_stocks / 12) * 40 +
        (n_sectors / 7) * 35 +
        ((100 - conc_pen) * 0.25)
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


def build_final_portfolio(
    scored_stocks: List[Dict],
    amount:        float,
    n_stocks:      int,
    profile:       Dict,
) -> Tuple[List[Dict], np.ndarray, Dict]:
    """
    Select stocks + compute allocations + compute portfolio metrics.
    """
    from app.recommendation.scorer import select_top_n

    max_sector = profile.get("max_sector", 0.40)
    max_single = profile.get("max_single_stock", 0.25)

    selected = select_top_n(scored_stocks, n_stocks, max_sector)
    if not selected:
        return [], np.array([]), {}

    weights = allocate_weights(selected, max_single, max_sector)
    metrics = compute_portfolio_metrics(selected, weights, amount)

    return selected, weights, metrics