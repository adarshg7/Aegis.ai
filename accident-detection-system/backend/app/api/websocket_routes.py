"""
WebSocket API endpoints.
/ws/gov      – Government dashboard real-time feed
/ws/drivers  – Driver PWA real-time feed
/ws/incident/{id} – Per-incident watchers
"""
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from jose import JWTError

from app.core.security import decode_token
from app.websocket.manager import ws_manager
import structlog

log = structlog.get_logger(__name__)
router = APIRouter(tags=["WebSocket"])


async def _auth_ws(token: str) -> dict:
    try:
        payload = decode_token(token)
        return payload
    except (JWTError, HTTPException):
        return {}


@router.websocket("/ws/gov")
async def gov_websocket(
    websocket: WebSocket,
    token: str = Query(...),
):
    payload = await _auth_ws(token)
    if not payload or payload.get("role") not in ("GOVERNMENT", "ADMIN"):
        await websocket.close(code=4001, reason="Unauthorized")
        return

    user_id = payload["sub"]
    await ws_manager.connect(websocket, "gov", user_id, payload["role"])
    try:
        # Send connection ACK
        await websocket.send_json({
            "type": "connected",
            "payload": {"room": "gov", "user_id": user_id},
        })
        # Keep alive – receive ping/pong from client
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        await ws_manager.disconnect(websocket)


@router.websocket("/ws/drivers")
async def driver_websocket(
    websocket: WebSocket,
    token: str = Query(...),
):
    payload = await _auth_ws(token)
    if not payload:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    user_id = payload["sub"]
    await ws_manager.connect(websocket, "drivers", user_id, payload.get("role", "DRIVER"))
    try:
        await websocket.send_json({
            "type": "connected",
            "payload": {"room": "drivers", "user_id": user_id},
        })
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            elif msg.get("type") == "location.update":
                # Update location in Redis for geofencing
                loc = msg.get("payload", {})
                lat = loc.get("lat")
                lon = loc.get("lon")
                log.debug("driver.location.update", user_id=user_id, lat=lat, lon=lon)
    except WebSocketDisconnect:
        pass
    finally:
        await ws_manager.disconnect(websocket)


@router.websocket("/ws/incident/{incident_id}")
async def incident_websocket(
    websocket: WebSocket,
    incident_id: str,
    token: str = Query(...),
):
    payload = await _auth_ws(token)
    if not payload:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    room = f"incident:{incident_id}"
    await ws_manager.connect(websocket, room, payload["sub"], payload.get("role"))
    try:
        await websocket.send_json({"type": "connected", "payload": {"room": room}})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await ws_manager.disconnect(websocket)


@router.get("/ws/stats")
async def ws_stats():
    return {
        "active_connections": ws_manager.active_connections_count,
        "rooms": ws_manager.room_stats(),
    }
