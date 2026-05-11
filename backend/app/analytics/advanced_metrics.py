import logging
import warnings
import numpy as np
import pandas as pd
import yfinance as yf
from typing import List, Dict, Optional
from app.cache import store as cache

logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore")

RISK_FREE = 0.065 / 252  # daily


def compute_advanced_metrics(
    portfolio_returns: pd.Series,
    holdings: List[Dict],
    risk_metrics: Dict,
) -> Dict:
    """Compute advanced metrics from portfolio returns series."""
    if portfolio_returns is None or len(portfolio_returns) < 30:
        return _empty_advanced("Insufficient return data (need 30+ days)")

    ps = portfolio_returns.dropna()
    if len(ps) < 30:
        return _empty_advanced("Too few data points after cleaning")

    try:
        return {
            "var_95":          _var(ps, 0.95),
            "var_99":          _var(ps, 0.99),
            "cvar_95":         _cvar(ps, 0.95),
            "alpha":           _alpha(ps),
            "regime":          _regime(ps),
            "factor_exposure": _factor_exposure(holdings),
            "interpretation":  _interpretations(ps),
        }
    except Exception as e:
        logger.error(f"Advanced metrics failed: {e}")
        return _empty_advanced(str(e))


def _var(ps: pd.Series, confidence: float) -> float:
    pct   = (1 - confidence) * 100
    value = float(np.percentile(ps, pct) * 100)
    return round(value, 3)


def _cvar(ps: pd.Series, confidence: float) -> float:
    threshold = np.percentile(ps, (1 - confidence) * 100)
    tail      = ps[ps <= threshold]
    if len(tail) == 0:
        return _var(ps, confidence)
    return round(float(tail.mean() * 100), 3)


def _alpha(ps: pd.Series) -> float:
    """Jensen's Alpha vs Nifty 50."""
    key    = f"alpha_nifty:{len(ps)}"
    cached = cache.get(key, 3600, disk=True)
    if cached is not None:
        return cached

    try:
        bench_data = yf.download(
            "^NSEI", period="1y",
            auto_adjust=True, progress=False, timeout=15
        )
        if bench_data.empty:
            return 0.0

        bench   = bench_data["Close"].squeeze().pct_change().dropna()
        aligned = pd.concat([ps, bench], axis=1).dropna()
        aligned.columns = ["port", "bench"]

        if len(aligned) < 30:
            return 0.0

        cov    = np.cov(aligned["port"], aligned["bench"])
        beta   = float(cov[0][1] / cov[1][1]) if abs(cov[1][1]) > 1e-10 else 1.0
        rf_d   = 0.065 / 252
        alpha  = (aligned["port"].mean() - rf_d) - beta * (aligned["bench"].mean() - rf_d)
        result = round(float(alpha * 252 * 100), 3)

        cache.set(key, result, 3600, disk=True)
        return result
    except Exception as e:
        logger.warning(f"Alpha failed: {e}")
        return 0.0


def _regime(ps: pd.Series) -> Dict:
    """Detect market regime from recent 30-day portfolio behavior."""
    if len(ps) < 30:
        return {"regime": "unknown", "label": "⚪ Insufficient Data", "color": "gray", "trend_pct": 0.0, "volatility_pct": 0.0}

    recent = ps.tail(30)
    trend  = float(recent.mean() * 252 * 100)
    vol    = float(recent.std() * np.sqrt(252) * 100)

    if trend > 12 and vol < 22:
        return {"regime": "bull",     "label": "🟢 Bull Market",  "color": "green",  "trend_pct": round(trend, 2), "volatility_pct": round(vol, 2)}
    if trend < -5 or vol > 35:
        return {"regime": "bear",     "label": "🔴 Bear Market",  "color": "red",    "trend_pct": round(trend, 2), "volatility_pct": round(vol, 2)}
    return {"regime": "sideways",     "label": "🟡 Sideways",     "color": "yellow", "trend_pct": round(trend, 2), "volatility_pct": round(vol, 2)}


def _factor_exposure(holdings: List[Dict]) -> Dict:
    sectors   = [h.get("sector", "Unknown") for h in holdings]
    n         = max(len(sectors), 1)
    tech_pct  = sectors.count("Technology") / n * 100
    bank_pct  = sectors.count("Banking") / n * 100
    engy_pct  = sectors.count("Energy") / n * 100
    fmcg_pct  = sectors.count("FMCG") / n * 100

    return {
        "momentum":  round(tech_pct, 1),
        "value":     round(100 - tech_pct, 1),
        "growth":    round(tech_pct * 0.8 + bank_pct * 0.2, 1),
        "defensive": round((fmcg_pct + engy_pct) / 2, 1),
    }


def _interpretations(ps: pd.Series) -> Dict:
    var  = _var(ps, 0.95)
    cvar = _cvar(ps, 0.95)
    alp  = _alpha(ps)
    return {
        "var":  (
            f"95% of days, daily loss won't exceed {abs(var):.2f}%"
            if var != 0 else "Insufficient data for VaR"
        ),
        "cvar": (
            f"On worst days beyond VaR, average loss is {abs(cvar):.2f}%"
            if cvar != 0 else "Insufficient data for CVaR"
        ),
        "alpha": (
            f"Generating {alp:.2f}% excess annual return vs Nifty 50"
            if alp > 0
            else f"Underperforming Nifty 50 by {abs(alp):.2f}% annually"
            if alp < 0
            else "Alpha data unavailable"
        ),
    }


def _empty_advanced(reason: str) -> Dict:
    return {
        "var_95": 0.0, "var_99": 0.0, "cvar_95": 0.0, "alpha": 0.0,
        "regime": {"regime": "unknown", "label": "⚪ No Data", "color": "gray", "trend_pct": 0.0, "volatility_pct": 0.0},
        "factor_exposure": {"momentum": 0, "value": 0, "growth": 0, "defensive": 0},
        "interpretation": {"var": reason, "cvar": reason, "alpha": reason},
        "error": reason,
    }