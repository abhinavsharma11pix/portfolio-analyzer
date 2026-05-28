import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel
from typing import List
from app.fundamental.fetcher import fetch_fundamentals, fetch_fundamentals_batch

logger = logging.getLogger(__name__)
router = APIRouter(default_response_class=ORJSONResponse)


@router.get("/{symbol}")
async def get_fundamentals(symbol: str):
    symbol = symbol.upper().strip()
    data   = fetch_fundamentals(symbol)
    if data.get("fundamental_summary") == "No fundamental data available":
        raise HTTPException(404, f"No fundamental data for {symbol}")
    return data


class BatchRequest(BaseModel):
    symbols: List[str]


@router.post("/batch")
async def get_fundamentals_batch(req: BatchRequest):
    if len(req.symbols) > 20:
        raise HTTPException(400, "Max 20 symbols per batch")
    symbols = [s.upper().strip() for s in req.symbols]
    return {"fundamentals": fetch_fundamentals_batch(symbols)}


@router.get("/{symbol}/summary")
async def get_summary(symbol: str):
    symbol = symbol.upper().strip()
    data   = fetch_fundamentals(symbol)
    return {
        "symbol":               data["symbol"],
        "name":                 data.get("name"),
        "grade":                data.get("fundamental_grade"),
        "composite":            data.get("composite_fundamental"),
        "valuation_score":      data.get("valuation_score"),
        "quality_score":        data.get("quality_score"),
        "growth_score":         data.get("growth_score"),
        "pe_ratio":             data.get("pe_ratio"),
        "pb_ratio":             data.get("pb_ratio"),
        "return_on_equity":     data.get("return_on_equity"),
        "profit_margin":        data.get("profit_margin"),
        "revenue_growth":       data.get("revenue_growth"),
        "dividend_yield":       data.get("dividend_yield"),
        "analyst_rating":       data.get("analyst_rating"),
        "target_price":         data.get("target_price"),
        "52w_high":             data.get("52w_high"),
        "52w_low":              data.get("52w_low"),
        "fundamental_summary":  data.get("fundamental_summary"),
    }