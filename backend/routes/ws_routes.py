"""
backend/routes/ws_routes.py
WebSocket endpoints for real-time telemetry streaming and anomaly push notifications.
"""

from __future__ import annotations

import asyncio
import json
from typing import Dict, List, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

ws_router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast_json(self, message: dict):
        if not self.active_connections:
            return
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.add(connection)
        for dead in disconnected:
            self.active_connections.discard(dead)


ws_manager = ConnectionManager()


@ws_router.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    """
    Bidirectional WebSocket endpoint.
    Pushes live telemetry frames and anomaly alerts.
    Receives optional client heartbeat/ping or command messages.
    """
    await ws_manager.connect(websocket)
    try:
        # Send initial welcome / connection acknowledgement
        await websocket.send_json({
            "type": "connection_ack",
            "message": "Connected to IoT Telemetry WebSocket Hub",
        })
        while True:
            # Keep listening for client messages/pings
            data_text = await websocket.receive_text()
            try:
                data = json.loads(data_text)
                if data.get("action") == "ping":
                    await websocket.send_json({"type": "pong"})
            except Exception:
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)
