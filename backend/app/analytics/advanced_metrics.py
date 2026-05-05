import logging
import numpy as np
import pandas as pd
import yfinance as yf
from typing import List, Dict

logger = logging.getLogger(__name__)


def compute_advanced_metrics(
    portfolio_returns: pd.Series,
    holdings: List[Dict],
    risk_metrics: Dict
) -> Dict:
    return {
        "var_95":           value_at_risk(portfolio_returns, 0.95),
        "var_99":           value_at_risk(portfolio_returns, 0.99),
        "cvar_95":          conditional_var(portfolio_returns, 0.95),
        "alpha":            compute_alpha(portfolio_returns),
        "regime":           detect_regime(portfolio_returns),
        "factor_exposure":  factor_exposure(holdings),
        "interpretation":   interpret_advanced(portfolio_returns, holdings),
    }


def value_at_risk(returns: pd.Series, confidence: float = 0.95) -> float:
    """
    Historical VaR: worst expected loss at given confidence.
    e.g. VaR 95% = -2.3% means 95% of days loss won't exceed 2.3%
    """
    if returns.empty:
        return 0.0
    return round(float(np.percentile(returns, (1 - confidence) * 100)) * 100, 3)


def conditional_var(returns: pd.Series, confidence: float = 0.95) -> float:
    """
    CVaR: average loss BEYOND the VaR threshold.
    More conservative than VaR — used by hedge funds.
    """
    if returns.empty:
        return 0.0
    var = np.percentile(returns, (1 - confidence) * 100)
    tail = returns[returns <= var]
    return round(float(tail.mean()) * 100, 3) if len(tail) > 0 else round(float(var) * 100, 3)


def compute_alpha(portfolio_returns: pd.Series) -> float:
    """
    Jensen's Alpha vs Nifty 50.
    Positive = outperforming market on risk-adjusted basis.
    """
    try:
        nifty = yf.download(
            "^NSEI", period="1y", auto_adjust=True, progress=False
        )
        if nifty.empty:
            return 0.0

        bench = nifty["Close"].squeeze().pct_change().dropna()
        aligned = pd.concat(
            [portfolio_returns, bench], axis=1
        ).dropna()
        aligned.columns = ["port", "bench"]

        if len(aligned) < 20:
            return 0.0

        risk_free = 0.065 / 252
        cov = np.cov(aligned["port"], aligned["bench"])
        beta = cov[0][1] / cov[1][1] if cov[1][1] != 0 else 1.0
        expected = risk_free + beta * (aligned["bench"].mean() - risk_free)
        alpha = (aligned["port"].mean() - expected) * 252
        return round(float(alpha * 100), 3)
    except Exception as e:
        logger.warning(f"Alpha computation failed: {e}")
        return 0.0


def detect_regime(returns: pd.Series) -> Dict:
    """
    Detect market regime: Bull / Bear / Sideways
    Based on rolling 30-day trend + volatility.
    """
    if len(returns) < 30:
        return {
            "regime": "unknown",
            "label": "⚪ Insufficient Data",
            "color": "gray",
            "trend_pct": 0.0,
            "volatility_pct": 0.0,
        }

    recent = returns.tail(30)
    trend  = float(recent.mean() * 252 * 100)
    vol    = float(recent.std() * np.sqrt(252) * 100)

    if trend > 10 and vol < 25:
        regime, label, color = "bull",     "🟢 Bull Market",  "green"
    elif trend < -5 or vol > 35:
        regime, label, color = "bear",     "🔴 Bear Market",  "red"
    else:
        regime, label, color = "sideways", "🟡 Sideways",     "yellow"

    return {
        "regime":          regime,
        "label":           label,
        "color":           color,
        "trend_pct":       round(trend, 2),
        "volatility_pct":  round(vol, 2),
    }


def factor_exposure(holdings: List[Dict]) -> Dict:
    """
    Estimate factor exposures from sector composition.
    No paid API needed.
    """
    if not holdings:
        return {}

    sectors = [h.get("sector", "Unknown") for h in holdings]
    n = len(sectors)

    tech_pct    = sectors.count("Technology") / n * 100
    banking_pct = sectors.count("Banking") / n * 100
    energy_pct  = sectors.count("Energy") / n * 100

    return {
        "momentum":   round(tech_pct, 1),
        "value":      round(100 - tech_pct, 1),
        "growth":     round(tech_pct * 0.8, 1),
        "defensive":  round((banking_pct + energy_pct) / 2, 1),
    }


def interpret_advanced(
    returns: pd.Series,
    holdings: List[Dict]
) -> Dict:
    var   = value_at_risk(returns, 0.95)
    cvar  = conditional_var(returns, 0.95)
    alpha = compute_alpha(returns)

    return {
        "var": (
            f"On 95% of trading days, your daily loss won't exceed {abs(var):.2f}%"
            if var != 0 else "Insufficient data for VaR"
        ),
        "cvar": (
            f"On your worst days (beyond VaR), average loss is {abs(cvar):.2f}%"
            if cvar != 0 else "Insufficient data for CVaR"
        ),
        "alpha": (
            f"Portfolio generating {alpha:.2f}% excess return vs Nifty 50 annually"
            if alpha > 0
            else f"Portfolio underperforming Nifty 50 by {abs(alpha):.2f}% annually"
        ),
    }