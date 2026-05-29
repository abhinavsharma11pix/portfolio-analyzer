import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel
from typing import List, Optional
from app.tax.engine import calculate_tax

logger = logging.getLogger(__name__)
router = APIRouter(default_response_class=ORJSONResponse)


class TaxRequest(BaseModel):
    holdings:  List[dict]
    trades:    Optional[List[dict]] = None
    target_fy: Optional[str]       = None


class TradeEntry(BaseModel):
    symbol:     str
    trade_type: str   # BUY or SELL
    quantity:   float
    price:      float
    trade_date: str   # YYYY-MM-DD
    exchange:   str   = "NSE"


@router.post("/calculate")
async def calculate(req: TaxRequest):
    if not req.holdings:
        raise HTTPException(400, "No holdings provided")

    result = calculate_tax(
        holdings=req.holdings,
        trades=req.trades or [],
        target_fy=req.target_fy,
    )
    return result


@router.get("/rates")
async def get_rates():
    """Current India capital gains tax rates."""
    return {
        "fy":        "2024-25",
        "effective": "July 23, 2024 onwards (Union Budget 2024)",
        "equity_listed": {
            "stcg": {
                "rate":          "20%",
                "holding_period": "Less than 12 months",
                "with_cess":     "20.8%",
                "note":          "Increased from 15% in Budget 2024",
            },
            "ltcg": {
                "rate":             "12.5%",
                "holding_period":   "12 months or more",
                "exemption":        "₹1,25,000 per financial year",
                "with_cess":        "13%",
                "note":             "Exemption increased from ₹1L to ₹1.25L in Budget 2024",
            },
        },
        "important_notes": [
            "STT (Securities Transaction Tax) must have been paid",
            "FIFO method used for lot matching",
            "STCG losses can offset STCG gains in same FY",
            "LTCG losses can offset LTCG gains in same FY",
            "Unabsorbed losses can be carried forward 8 years",
            "No wash sale rules in India — can repurchase immediately",
            "Advance tax applicable if tax liability > ₹10,000",
        ],
    }


@router.post("/harvest-preview")
async def harvest_preview(req: TaxRequest):
    """Preview tax harvesting opportunities."""
    if not req.holdings:
        raise HTTPException(400, "No holdings")

    result = calculate_tax(req.holdings, req.trades or [], req.target_fy)
    return {
        "harvest_suggestions": result.get("harvest_suggestions", []),
        "current_stcg":        result.get("total_stcg", 0),
        "current_ltcg":        result.get("total_ltcg", 0),
        "current_tax":         result.get("total_tax_with_cess", 0),
    }