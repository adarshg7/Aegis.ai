"""
WebSocket connection manager for real-time broadcasting.
Supports rooms (gov, drivers, per-accident channels).
"""
import asyncio
import json
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Set

import structlog
from fastapi import WebSocket
from starlette.websockets import WebSocketState

log = structlog.get_logger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections grouped by room.
    Rooms: 'gov' (government dashboard), 'drivers' (all drivers),
           'incident:{accident_id}' (per-incident watchers).
    """

    def __init__(self):
        # room_id -> set of WebSocket connections
        self._rooms: Dict[str, Set[WebSocket]] = defaultdict(set)
        # WebSocket -> metadata dict
        self._metadata: Dict[WebSocket, dict] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, room: str, user_id: str, role: str):
        await websocket.accept()
        async with self._lock:
            self._rooms[room].add(websocket)
            self._metadata[websocket] = {
                "user_id": user_id,
                "role": role,
                "room": room,
                "connected_at": datetime.utcnow().isoformat(),
            }
        log.info("ws.connected", user_id=user_id, room=room)

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            meta = self._metadata.pop(websocket, {})
            room = meta.get("room")
            if room and websocket in self._rooms.get(room, set()):
                self._rooms[room].discard(websocket)
        log.info("ws.disconnected", meta=meta)

    async def broadcast_to_room(self, room: str, message: dict):
        """Send JSON message to all connections in a room."""
        payload = json.dumps(message, default=str)
        dead: List[WebSocket] = []

        async with self._lock:
            connections = set(self._rooms.get(room, set()))

        for ws in connections:
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_text(payload)
            except Exception as e:
                log.warning("ws.send.failed", error=str(e))
                dead.append(ws)

        for ws in dead:
            await self.disconnect(ws)

    async def broadcast_all(self, message: dict):
        """Broadcast to ALL connected clients across all rooms."""
        payload = json.dumps(message, default=str)
        all_ws: List[WebSocket] = []
        async with self._lock:
            for connections in self._rooms.values():
                all_ws.extend(connections)

        dead = []
        for ws in all_ws:
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_text(payload)
            except Exception:
                dead.append(ws)

        for ws in dead:
            await self.disconnect(ws)

    async def send_to_user(self, user_id: str, message: dict):
        """Send a message to a specific user's WebSocket(s)."""
        payload = json.dumps(message, default=str)
        targets = [
            ws for ws, meta in self._metadata.items()
            if meta.get("user_id") == user_id
        ]
        for ws in targets:
            try:
                await ws.send_text(payload)
            except Exception:
                await self.disconnect(ws)

    @property
    def active_connections_count(self) -> int:
        return len(self._metadata)

    def room_stats(self) -> dict:
        return {room: len(conns) for room, conns in self._rooms.items()}


# Global singleton instance
ws_manager = ConnectionManager()
