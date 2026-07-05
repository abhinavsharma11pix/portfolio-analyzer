"""
backend/app/api/routes/analytics.py — Complete file.

Fixed:
  1. /benchmark now reads the 'benchmark' field from the payload and
     passes it to compare_portfolio_vs_benchmarks — previously the
     benchmark symbol sent by the frontend was silently ignored, so
     clicking SENSEX/S&P/NASDAQ had no effect.

  2. Cache key now includes the benchmark symbol so switching between
     NIFTY50, SENSEX, S&P500 each gets its own cached result.

  3. When portfolio returns are insufficient, returns a safe zero-value
     structure that matches the shape the frontend expects, so the chart
     renders a "not enough data" message instead of crashing.
"""
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import ORJSONResponse
from app.cache import store as cache
from app.cache.symbol_cache import is_delisted

logger = logging.getLogger(__name__)
router = APIRouter(default_response_class=ORJSONResponse)

VALID_BENCHMARKS = {
    "^NSEI", "^BSESN", "^GSPC", "^IXIC", "^DJI", "^NSEBANK",
}
DEFAULT_BENCHMARK = "^NSEI"


def _clean_holdings(holdings: list) -> list:
    """Remove delisted symbols before analytics."""
    return [h for h in holdings if not is_delisted(h.get("symbol", ""))]


def _safe_benchmark(raw: str) -> str:
    """Validate benchmark symbol — fall back to NIFTY50 if unknown."""
    b = (raw or DEFAULT_BENCHMARK).strip().upper()
    return b if b in VALID_BENCHMARKS else DEFAULT_BENCHMARK


# ── /advanced ────────────────────────────────────────────────

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
            "regime": {
                "regime": "unknown", "label": "⚪ Insufficient Data",
                "color": "gray", "trend_pct": 0.0, "volatility_pct": 0.0,
            },
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


# ── /benchmark ───────────────────────────────────────────────

@router.post("/benchmark")
async def get_benchmark(payload: dict):
    from app.analytics.portfolio_returns import build_portfolio_returns
    from app.analytics.benchmark import compare_portfolio_vs_benchmarks

    holdings  = _clean_holdings(payload.get("holdings", []))
    benchmark = _safe_benchmark(payload.get("benchmark", DEFAULT_BENCHMARK))

    if not holdings:
        raise HTTPException(400, "No valid holdings")

    # Cache key includes benchmark so each index gets its own result
    key    = cache.make_portfolio_key("benchmark_v3", holdings, {"bm": benchmark})
    cached = cache.get(key, cache.TTL_BENCHMARK, disk=True)
    if cached:
        logger.info(f"Benchmark cache hit: {benchmark}")
        return cached

    returns = build_portfolio_returns(holdings)

    if returns is None or len(returns) < 20:
        # Safe zeros that match the frontend's expected shape
        return _empty_benchmark(benchmark)

    try:
        result = compare_portfolio_vs_benchmarks(returns, holdings, benchmark)
    except Exception as e:
        logger.warning(f"Benchmark compute failed for {benchmark}: {e}")
        return _empty_benchmark(benchmark)

    # Validate result has the shape the frontend expects before caching
    if not isinstance(result, dict) or "portfolio_return" not in result:
        logger.warning(f"Benchmark returned unexpected shape: {list(result.keys()) if isinstance(result, dict) else type(result)}")
        return _empty_benchmark(benchmark)

    cache.set(key, result, cache.TTL_BENCHMARK, disk=True)
    return result


def _empty_benchmark(benchmark: str) -> dict:
    """
    Returns a valid zero-state response when data is unavailable.
    Shape matches exactly what BenchmarkChart.tsx expects, so the
    component renders 'Chart data unavailable' instead of crashing.
    """
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
        "data_note":         "Insufficient data or benchmark temporarily unavailable (yfinance rate limit). Try again in 30s.",
    }


# ── /simulate ────────────────────────────────────────────────

@router.post("/simulate")
async def simulate(payload: dict):
    from app.analytics.simulator import simulate_scenarios

    holdings  = payload.get("holdings", [])
    scenarios = payload.get("scenarios", None)

    if not holdings:
        raise HTTPException(400, "No holdings")

    return {"scenarios": simulate_scenarios(holdings, scenarios)}


# ── /scenarios/default ───────────────────────────────────────

@router.get("/scenarios/default")
async def default_scenarios():
    from app.analytics.simulator import DEFAULT_SCENARIOS
    return {"scenarios": DEFAULT_SCENARIOS}
