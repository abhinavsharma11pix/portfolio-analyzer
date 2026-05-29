import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional
from app.api.dependencies import get_current_user, get_optional_user
from app.alerts.engine import alert_engine, ALERT_TYPES
from app.core.database import get_connection

logger = logging.getLogger(__name__)
router = APIRouter(default_response_class=ORJSONResponse)


class CreateAlertRequest(BaseModel):
    symbol:       str
    alert_type:   str
    threshold:    float
    direction:    str  = "both"
    notify_email: bool = False


class MarkReadRequest(BaseModel):
    alert_ids: List[int] = []
    all:       bool      = False


@router.get("/types")
async def get_alert_types():
    return {
        "types": [
            {"value": k, "label": v,
             "description": _type_desc(k)}
            for k, v in ALERT_TYPES.items()
        ]
    }


@router.post("/rules", status_code=201)
async def create_rule(
    req:  CreateAlertRequest,
    user: dict = Depends(get_optional_user),
):
    valid = list(ALERT_TYPES.keys())
    if req.alert_type not in valid:
        raise HTTPException(400, f"Invalid alert_type. Choose: {valid}")

    conn = get_connection()
    try:
        cur = conn.execute(
            """INSERT INTO alert_rules
               (user_id, symbol, alert_type, threshold, direction, notify_email)
               VALUES (?,?,?,?,?,?)""",
            (
                user["id"] if user else None,
                req.symbol.upper(), req.alert_type,
                req.threshold, req.direction,
                1 if req.notify_email else 0,
            )
        )
        conn.commit()
        rule_id = cur.lastrowid
        row     = conn.execute(
            "SELECT * FROM alert_rules WHERE id=?", (rule_id,)
        ).fetchone()
        return dict(row)
    finally:
        conn.close()


@router.get("/rules")
async def list_rules(user: dict = Depends(get_optional_user)):
    conn = get_connection()
    try:
        uid  = user["id"] if user else None
        rows = conn.execute(
            "SELECT * FROM alert_rules WHERE user_id=? AND is_active=1 ORDER BY created_at DESC",
            (uid,)
        ).fetchall()
        return {"rules": [dict(r) for r in rows]}
    finally:
        conn.close()


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: int, user: dict = Depends(get_optional_user)):
    conn = get_connection()
    try:
        uid = user["id"] if user else None
        cur = conn.execute(
            "UPDATE alert_rules SET is_active=0 WHERE id=? AND user_id=?",
            (rule_id, uid)
        )
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(404, "Rule not found")
        return {"deleted": True}
    finally:
        conn.close()


@router.get("/history")
async def get_history(
    limit:    int  = Query(default=50, le=200),
    unread:   bool = Query(default=False),
    user:     dict = Depends(get_optional_user),
):
    conn = get_connection()
    try:
        where = "WHERE is_read=0" if unread else ""
        rows  = conn.execute(
            f"SELECT * FROM alert_history {where} ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        unread_count = conn.execute(
            "SELECT COUNT(*) FROM alert_history WHERE is_read=0"
        ).fetchone()[0]
        return {
            "alerts":       [dict(r) for r in rows],
            "unread_count": unread_count,
        }
    finally:
        conn.close()


@router.post("/mark-read")
async def mark_read(req: MarkReadRequest):
    if req.all:
        alert_engine.mark_all_read()
    else:
        alert_engine.mark_read(req.alert_ids)
    return {"done": True}


@router.get("/unread-count")
async def unread_count():
    conn = get_connection()
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM alert_history WHERE is_read=0"
        ).fetchone()[0]
        return {"count": count}
    finally:
        conn.close()


def _type_desc(t: str) -> str:
    descs = {
        "price_above":    "Alert when price rises above a target",
        "price_below":    "Alert when price falls below a level",
        "price_up_pct":   "Alert when stock is up X% from your buy price",
        "price_down_pct": "Alert when stock is down X% from your buy price (stop loss)",
        "pnl_positive":   "Alert when portfolio turns profitable",
        "pnl_negative":   "Alert when portfolio loss exceeds threshold",
    }
    return descs.get(t, "")