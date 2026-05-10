import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import ORJSONResponse
from app.cache import store as cache

logger = logging.getLogger(__name__)
router = APIRouter(default_response_class=ORJSONResponse)


@router.post("/advanced")
async def get_advanced(payload: dict):
    from app.analytics.portfolio_returns import build_portfolio_returns
    from app.analytics.advanced_metrics import compute_advanced_metrics

    holdings     = payload.get("holdings", [])
    risk_metrics = payload.get("risk_metrics", {})
    if not holdings:
        raise HTTPException(400, "No holdings")

    key    = cache.make_portfolio_key("advanced", holdings, risk_metrics)
    cached = cache.get(key, cache.TTL_ANALYTICS)
    if cached:
        return cached

    returns = build_portfolio_returns(holdings)
    if returns is None or returns.empty:
        raise HTTPException(422, "Could not build portfolio returns")

    result = compute_advanced_metrics(returns, holdings, risk_metrics)
    cache.set(key, result, cache.TTL_ANALYTICS)
    return result


@router.post("/benchmark")
async def get_benchmark(payload: dict):
    from app.analytics.portfolio_returns import build_portfolio_returns
    from app.analytics.benchmark import compare_portfolio_vs_benchmarks

    holdings = payload.get("holdings", [])
    if not holdings:
        raise HTTPException(400, "No holdings")

    key    = cache.make_portfolio_key("benchmark", holdings)
    cached = cache.get(key, cache.TTL_BENCHMARK, disk=True)
    if cached:
        return cached

    returns = build_portfolio_returns(holdings)
    if returns is None or returns.empty:
        raise HTTPException(422, "Could not build portfolio returns")

    result = compare_portfolio_vs_benchmarks(returns, holdings)
    cache.set(key, result, cache.TTL_BENCHMARK, disk=True)
    return result


@router.post("/simulate")
async def simulate(payload: dict):
    from app.analytics.simulator import simulate_scenarios, DEFAULT_SCENARIOS
    holdings  = payload.get("holdings", [])
    scenarios = payload.get("scenarios", None)
    if not holdings:
        raise HTTPException(400, "No holdings")
    return {"scenarios": simulate_scenarios(holdings, scenarios)}


@router.get("/scenarios/default")
async def default_scenarios():
    from app.analytics.simulator import DEFAULT_SCENARIOS
    return {"scenarios": DEFAULT_SCENARIOS}