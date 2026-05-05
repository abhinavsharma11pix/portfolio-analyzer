import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.connection_manager import manager
from app.core.price_broadcaster import set_tracked_symbols, set_baseline

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/prices")
async def websocket_prices(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "subscribe":
                symbols   = data.get("symbols", [])
                baselines = data.get("baselines", {})
                if symbols:
                    set_tracked_symbols(symbols)
                    set_baseline(baselines)
                    await manager.send_to(websocket, {
                        "type":    "subscribed",
                        "symbols": symbols,
                    })
            elif data.get("type") == "ping":
                await manager.send_to(websocket, {
                    "type":      "pong",
                    "timestamp": data.get("timestamp"),
                })
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)