import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional
from app.cache import store as cache

logger = logging.getLogger(__name__)
router = APIRouter(default_response_class=ORJSONResponse)

VALID_GOALS    = ["wealth_creation","passive_growth","retirement","high_growth",
                  "dividend_income","low_risk","tax_efficient","learning"]
VALID_HORIZONS = ["short","medium","long"]
VALID_MARKETS  = ["india","us"]


class RecommendationRequest(BaseModel):
    amount:             float       = Field(..., gt=0)
    goal:               str
    horizon:            str
    market:             str         = "india"
    exchange:           str         = "auto"
    preferred_sectors:  Optional[List[str]] = Field(default_factory=list)
    n_stocks_min:       int         = Field(default=5,  ge=3,  le=20)
    n_stocks_max:       int         = Field(default=10, ge=3,  le=20)

    def validate_stock_range(self):
        if self.n_stocks_min > self.n_stocks_max:
            raise ValueError("n_stocks_min must be <= n_stocks_max")


class ProfileRequest(BaseModel):
    amount:            float
    goal:              str
    horizon:           str
    market:            str = "india"
    preferred_sectors: Optional[List[str]] = []


@router.post("/profile")
async def get_risk_profile(req: ProfileRequest):
    from app.recommendation.engine import infer_risk_profile
    profile = infer_risk_profile(
        req.amount, req.goal, req.horizon, req.market, req.preferred_sectors or []
    )
    return {
        "category":          profile.category,
        "confidence":        profile.confidence,
        "explanation":       profile.explanation,
        "equity_pct":        profile.equity_pct,
        "etf_pct":           profile.etf_pct,
        "volatility_target": profile.volatility_target,
    }


@router.post("/generate")
async def generate(req: RecommendationRequest):
    if req.goal    not in VALID_GOALS:
        raise HTTPException(400, f"Invalid goal: {req.goal}")
    if req.horizon not in VALID_HORIZONS:
        raise HTTPException(400, f"Invalid horizon: {req.horizon}")
    if req.market  not in VALID_MARKETS:
        raise HTTPException(400, f"Invalid market: {req.market}")
    if req.n_stocks_min > req.n_stocks_max:
        raise HTTPException(400, "n_stocks_min must be <= n_stocks_max")

    from app.recommendation.engine import generate_recommendation
    result = generate_recommendation(
        amount=req.amount,
        goal=req.goal,
        horizon=req.horizon,
        market=req.market,
        exchange=req.exchange,
        preferred_sectors=req.preferred_sectors or [],
        n_stocks_min=req.n_stocks_min,
        n_stocks_max=req.n_stocks_max,
    )

    if "error" in result:
        raise HTTPException(503, result["error"])

    return result


@router.get("/goals")
async def get_goals():
    return {
        "goals": [
            {"value": "wealth_creation",  "label": "Wealth Creation",       "icon": "📈"},
            {"value": "passive_growth",   "label": "Passive Growth",         "icon": "🌱"},
            {"value": "retirement",       "label": "Retirement Planning",    "icon": "🏖️"},
            {"value": "high_growth",      "label": "High Growth",            "icon": "🚀"},
            {"value": "dividend_income",  "label": "Dividend Income",        "icon": "💰"},
            {"value": "low_risk",         "label": "Capital Protection",     "icon": "🛡️"},
            {"value": "tax_efficient",    "label": "Tax-Efficient Investing", "icon": "📋"},
            {"value": "learning",         "label": "Learning & Demo",        "icon": "🎓"},
        ],
        "horizons": [
            {"value": "short",  "label": "Short Term (< 1 year)",  "icon": "⚡"},
            {"value": "medium", "label": "Medium Term (1–3 years)", "icon": "📅"},
            {"value": "long",   "label": "Long Term (3+ years)",   "icon": "🏔️"},
        ],
        "markets": [
            {"value": "india", "label": "India (NSE/BSE)", "flag": "🇮🇳"},
            {"value": "us",    "label": "US (NYSE/NASDAQ)", "flag": "🇺🇸"},
        ],
        "sectors": {
            "india": ["Technology","Banking","Healthcare","FMCG","Energy",
                      "Finance","Auto","Infra","Consumer","Pharma","Defense","IT","Metals"],
            "us":    ["Technology","Finance","Healthcare","Consumer","Energy",
                      "Infra","Metals","ETF"],
        },
    }


@router.delete("/cache")
async def clear_rec_cache():
    """Clear recommendation cache — force fresh data."""
    from app.cache.store import _disk
    cleared = 0
    try:
        for key in list(_disk):
            if "rec_v3" in str(key) or "scores" in str(key) or "nse_universe" in str(key):
                _disk.delete(key)
                cleared += 1
    except Exception:
        pass
    return {"cleared": cleared}