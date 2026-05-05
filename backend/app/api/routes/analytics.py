import logging
from fastapi import APIRouter, HTTPException
from app.analytics.portfolio_returns import build_portfolio_returns
from app.analytics.advanced_metrics import compute_advanced_metrics
from app.analytics.benchmark import compare_portfolio_vs_benchmarks
from app.analytics.simulator import simulate_scenarios, DEFAULT_SCENARIOS

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/advanced")
async def get_advanced_metrics(payload: dict):
    """VaR, CVaR, Alpha, Regime Detection, Factor Exposure."""
    holdings    = payload.get("holdings", [])
    risk_metrics = payload.get("risk_metrics", {})

    if not holdings:
        raise HTTPException(status_code=400, detail="No holdings")

    returns = build_portfolio_returns(holdings)
    if returns is None or returns.empty:
        raise HTTPException(
            status_code=422,
            detail="Could not build portfolio returns"
        )

    result = compute_advanced_metrics(returns, holdings, risk_metrics)
    return result


@router.post("/benchmark")
async def get_benchmark_comparison(payload: dict):
    """Compare portfolio vs Nifty 50, S&P 500, Sensex."""
    holdings = payload.get("holdings", [])

    if not holdings:
        raise HTTPException(status_code=400, detail="No holdings")

    returns = build_portfolio_returns(holdings)
    if returns is None or returns.empty:
        raise HTTPException(
            status_code=422,
            detail="Could not build portfolio returns"
        )

    result = compare_portfolio_vs_benchmarks(returns, holdings)
    return result


@router.post("/simulate")
async def simulate_crash(payload: dict):
    """Simulate portfolio under crash scenarios."""
    holdings  = payload.get("holdings", [])
    scenarios = payload.get("scenarios", None)

    if not holdings:
        raise HTTPException(status_code=400, detail="No holdings")

    result = simulate_scenarios(holdings, scenarios)
    return {"scenarios": result}


@router.get("/scenarios/default")
async def get_default_scenarios():
    """Return available crash scenarios."""
    return {"scenarios": DEFAULT_SCENARIOS}