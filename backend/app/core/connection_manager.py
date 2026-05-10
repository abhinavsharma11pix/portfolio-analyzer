import asyncio
import json
import logging
from typing import Set, Dict, Any
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self._connections: Set[WebSocket]     = set()
        self._metadata: Dict[WebSocket, dict] = {}
        self._lock = asyncio.Lock()

    @property
    def active_count(self) -> int:
        return len(self._connections)

    @property
    def has_active(self) -> bool:
        return bool(self._connections)

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._connections.add(ws)
            self._metadata[ws] = {"connected_at": asyncio.get_event_loop().time()}
        logger.info(f"WS connected. Total: {self.active_count}")

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(ws)
            self._metadata.pop(ws, None)
        logger.info(f"WS disconnected. Total: {self.active_count}")

    async def broadcast(self, data: dict) -> int:
        """Broadcast to all clients. Returns number of successful sends."""
        if not self._connections:
            return 0

        message = json.dumps(data, default=str)
        dead: Set[WebSocket] = set()
        sent = 0

        # Snapshot to avoid mutation during iteration
        connections = set(self._connections)

        async def _send(ws: WebSocket):
            nonlocal sent
            try:
                await asyncio.wait_for(ws.send_text(message), timeout=3.0)
                sent += 1
            except Exception:
                dead.add(ws)

        await asyncio.gather(*[_send(ws) for ws in connections], return_exceptions=True)

        # Clean up dead connections
        if dead:
            async with self._lock:
                for ws in dead:
                    self._connections.discard(ws)
                    self._metadata.pop(ws, None)
            logger.info(f"Cleaned {len(dead)} dead connections")

        return sent

    async def send_to(self, ws: WebSocket, data: dict) -> bool:
        try:
            await asyncio.wait_for(
                ws.send_text(json.dumps(data, default=str)),
                timeout=3.0
            )
            return True
        except Exception:
            await self.disconnect(ws)
            return False


manager = ConnectionManager()