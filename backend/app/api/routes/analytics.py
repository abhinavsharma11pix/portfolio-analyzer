"""
backend/app/api/routes/analytics.py — Complete file.

Benchmark fix: builds portfolio returns directly from yfinance inside the
route rather than relying on build_portfolio_returns (which returns None/empty
and blocks the benchmark from ever computing).

The direct approach:
  1. Download 1y OHLCV for each holding symbol
  2. Compute daily returns per symbol
  3. Weight by invested_value to get portfolio daily return series
  4. Pass that series to compare_portfolio_vs_benchmarks

This bypasses the empty-returns problem entirely.
"""
import logging
import numpy as np
import pandas as pd
import yfinance as yf
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import ORJSONResponse
from app.cache import store as cache
from app.cache.symbol_cache import is_delisted

logger = logging.getLogger(__name__)
router = APIRouter(default_response_class=ORJSONResponse)

VALID_BENCHMARKS = {"^NSEI", "^BSESN", "^GSPC", "^IXIC", "^DJI"}
DEFAULT_BENCHMARK = "^NSEI"


def _clean_holdings(holdings: list) -> list:
    return [h for h in holdings if not is_delisted(h.get("symbol", ""))]


def _safe_benchmark(raw: str) -> str:
    b = (raw or DEFAULT_BENCHMARK).strip().upper()
    return b if b in VALID_BENCHMARKS else DEFAULT_BENCHMARK


def _build_portfolio_returns_direct(holdings: list) -> Optional[pd.Series]:
    """
    Build a weighted portfolio daily return series directly from yfinance.
    More robust than portfolio_returns.py because it handles partial failures —
    if some symbols fail to download, the rest still contribute.
    """
    if not holdings:
        return None

    total_invested = sum(
        float(h.get("invested_value", 0) or h.get("quantity", 0) * h.get("avg_buy_price", 0))
        for h in holdings
    )
    if total_invested <= 0:
        return None

    symbols = [h["symbol"] for h in holdings]
    try:
        raw = yf.download(
            symbols, period="1y",
            auto_adjust=True, progress=False,
            timeout=30, threads=True,
        )
        if raw.empty:
            return None

        # Extract Close prices
        if len(symbols) == 1:
            close = raw[["Close"]] if "Close" in raw.columns else raw.iloc[:, [0]]
            close.columns = symbols
        elif isinstance(raw.columns, pd.MultiIndex):
            close = raw["Close"] if "Close" in raw.columns.get_level_values(0) else raw.xs("Close", axis=1, level=0)
        else:
            close = raw["Close"] if "Close" in raw.columns else raw

        if isinstance(close, pd.Series):
            close = close.to_frame(name=symbols[0])

        # Daily returns per symbol
        rets = close.pct_change().dropna(how="all")
        if len(rets) < 20:
            return None

        # Weighted portfolio return
        portfolio_return = pd.Series(0.0, index=rets.index)
        for h in holdings:
            sym = h["symbol"]
            if sym not in rets.columns:
                continue
            invested = float(
                h.get("invested_value", 0)
                or h.get("quantity", 0) * h.get("avg_buy_price", 0)
            )
            if invested <= 0:
                continue
            weight = invested / total_invested
            sym_rets = rets[sym].fillna(0)
            portfolio_return = portfolio_return + sym_rets * weight

        result = portfolio_return[portfolio_return != 0].dropna()
        return result if len(result) >= 20 else None

    except Exception as e:
        logger.warning(f"Direct portfolio returns build failed: {e}")
        return None


# ── /advanced ─────────────────────────────────────────────────

@router.post("/advanced")
async def get_advanced(payload: dict):
    from app.analytics.portfolio_returns import build_portfolio_returns
    from app.analytics.advanced_metrics import compute_advanced_metrics

    holdings     = _clean_holdings(payload.get("holdings", []))
    risk_metrics = payload.get("risk_metrics", {})

    if not holdings:
        raise HTTPException(400, "No valid holdings")

    key    = cache.make_portfolio_key("advanced_v2", holdings, risk_metrics)
    cached = cache.get(key, cache.TTL_ANALYTICS)
    if cached:
        return cached

    returns = build_portfolio_returns(holdings)
    if returns is None or len(returns) < 20:
        return {
            "var_95": 0.0, "var_99": 0.0, "cvar_95": 0.0, "alpha": 0.0,
            "regime": {"regime": "unknown", "label": "⚪ Insufficient Data",
                       "color": "gray", "trend_pct": 0.0, "volatility_pct": 0.0},
            "factor_exposure": {"momentum": 0, "value": 0, "growth": 0, "defensive": 0},
            "interpretation": {
                "var":   "Need 20+ trading days of data",
                "cvar":  "Need 20+ trading days of data",
                "alpha": "Need 20+ trading days of data",
            },
            "data_note": "One or more symbols unavailable — advanced metrics limited",
        }

    result = compute_advanced_metrics(returns, holdings, risk_metrics)
    cache.set(key, result, cache.TTL_ANALYTICS)
    return result


# ── /benchmark ────────────────────────────────────────────────

@router.post("/benchmark")
async def get_benchmark(payload: dict):
    from app.analytics.benchmark import compare_portfolio_vs_benchmarks

    holdings  = _clean_holdings(payload.get("holdings", []))
    benchmark = _safe_benchmark(payload.get("benchmark", DEFAULT_BENCHMARK))

    if not holdings:
        raise HTTPException(400, "No valid holdings")

    key    = cache.make_portfolio_key("benchmark_v4", holdings, {"bm": benchmark})
    cached = cache.get(key, cache.TTL_BENCHMARK, disk=True)
    if cached:
        logger.info(f"Benchmark cache hit: {benchmark}")
        return cached

    # Build portfolio returns directly (more robust than portfolio_returns.py)
    returns = _build_portfolio_returns_direct(holdings)

    if returns is None:
        logger.warning("Portfolio returns empty — returning zero-state benchmark")
        return _empty_benchmark(benchmark)

    logger.info(f"Built portfolio returns: {len(returns)} days. Computing vs {benchmark}...")

    try:
        result = compare_portfolio_vs_benchmarks(returns, holdings, benchmark)
    except Exception as e:
        logger.warning(f"Benchmark compute failed for {benchmark}: {e}")
        return _empty_benchmark(benchmark)

    if not isinstance(result, dict) or "portfolio_return" not in result:
        logger.warning(f"Benchmark returned unexpected shape for {benchmark}")
        return _empty_benchmark(benchmark)

    cache.set(key, result, cache.TTL_BENCHMARK, disk=True)
    return result


def _empty_benchmark(benchmark: str) -> dict:
    return {
        "portfolio_return":  0.0,
        "benchmark_return":  0.0,
        "alpha":             0.0,
        "beta":              1.0,
        "correlation":       0.0,
        "tracking_error":    0.0,
        "information_ratio": 0.0,
        "chart_data":        [],
        "benchmark_name":    benchmark,
        "data_note":         "Benchmark data temporarily unavailable. Try again in 30s.",
    }


# ── /simulate ─────────────────────────────────────────────────

@router.post("/simulate")
async def simulate(payload: dict):
    from app.analytics.simulator import simulate_scenarios
    holdings  = payload.get("holdings", [])
    scenarios = payload.get("scenarios", None)
    if not holdings:
        raise HTTPException(400, "No holdings")
    return {"scenarios": simulate_scenarios(holdings, scenarios)}


# ── /scenarios/default ────────────────────────────────────────

@router.get("/scenarios/default")
async def default_scenarios():
    from app.analytics.simulator import DEFAULT_SCENARIOS
    return {"scenarios": DEFAULT_SCENARIOS}
