import logging
import warnings
import numpy as np
import pandas as pd
import yfinance as yf
from typing import List, Dict
from app.cache import store as cache

logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore")


def _batch_download(symbols: List[str], period: str = "1y") -> pd.DataFrame:
    key    = cache.make_portfolio_key("prices_raw", [{"s": s} for s in symbols], period)
    cached = cache.get(key, cache.TTL_ANALYTICS, disk=True)
    if cached is not None:
        return pd.DataFrame(cached)

    try:
        data = yf.download(
            symbols, period=period,
            auto_adjust=True, progress=False, timeout=25,
        )
        if data.empty:
            return pd.DataFrame()

        if len(symbols) == 1:
            prices = data[["Close"]].rename(columns={"Close": symbols[0]})
        else:
            prices = data["Close"] if "Close" in data.columns else data.xs("Close", axis=1, level=0)

        prices = prices.dropna(how="all")
        cache.set(key, prices.to_dict(), cache.TTL_ANALYTICS, disk=True)
        return prices
    except Exception as e:
        logger.warning(f"Batch download failed: {e}")
        return pd.DataFrame()


def calculate_risk_metrics(holdings: List[Dict]) -> Dict:
    valid = [h for h in holdings if h.get("symbol") and _safe_float(h.get("invested_value")) > 0]
    if not valid:
        return _empty()

    # Cache check
    key    = cache.make_portfolio_key("risk", valid)
    cached = cache.get(key, cache.TTL_ANALYTICS)
    if cached:
        return cached

    symbols   = [h["symbol"] for h in valid]
    total_inv = sum(_safe_float(h.get("invested_value")) for h in valid)
    w         = np.array([_safe_float(h.get("invested_value")) / total_inv for h in valid])

    prices_df = _batch_download(symbols)
    if prices_df.empty:
        return _empty()

    available  = [s for s in symbols if s in prices_df.columns]
    if len(available) < 1:
        return _empty()

    prices  = prices_df[available].dropna(how="all")
    returns = prices.pct_change(fill_method=None).dropna()
    if len(returns) < 20:
        return _empty()

    # Align weights
    idx  = [symbols.index(s) for s in available if s in symbols]
    wa   = w[idx]; wa = wa / wa.sum()

    port_ret = returns[available].values @ wa
    ps       = pd.Series(port_ret)

    ann_ret  = float(ps.mean() * 252 * 100)
    ann_vol  = float(ps.std() * np.sqrt(252) * 100)
    rf       = 6.5
    sharpe   = round((ann_ret - rf) / ann_vol, 3) if ann_vol > 0 else 0.0

    # Sortino
    neg      = ps[ps < 0]
    sortino  = round((ann_ret - rf) / (float(neg.std()) * np.sqrt(252) * 100), 3) if len(neg) > 1 else 0.0

    # Max drawdown — vectorized
    cum     = (1 + ps).cumprod()
    max_dd  = float(((cum - cum.cummax()) / cum.cummax()).min() * 100)

    # Beta
    beta = _compute_beta(ps)

    # Sector breakdown
    sector_map: Dict[str, float] = {}
    for h in valid:
        sec = h.get("sector") or "Unknown"
        sector_map[sec] = sector_map.get(sec, 0) + _safe_float(h.get("invested_value"))

    sector_breakdown = [
        {"sector": k, "weight_pct": round(v / total_inv * 100, 1)}
        for k, v in sorted(sector_map.items(), key=lambda x: -x[1])
    ]

    result = {
        "sharpe_ratio":              round(sharpe, 3),
        "sortino_ratio":             round(sortino, 3),
        "annualized_return_pct":     round(ann_ret, 2),
        "annualized_volatility_pct": round(ann_vol, 2),
        "max_drawdown_pct":          round(max_dd, 2),
        "beta":                      round(beta, 3),
        "sector_breakdown":          sector_breakdown,
        "total_holdings":            len(valid),
        "total_invested":            round(total_inv, 2),
        "interpretation": {
            "sharpe":     _interp_sharpe(sharpe),
            "volatility": _interp_vol(ann_vol),
            "drawdown":   f"Worst loss from peak: {abs(max_dd):.1f}%",
            "beta":       _interp_beta(beta),
        },
    }
    cache.set(key, result, cache.TTL_ANALYTICS)
    return result


def _compute_beta(ps: pd.Series) -> float:
    key    = f"beta_nifty:{len(ps)}"
    cached = cache.get(key, cache.TTL_ANALYTICS, disk=True)
    if cached is not None:
        return cached
    try:
        n     = yf.download("^NSEI", period="1y", auto_adjust=True, progress=False, timeout=10)
        bench = n["Close"].pct_change(fill_method=None).dropna()
        ali   = pd.concat([ps, bench], axis=1).dropna()
        if len(ali) < 20:
            return 1.0
        cov   = np.cov(ali.iloc[:, 0], ali.iloc[:, 1])
        beta  = float(cov[0][1] / cov[1][1]) if cov[1][1] != 0 else 1.0
        cache.set(key, beta, cache.TTL_ANALYTICS, disk=True)
        return round(beta, 3)
    except Exception:
        return 1.0


def _safe_float(v, d: float = 0.0) -> float:
    try:
        r = float(v); return r if r == r else d
    except Exception:
        return d


def _interp_sharpe(s):
    if s >= 2:   return "Excellent risk-adjusted returns"
    if s >= 1:   return "Good — solid performance per unit risk"
    if s >= 0.5: return "Average — moderate risk compensation"
    if s >= 0:   return "Below average — risk not well compensated"
    return "Poor — taking risk without adequate return"


def _interp_vol(v):
    if v < 12:  return "Low — stable portfolio"
    if v < 20:  return "Moderate — normal equity range"
    if v < 30:  return "High — significant price swings"
    return "Very high — extreme risk profile"


def _interp_beta(b):
    if b < 0.5:  return "Very defensive"
    if b < 0.85: return "Defensive — less volatile than Nifty"
    if b < 1.15: return "Market-like"
    if b < 1.5:  return "Aggressive"
    return "Very aggressive"


def _empty() -> Dict:
    return {
        "sharpe_ratio": 0, "sortino_ratio": 0,
        "annualized_return_pct": 0, "annualized_volatility_pct": 0,
        "max_drawdown_pct": 0, "beta": 1.0, "sector_breakdown": [],
        "total_holdings": 0, "total_invested": 0,
        "interpretation": {k: "Insufficient data" for k in ["sharpe","volatility","drawdown","beta"]},
    }