import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import ORJSONResponse
from app.cache import store as cache
from app.cache.symbol_cache import is_delisted

logger = logging.getLogger(__name__)
router = APIRouter(default_response_class=ORJSONResponse)


def _clean_holdings(holdings: list) -> list:
    """Remove delisted symbols before analytics."""
    return [h for h in holdings if not is_delisted(h.get("symbol",""))]


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
        # Return empty advanced metrics rather than 422
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


@router.post("/benchmark")
async def get_benchmark(payload: dict):
    from app.analytics.portfolio_returns import build_portfolio_returns
    from app.analytics.benchmark import compare_portfolio_vs_benchmarks

    holdings = _clean_holdings(payload.get("holdings", []))
    if not holdings:
        raise HTTPException(400, "No valid holdings")

    key    = cache.make_portfolio_key("benchmark_v2", holdings)
    cached = cache.get(key, cache.TTL_BENCHMARK, disk=True)
    if cached:
        return cached

    returns = build_portfolio_returns(holdings)
    if returns is None or len(returns) < 20:
        return {
            "error":     "Insufficient data for benchmark comparison",
            "data_note": "One or more symbols may be delisted or unavailable",
            "benchmarks": [],
        }

    result = compare_portfolio_vs_benchmarks(returns, holdings)
    cache.set(key, result, cache.TTL_BENCHMARK, disk=True)
    return result


@router.post("/simulate")
async def simulate(payload: dict):
    from app.analytics.simulator import simulate_scenarios
    holdings  = payload.get("holdings", [])
    scenarios = payload.get("scenarios", None)
    if not holdings:
        raise HTTPException(400, "No holdings")
    return {"scenarios": simulate_scenarios(holdings, scenarios)}


@router.get("/scenarios/default")
async def default_scenarios():
    from app.analytics.simulator import DEFAULT_SCENARIOS
    return {"scenarios": DEFAULT_SCENARIOS}