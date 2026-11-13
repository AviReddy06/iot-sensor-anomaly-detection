"""
backend/routes/ws_routes.py
WebSocket endpoints for live client and admin telemetry streaming.
/ws/client broadcasts client-safe readings without internal model scores.
/ws/admin requires authentication token and streams full inference diagnostics.
"""

from __future__ import annotations
import asyncio
import json
from typing import Any, Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.auth import verify_signed_token
from backend.config import ADMIN_PASSWORD
from backend.services.serial_service import serial_service

router = APIRouter(tags=["websockets"])


class WebSocketHub:
    def __init__(self):
        # Step 1: Active WebSocket connection sets
        self.client_sockets: Set[WebSocket] = set()
        self.admin_sockets: Set[WebSocket] = set()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        # Step 2: Register serial service callback
        serial_service.add_listener(self.broadcast_sync)

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def broadcast_sync(self, payload: Dict[str, Any]) -> None:
        # Step 1: Schedule async broadcast on event loop
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self.broadcast(payload), self._loop)

    async def connect_client(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.client_sockets.add(websocket)

    def disconnect_client(self, websocket: WebSocket) -> None:
        self.client_sockets.discard(websocket)

    async def connect_admin(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.admin_sockets.add(websocket)

    def disconnect_admin(self, websocket: WebSocket) -> None:
        self.admin_sockets.discard(websocket)

    async def broadcast(self, payload: Dict[str, Any]) -> None:
        # Step 1: Create client-safe payload (NO scores, z-scores, or model internals)
        client_payload = {
            "type": "reading",
            "timestamp": payload["timestamp"],
            "temperature": payload["temperature"],
            "humidity": payload["humidity"],
            "is_simulated": payload["is_simulated"],
            "source": payload.get("source_label", "Live"),
            "event": payload.get("closed_event"),
        }
        client_msg = json.dumps(client_payload)

        # Step 2: Send to client connections
        dead_clients = set()
        for ws in self.client_sockets:
            try:
                await ws.send_text(client_msg)
            except Exception:
                dead_clients.add(ws)
        self.client_sockets.difference_update(dead_clients)

        # Step 3: Create full diagnostic payload for admin
        admin_payload = {
            "type": "telemetry",
            **payload,
        }
        admin_msg = json.dumps(admin_payload)

        # Step 4: Send to admin connections
        dead_admins = set()
        for ws in self.admin_sockets:
            try:
                await ws.send_text(admin_msg)
            except Exception:
                dead_admins.add(ws)
        self.admin_sockets.difference_update(dead_admins)


hub = WebSocketHub()


@router.websocket("/ws/client")
async def websocket_client_endpoint(websocket: WebSocket):
    # Step 1: Connect public client
    await hub.connect_client(websocket)
    try:
        while True:
            # Client heartbeats
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        hub.disconnect_client(websocket)


@router.websocket("/ws/admin")
async def websocket_admin_endpoint(websocket: WebSocket):
    # Step 1: Check token query parameter
    token = websocket.query_params.get("token")
    if not ADMIN_PASSWORD or not token or not verify_signed_token(token):
        await websocket.close(code=4001, reason="Unauthorized admin token")
        return

    # Step 2: Connect authenticated admin
    await hub.connect_admin(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        hub.disconnect_admin(websocket)
