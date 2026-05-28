import logging
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel, Field
from typing import List
from app.api.dependencies import get_current_user
from app.db.user_repository import PortfolioRepository

logger    = logging.getLogger(__name__)
router    = APIRouter(default_response_class=ORJSONResponse)
port_repo = PortfolioRepository()


class CreateReq(BaseModel):
    name:        str = Field(..., min_length=1, max_length=50)
    description: str = Field(default="", max_length=200)


class SaveHoldingsReq(BaseModel):
    holdings: List[dict]
    summary:  dict = {}


@router.get("")
async def list_portfolios(user: dict = Depends(get_current_user)):
    return {"portfolios": port_repo.list_for_user(user["id"])}


@router.post("", status_code=201)
async def create_portfolio(req: CreateReq, user: dict = Depends(get_current_user)):
    p = port_repo.create(user["id"], req.name, req.description)
    if not p:
        raise HTTPException(500, "Create failed")
    return p


@router.get("/{pid}")
async def get_portfolio(pid: int, user: dict = Depends(get_current_user)):
    p = port_repo.get_by_id(pid, user["id"])
    if not p:
        raise HTTPException(404, "Not found")
    return {**p, "holdings": port_repo.get_holdings(pid, user["id"])}


@router.put("/{pid}")
async def update_portfolio(pid: int, req: CreateReq, user: dict = Depends(get_current_user)):
    if not port_repo.update(pid, user["id"], req.name, req.description):
        raise HTTPException(404, "Not found")
    return port_repo.get_by_id(pid, user["id"])


@router.delete("/{pid}")
async def delete_portfolio(pid: int, user: dict = Depends(get_current_user)):
    if not port_repo.delete(pid, user["id"]):
        raise HTTPException(404, "Not found")
    return {"deleted": True}


@router.post("/{pid}/holdings")
async def save_holdings(
    pid: int, req: SaveHoldingsReq,
    bg: BackgroundTasks,
    user: dict = Depends(get_current_user),
):
    if not port_repo.get_by_id(pid, user["id"]):
        raise HTTPException(404, "Portfolio not found")
    port_repo.save_holdings(pid, req.holdings)
    bg.add_task(port_repo.save_snapshot, pid, req.summary)
    return {"saved": len(req.holdings), "portfolio_id": pid}


@router.get("/{pid}/holdings")
async def get_holdings(pid: int, user: dict = Depends(get_current_user)):
    if not port_repo.get_by_id(pid, user["id"]):
        raise HTTPException(404, "Not found")
    return {"holdings": port_repo.get_holdings(pid, user["id"])}


@router.get("/{pid}/history")
async def get_history(pid: int, days: int = 90, user: dict = Depends(get_current_user)):
    return {"snapshots": port_repo.get_snapshots(pid, user["id"], days)}