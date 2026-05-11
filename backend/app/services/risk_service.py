"""
Production-grade risk engine.
Robust to bad data, rate limits, delisted stocks.
Never silently returns zeros.
"""
import logging
import warnings
import numpy as np
import pandas as pd
import yfinance as yf
from typing import List, Dict, Optional, Tuple
from app.cache import store as cache

logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore")

RISK_FREE_RATE = 0.065   # 6.5% — Indian risk-free rate (10yr G-sec)
MIN_DATA_POINTS = 30     # Minimum trading days needed


def _safe_float(v, default: float = 0.0) -> float:
    try:
        r = float(v)
        return r if (r == r and abs(r) < 1e10) else default
    except Exception:
        return default


def _download_with_fallback(
    symbols: List[str], period: str = "1y"
) -> pd.DataFrame:
    """
    Download price data — batch first, individual fallback.
    Handles rate limits and delisted stocks gracefully.
    """
    cache_key = cache.make_portfolio_key("dl", [{"s": s} for s in symbols], period)
    cached    = cache.get(cache_key, 3600, disk=True)
    if cached is not None:
        try:
            return pd.DataFrame(cached)
        except Exception:
            pass

    prices: Dict[str, pd.Series] = {}

    # Try batch download first
    try:
        data = yf.download(
            symbols, period=period,
            auto_adjust=True, progress=False,
            timeout=30, threads=True,
        )
        if not data.empty:
            if len(symbols) == 1:
                col = "Close"
                if col in data.columns:
                    prices[symbols[0]] = data[col].squeeze()
            else:
                if isinstance(data.columns, pd.MultiIndex):
                    if "Close" in data.columns.get_level_values(0):
                        close = data["Close"]
                    elif "Close" in data.columns.get_level_values(1):
                        close = data.xs("Close", axis=1, level=1)
                    else:
                        close = data.iloc[:, :len(symbols)]
                else:
                    close = data["Close"] if "Close" in data.columns else data
                for sym in symbols:
                    if sym in close.columns:
                        s = close[sym].dropna()
                        if len(s) >= MIN_DATA_POINTS:
                            prices[sym] = s
    except Exception as e:
        logger.warning(f"Batch download failed: {e}")

    # Individual fallback for missing symbols
    missing = [s for s in symbols if s not in prices]
    if missing:
        logger.info(f"Individual fallback for {len(missing)} symbols")
        for sym in missing:
            try:
                t    = yf.Ticker(sym)
                hist = t.history(period=period, timeout=10)
                if not hist.empty and len(hist) >= MIN_DATA_POINTS:
                    prices[sym] = hist["Close"]
            except Exception:
                logger.debug(f"Individual download failed: {sym}")

    if not prices:
        return pd.DataFrame()

    df = pd.DataFrame(prices).dropna(how="all")
    if not df.empty:
        try:
            cache.set(cache_key, df.to_dict(), 3600, disk=True)
        except Exception:
            pass
    return df


def calculate_risk_metrics(holdings: List[Dict]) -> Dict:
    """
    Robust portfolio risk calculation.
    Returns meaningful values even with partial data.
    """
    if not holdings:
        return _empty_metrics("No holdings provided")

    # Validate holdings — only use ones with valid data
    valid = []
    for h in holdings:
        inv = _safe_float(h.get("invested_value"), 0)
        qty = _safe_float(h.get("quantity"), 0)
        avg = _safe_float(h.get("avg_buy_price"), 0)
        sym = h.get("symbol", "").strip()
        if sym and (inv > 0 or (qty > 0 and avg > 0)):
            if inv <= 0:
                inv = qty * avg
            valid.append({**h, "invested_value": inv, "symbol": sym})

    if not valid:
        return _empty_metrics("No valid holdings with price data")

    # Cache check
    key    = cache.make_portfolio_key("risk_v3", valid)
    cached = cache.get(key, 600)
    if cached:
        logger.info("Risk metrics from cache")
        return cached

    symbols   = [h["symbol"] for h in valid]
    total_inv = sum(h["invested_value"] for h in valid)

    if total_inv <= 0:
        return _empty_metrics("Total invested value is zero")

    weights = np.array([h["invested_value"] / total_inv for h in valid])

    # Download prices
    prices_df = _download_with_fallback(symbols)

    if prices_df.empty:
        logger.warning("Price download returned empty — using holdings-based metrics only")
        result = _holdings_only_metrics(valid, total_inv)
        cache.set(key, result, 300)
        return result

    # Align symbols
    available = [s for s in symbols if s in prices_df.columns]
    if len(available) == 0:
        return _holdings_only_metrics(valid, total_inv)

    logger.info(f"Computing risk with {len(available)}/{len(symbols)} symbols")

    prices  = prices_df[available].ffill().dropna(how="all")
    returns = prices.pct_change().dropna()

    if len(returns) < MIN_DATA_POINTS:
        logger.warning(f"Only {len(returns)} data points — insufficient for reliable metrics")
        return _holdings_only_metrics(valid, total_inv)

    # Align weights to available symbols
    avail_idx = [symbols.index(s) for s in available if s in symbols]
    w = weights[avail_idx]
    w = w / w.sum()  # renormalize

    # ── Portfolio returns ─────────────────────────────────────
    port_ret = returns[available].values @ w
    ps       = pd.Series(port_ret, index=returns.index)

    n_years = len(ps) / 252

    ann_ret = float(ps.mean() * 252 * 100)
    ann_vol = float(ps.std() * np.sqrt(252) * 100) if ps.std() > 0 else 0.1

    # ── Sharpe ratio ──────────────────────────────────────────
    daily_rf = RISK_FREE_RATE / 252
    sharpe   = float((ps.mean() - daily_rf) / ps.std() * np.sqrt(252)) if ps.std() > 0 else 0.0

    # ── Sortino ratio ─────────────────────────────────────────
    neg_rets   = ps[ps < 0]
    downside   = float(neg_rets.std() * np.sqrt(252)) if len(neg_rets) > 1 else ann_vol / 100
    sortino    = float((ps.mean() - daily_rf) / (downside / np.sqrt(252))) if downside > 0 else 0.0

    # ── Max drawdown ──────────────────────────────────────────
    cum     = (1 + ps).cumprod()
    rolling = cum.cummax()
    dd      = (cum - rolling) / rolling.replace(0, np.nan)
    max_dd  = float(dd.min() * 100) if not dd.empty else 0.0

    # ── Calmar ratio ──────────────────────────────────────────
    calmar = round(ann_ret / abs(max_dd), 2) if max_dd < 0 else 0.0

    # ── Beta ──────────────────────────────────────────────────
    beta = _compute_beta_robust(ps)

    # ── VaR & CVaR ────────────────────────────────────────────
    var_95  = float(np.percentile(ps, 5) * 100)
    var_99  = float(np.percentile(ps, 1) * 100)
    cvar_95 = float(ps[ps <= np.percentile(ps, 5)].mean() * 100) if len(ps) > 20 else var_95

    # ── Sector breakdown ──────────────────────────────────────
    sector_map: Dict[str, float] = {}
    for h in valid:
        sec = h.get("sector") or "Unknown"
        sector_map[sec] = sector_map.get(sec, 0) + h["invested_value"]
    sector_breakdown = sorted(
        [{"sector": k, "weight_pct": round(v / total_inv * 100, 1)} for k, v in sector_map.items()],
        key=lambda x: -x["weight_pct"]
    )
    top_sector     = sector_breakdown[0]["sector"] if sector_breakdown else "N/A"
    top_sector_pct = sector_breakdown[0]["weight_pct"] if sector_breakdown else 0

    # ── Correlation ───────────────────────────────────────────
    avg_correlation = 0.0
    if len(available) > 1:
        corr_matrix     = returns[available].corr()
        mask            = np.triu(np.ones(corr_matrix.shape), k=1).astype(bool)
        upper           = corr_matrix.where(mask)
        flat            = upper.stack().dropna()
        avg_correlation = round(float(flat.mean()), 3) if len(flat) > 0 else 0.0

    # ── Diversification score ─────────────────────────────────
    n_stocks   = len(valid)
    n_sectors  = len(sector_map)
    conc_score = 100 - (max(sector_map.values()) / total_inv * 100) if total_inv > 0 else 50
    div_score  = min(100, int(
        (min(n_stocks, 15) / 15 * 40) +
        (min(n_sectors, 8) / 8 * 30) +
        (conc_score * 0.30)
    ))

    total_cv = sum(
        _safe_float(h.get("current_value")) or h["invested_value"]
        for h in valid
    )

    result = {
        # Core
        "sharpe_ratio":               round(sharpe, 3),
        "sortino_ratio":              round(sortino, 3),
        "calmar_ratio":               calmar,
        "annualized_return_pct":      round(ann_ret, 2),
        "annualized_volatility_pct":  round(ann_vol, 2),
        "max_drawdown_pct":           round(max_dd, 2),
        "beta":                       round(beta, 3),
        # Risk measures
        "var_95_daily_pct":           round(var_95, 3),
        "var_99_daily_pct":           round(var_99, 3),
        "cvar_95_daily_pct":          round(cvar_95, 3),
        # Portfolio
        "avg_correlation":            avg_correlation,
        "diversification_score":      div_score,
        "total_holdings":             len(valid),
        "total_invested":             round(total_inv, 2),
        "total_current_value":        round(total_cv, 2),
        "data_points":                len(ps),
        "n_years":                    round(n_years, 2),
        # Breakdown
        "sector_breakdown":           sector_breakdown,
        "top_sector":                 top_sector,
        "top_sector_weight_pct":      top_sector_pct,
        # Interpretation
        "interpretation": {
            "sharpe":       _interp_sharpe(sharpe),
            "volatility":   _interp_vol(ann_vol),
            "drawdown":     f"Worst historical decline from peak: {abs(max_dd):.1f}%",
            "beta":         _interp_beta(beta),
            "diversification": _interp_div(div_score),
        },
        "data_quality": "full" if len(available) == len(symbols) else "partial",
        "missing_symbols": [s for s in symbols if s not in available],
    }

    cache.set(key, result, 600)
    return result


def _compute_beta_robust(ps: pd.Series) -> float:
    """Compute beta vs Nifty 50 with disk caching."""
    cache_key = f"beta_nifty50:{len(ps)}"
    cached    = cache.get(cache_key, 3600, disk=True)
    if cached is not None:
        return cached

    try:
        bench_data = yf.download(
            "^NSEI", period="1y",
            auto_adjust=True, progress=False, timeout=15
        )
        if bench_data.empty:
            # Fallback to Sensex
            bench_data = yf.download(
                "^BSESN", period="1y",
                auto_adjust=True, progress=False, timeout=10
            )
        if bench_data.empty:
            return 1.0

        bench  = bench_data["Close"].squeeze().pct_change().dropna()
        aligned = pd.concat([ps, bench], axis=1).dropna()
        aligned.columns = ["port", "bench"]

        if len(aligned) < MIN_DATA_POINTS:
            return 1.0

        cov  = np.cov(aligned["port"], aligned["bench"])
        beta = float(cov[0][1] / cov[1][1]) if abs(cov[1][1]) > 1e-10 else 1.0
        beta = max(-3.0, min(3.0, beta))  # clip extreme values

        cache.set(cache_key, round(beta, 3), 3600, disk=True)
        return round(beta, 3)
    except Exception as e:
        logger.warning(f"Beta computation failed: {e}")
        return 1.0


def _holdings_only_metrics(holdings: List[Dict], total_inv: float) -> Dict:
    """Fallback when market data unavailable — sector/allocation metrics only."""
    sector_map: Dict[str, float] = {}
    for h in holdings:
        sec = h.get("sector") or "Unknown"
        sector_map[sec] = sector_map.get(sec, 0) + h["invested_value"]

    sector_breakdown = sorted(
        [{"sector": k, "weight_pct": round(v / total_inv * 100, 1)} for k, v in sector_map.items()],
        key=lambda x: -x["weight_pct"]
    )
    n_stocks  = len(holdings)
    n_sectors = len(sector_map)
    top_pct   = sector_breakdown[0]["weight_pct"] if sector_breakdown else 0
    div_score = min(100, int((min(n_stocks, 15)/15*40) + (min(n_sectors, 8)/8*30) + ((100-top_pct)*0.30)))

    return {
        "sharpe_ratio": 0.0, "sortino_ratio": 0.0, "calmar_ratio": 0.0,
        "annualized_return_pct": 0.0, "annualized_volatility_pct": 0.0,
        "max_drawdown_pct": 0.0, "beta": 1.0,
        "var_95_daily_pct": 0.0, "var_99_daily_pct": 0.0, "cvar_95_daily_pct": 0.0,
        "avg_correlation": 0.0, "diversification_score": div_score,
        "total_holdings": n_stocks, "total_invested": round(total_inv, 2),
        "total_current_value": round(total_inv, 2), "data_points": 0,
        "sector_breakdown": sector_breakdown,
        "top_sector": sector_breakdown[0]["sector"] if sector_breakdown else "N/A",
        "top_sector_weight_pct": top_pct,
        "interpretation": {
            "sharpe": "Insufficient market data",
            "volatility": "Insufficient market data",
            "drawdown": "Insufficient market data",
            "beta": "Insufficient market data",
            "diversification": _interp_div(div_score),
        },
        "data_quality": "holdings_only",
        "missing_symbols": [h["symbol"] for h in holdings],
    }


def _empty_metrics(reason: str = "No data") -> Dict:
    return {
        "sharpe_ratio": 0, "sortino_ratio": 0, "calmar_ratio": 0,
        "annualized_return_pct": 0, "annualized_volatility_pct": 0,
        "max_drawdown_pct": 0, "beta": 1.0,
        "var_95_daily_pct": 0, "var_99_daily_pct": 0, "cvar_95_daily_pct": 0,
        "avg_correlation": 0, "diversification_score": 0,
        "total_holdings": 0, "total_invested": 0, "total_current_value": 0,
        "data_points": 0, "sector_breakdown": [],
        "top_sector": "N/A", "top_sector_weight_pct": 0,
        "interpretation": {k: reason for k in ["sharpe","volatility","drawdown","beta","diversification"]},
        "data_quality": "none", "missing_symbols": [], "error": reason,
    }


def _interp_sharpe(s: float) -> str:
    if s >= 3:   return "Outstanding — top-tier risk-adjusted returns"
    if s >= 2:   return "Excellent — exceptional risk-adjusted performance"
    if s >= 1:   return "Good — solid returns per unit of risk"
    if s >= 0.5: return "Average — moderate risk compensation"
    if s >= 0:   return "Below average — risk not fully compensated"
    return "Poor — bearing significant risk without adequate returns"


def _interp_vol(v: float) -> str:
    if v < 8:   return "Very low — near bond-like stability"
    if v < 15:  return "Low — stable portfolio"
    if v < 22:  return "Moderate — typical equity range"
    if v < 30:  return "High — significant price swings expected"
    return "Very high — extreme volatility, only for risk-tolerant investors"


def _interp_beta(b: float) -> str:
    if b < 0:    return "Inverse market — hedges against market declines"
    if b < 0.5:  return "Very defensive — much less volatile than market"
    if b < 0.85: return "Defensive — moves less than Nifty 50"
    if b < 1.15: return "Market-neutral — closely tracks Nifty 50"
    if b < 1.5:  return "Aggressive — amplifies market movements"
    return "Very aggressive — significantly more volatile than market"


def _interp_div(score: int) -> str:
    if score >= 80: return "Excellent diversification across sectors and stocks"
    if score >= 60: return "Good diversification — moderate concentration risk"
    if score >= 40: return "Fair — consider adding more sectors"
    return "Poor — high concentration risk, consider diversifying"