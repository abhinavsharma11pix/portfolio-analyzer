import logging
import time
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel
from typing import List, Optional
from app.api.dependencies import get_optional_user
from app.alerts.engine import alert_engine, ALERT_TYPES
from app.core.database import get_connection

logger = logging.getLogger(__name__)
router = APIRouter(default_response_class=ORJSONResponse)

# Simple in-memory cache for unread count — avoids hammering SQLite
_unread_cache: dict = {"count": 0, "ts": 0.0}
UNREAD_TTL = 15  # seconds


@router.get("/unread-count")
async def unread_count():
    """Cached unread count — never blocks."""
    now = time.monotonic()
    if now - _unread_cache["ts"] < UNREAD_TTL:
        return {"count": _unread_cache["count"]}
    try:
        conn  = get_connection()
        count = conn.execute(
            "SELECT COUNT(*) FROM alert_history WHERE is_read=0"
        ).fetchone()[0]
        conn.close()
        _unread_cache["count"] = count
        _unread_cache["ts"]    = now
        return {"count": count}
    except Exception:
        # Table may not exist yet — return 0 silently
        return {"count": 0}


@router.get("/types")
async def get_alert_types():
    return {
        "types": [
            {"value": k, "label": v, "description": _type_desc(k)}
            for k, v in ALERT_TYPES.items()
        ]
    }


@router.post("/rules", status_code=201)
async def create_rule(
    req:  dict,
    user: dict = Depends(get_optional_user),
):
    valid = list(ALERT_TYPES.keys())
    if req.get("alert_type") not in valid:
        raise HTTPException(400, f"Invalid alert_type. Choose: {valid}")
    try:
        conn = get_connection()
        cur  = conn.execute(
            """INSERT INTO alert_rules
               (user_id, symbol, alert_type, threshold, direction, notify_email)
               VALUES (?,?,?,?,?,?)""",
            (
                user["id"] if user else None,
                req.get("symbol","").upper(),
                req.get("alert_type"),
                req.get("threshold", 0),
                req.get("direction", "both"),
                1 if req.get("notify_email") else 0,
            )
        )
        conn.commit()
        rule_id = cur.lastrowid
        row     = conn.execute(
            "SELECT * FROM alert_rules WHERE id=?", (rule_id,)
        ).fetchone()
        conn.close()
        return dict(row)
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/rules")
async def list_rules(user: dict = Depends(get_optional_user)):
    try:
        conn = get_connection()
        uid  = user["id"] if user else None
        rows = conn.execute(
            "SELECT * FROM alert_rules WHERE user_id=? AND is_active=1 ORDER BY created_at DESC",
            (uid,)
        ).fetchall()
        conn.close()
        return {"rules": [dict(r) for r in rows]}
    except Exception:
        return {"rules": []}


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: int, user: dict = Depends(get_optional_user)):
    try:
        conn = get_connection()
        uid  = user["id"] if user else None
        cur  = conn.execute(
            "UPDATE alert_rules SET is_active=0 WHERE id=? AND user_id=?",
            (rule_id, uid)
        )
        conn.commit()
        conn.close()
        if cur.rowcount == 0:
            raise HTTPException(404, "Rule not found")
        return {"deleted": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/history")
async def get_history(
    limit:  int  = Query(default=50, le=200),
    unread: bool = Query(default=False),
):
    try:
        conn  = get_connection()
        where = "WHERE is_read=0" if unread else ""
        rows  = conn.execute(
            f"SELECT * FROM alert_history {where} ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        count = conn.execute(
            "SELECT COUNT(*) FROM alert_history WHERE is_read=0"
        ).fetchone()[0]
        conn.close()
        _unread_cache["count"] = count
        _unread_cache["ts"]    = time.monotonic()
        return {"alerts": [dict(r) for r in rows], "unread_count": count}
    except Exception:
        return {"alerts": [], "unread_count": 0}


@router.post("/mark-read")
async def mark_read(req: dict):
    try:
        if req.get("all"):
            alert_engine.mark_all_read()
        else:
            alert_engine.mark_read(req.get("alert_ids", []))
        _unread_cache["count"] = 0
        _unread_cache["ts"]    = time.monotonic()
    except Exception:
        pass
    return {"done": True}


def _type_desc(t: str) -> str:
    return {
        "price_above":    "Alert when price rises above a target",
        "price_below":    "Alert when price falls below a level",
        "price_up_pct":   "Alert when stock is up X% from your buy price",
        "price_down_pct": "Alert when stock is down X% from your buy price",
    }.get(t, "")