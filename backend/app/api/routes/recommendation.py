import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional
from app.recommendation.engine import generate_recommendation, infer_risk_profile
from app.cache import store as cache

logger = logging.getLogger(__name__)
router = APIRouter(default_response_class=ORJSONResponse)


class RecommendationRequest(BaseModel):
    amount:             float          = Field(..., gt=0, description="Investment amount")
    goal:               str            = Field(..., description="Investment goal")
    horizon:            str            = Field(..., description="short/medium/long")
    market:             str            = Field(default="india", description="india/us")
    exchange:           str            = Field(default="auto")
    preferred_sectors:  Optional[List[str]] = Field(default_factory=list)


class ProfileRequest(BaseModel):
    amount:            float
    goal:              str
    horizon:           str
    market:            str = "india"
    preferred_sectors: Optional[List[str]] = []


@router.post("/profile")
async def get_risk_profile(req: ProfileRequest):
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
    # Validate inputs
    valid_goals    = ["wealth_creation","passive_growth","retirement","high_growth","dividend_income","low_risk","tax_efficient","learning"]
    valid_horizons = ["short","medium","long"]
    valid_markets  = ["india","us"]

    if req.goal not in valid_goals:
        raise HTTPException(400, f"Invalid goal. Choose from: {valid_goals}")
    if req.horizon not in valid_horizons:
        raise HTTPException(400, f"Invalid horizon. Choose from: {valid_horizons}")
    if req.market not in valid_markets:
        raise HTTPException(400, f"Invalid market. Choose from: {valid_markets}")

    # Cache key
    key    = cache._make_key("rec", {
        "amt": int(req.amount / 1000),  # round to nearest 1000 for cache hit
        "goal": req.goal, "h": req.horizon,
        "mkt": req.market, "sec": sorted(req.preferred_sectors or [])
    })
    cached = cache.get(key, 1800)
    if cached:
        return cached

    result = generate_recommendation(
        amount=req.amount,
        goal=req.goal,
        horizon=req.horizon,
        market=req.market,
        exchange=req.exchange,
        preferred_sectors=req.preferred_sectors,
    )

    if "error" in result:
        raise HTTPException(503, result["error"])

    cache.set(key, result, 1800)
    return result


@router.get("/goals")
async def get_goals():
    return {
        "goals": [
            {"value": "wealth_creation",  "label": "Wealth Creation",      "icon": "📈"},
            {"value": "passive_growth",   "label": "Passive Growth",        "icon": "🌱"},
            {"value": "retirement",       "label": "Retirement Planning",   "icon": "🏖️"},
            {"value": "high_growth",      "label": "High Growth",           "icon": "🚀"},
            {"value": "dividend_income",  "label": "Dividend Income",       "icon": "💰"},
            {"value": "low_risk",         "label": "Low Risk Stability",    "icon": "🛡️"},
            {"value": "tax_efficient",    "label": "Tax-Efficient Investing","icon": "📋"},
            {"value": "learning",         "label": "Learning & Demo",       "icon": "🎓"},
        ],
        "horizons": [
            {"value": "short",  "label": "Short Term (< 1 year)",  "icon": "⚡"},
            {"value": "medium", "label": "Medium Term (1–3 years)", "icon": "📅"},
            {"value": "long",   "label": "Long Term (3+ years)",   "icon": "🏔️"},
        ],
        "sectors": [
            "Technology","Banking","Healthcare","FMCG","Energy",
            "Finance","Auto","Infra","Consumer","Pharma","ETF",
        ],
    }