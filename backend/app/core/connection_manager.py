import logging
import asyncio
import json
from typing import Set
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages all active WebSocket connections.
    Smart scheduler checks this to decide refresh rate.
    """

    def __init__(self):
        self._connections: Set[WebSocket] = set()

    @property
    def active_count(self) -> int:
        return len(self._connections)

    @property
    def has_active(self) -> bool:
        return len(self._connections) > 0

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._connections.add(ws)
        logger.info(
            f"WebSocket connected. "
            f"Active connections: {self.active_count}"
        )

    def disconnect(self, ws: WebSocket):
        self._connections.discard(ws)
        logger.info(
            f"WebSocket disconnected. "
            f"Active connections: {self.active_count}"
        )

    async def broadcast(self, data: dict):
        """Send price update to ALL connected clients."""
        if not self._connections:
            return

        message = json.dumps(data)
        dead = set()

        for ws in self._connections.copy():
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)

        # Clean up dead connections
        for ws in dead:
            self._connections.discard(ws)

    async def send_to(self, ws: WebSocket, data: dict):
        """Send message to ONE client."""
        try:
            await ws.send_text(json.dumps(data))
        except Exception:
            self._connections.discard(ws)


# Singleton — shared across the entire app
manager = ConnectionManager()