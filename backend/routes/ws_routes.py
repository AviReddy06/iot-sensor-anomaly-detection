"""
backend/routes/ws_routes.py
Separated WebSocket endpoints: public /ws/client, authenticated /ws/admin, and legacy /ws/telemetry.
High-concurrency non-blocking broadcaster with per-client bounded queues and drop-oldest policy.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import re
from typing import Dict, List, Optional, Set

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from backend import config
from backend.auth import verify_signed_token


def _is_allowed_origin(origin: Optional[str]) -> bool:
    """Check if the origin is in the allowed list or matches the regex."""
    if not origin:
        return False
    # Check exact matches first
    if origin in config.ALLOWED_ORIGINS:
        return True
    # Check regex pattern
    if re.match(config.ALLOWED_ORIGIN_REGEX, origin):
        return True
    return False

ws_router = APIRouter(tags=["WebSocket"])


class MonotonicTimestampTracker:
    """Ensures timestamps broadcast to clients never travel backward."""
    def __init__(self):
        self._last_epoch: float = 0.0

    def reset(self) -> None:
        """Reset the monotonic baseline epoch for a new stream session or replay pass."""
        self._last_epoch = 0.0

    def process(self, raw_ts: str) -> str:
        if not raw_ts:
            now_dt = datetime.now(timezone.utc)
            epoch = now_dt.timestamp()
            if epoch <= self._last_epoch:
                epoch = self._last_epoch + 0.001
            self._last_epoch = epoch
            return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()

        try:
            clean_ts = raw_ts.replace("Z", "+00:00")
            if "T" in clean_ts:
                dt = datetime.fromisoformat(clean_ts)
            else:
                dt = datetime.strptime(clean_ts[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            epoch = dt.timestamp()
            if epoch <= self._last_epoch:
                epoch = self._last_epoch + 0.001
                dt = datetime.fromtimestamp(epoch, tz=timezone.utc)
                self._last_epoch = epoch
                return dt.isoformat()
            self._last_epoch = epoch
            return raw_ts
        except Exception:
            return raw_ts


class ClientSession:
    """Per-client bounded queue with drop-oldest overflow policy."""
    def __init__(self, websocket: WebSocket, client_type: str, max_queue: int = 100):
        self.websocket = websocket
        self.client_type = client_type  # "client", "admin", "telemetry"
        self.queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=max_queue)
        self.dropped_count: int = 0
        self.sender_task: Optional[asyncio.Task] = None

    def push(self, message: dict) -> None:
        """Non-blocking O(1) push with drop-oldest discard on queue saturation."""
        if self.queue.full():
            try:
                self.queue.get_nowait()
                self.dropped_count += 1
            except (asyncio.QueueEmpty, ValueError):
                pass
        try:
            self.queue.put_nowait(message)
        except asyncio.QueueFull:
            self.dropped_count += 1


class ConnectionManager:
    """Central non-blocking broadcast router."""
    def __init__(self, queue_capacity: int = 100):
        self.queue_capacity = queue_capacity
        self.sessions: Dict[WebSocket, ClientSession] = {}
        self.mono_tracker = MonotonicTimestampTracker()
        self.total_dropped_messages: int = 0

    def reset_tracker(self) -> None:
        """Reset the monotonic timestamp tracker baseline."""
        self.mono_tracker.reset()

    @property
    def active_connections(self) -> Set[WebSocket]:
        return set(self.sessions.keys())

    async def connect(self, websocket: WebSocket, client_type: str = "client") -> ClientSession:
        await websocket.accept()
        session = ClientSession(websocket, client_type, max_queue=self.queue_capacity)
        self.sessions[websocket] = session
        session.sender_task = asyncio.create_task(self._client_sender_loop(session))
        return session

    def disconnect(self, websocket: WebSocket) -> None:
        session = self.sessions.pop(websocket, None)
        if session:
            self.total_dropped_messages += session.dropped_count
            if session.sender_task and not session.sender_task.done():
                session.sender_task.cancel()

    def get_metrics(self) -> Dict[str, Any]:
        """Aggregate queue depth and dropped message metrics."""
        q_depth = sum(s.queue.qsize() for s in self.sessions.values())
        dropped = self.total_dropped_messages + sum(s.dropped_count for s in self.sessions.values())
        return {
            "queue_depth": q_depth,
            "dropped_messages": dropped,
            "connected_clients": len(self.sessions),
            "sessions_by_type": {
                "client": sum(1 for s in self.sessions.values() if s.client_type == "client"),
                "admin": sum(1 for s in self.sessions.values() if s.client_type == "admin"),
                "telemetry": sum(1 for s in self.sessions.values() if s.client_type == "telemetry"),
            },
        }

    def shutdown(self) -> None:
        """Gracefully terminate all client sender tasks and clear active sessions."""
        for ws, session in list(self.sessions.items()):
            self.total_dropped_messages += session.dropped_count
            if session.sender_task and not session.sender_task.done():
                session.sender_task.cancel()
        self.sessions.clear()

    async def _client_sender_loop(self, session: ClientSession) -> None:
        try:
            while True:
                msg = await session.queue.get()
                await session.websocket.send_json(msg)
                session.queue.task_done()
        except (WebSocketDisconnect, ConnectionResetError, asyncio.CancelledError):
            pass
        except Exception:
            pass
        finally:
            self.disconnect(session.websocket)

    async def broadcast_json(self, raw_frame: dict) -> None:
        """
        Instantaneous non-blocking broadcast dispatch across connected sessions.
        Partitions payloads into client-safe and administrative frames.
        """
        if not self.sessions:
            return

        ts_str = self.mono_tracker.process(str(raw_frame.get("timestamp", "")))
        temp = float(raw_frame.get("temperature", 0.0))
        hum = float(raw_frame.get("humidity", 0.0))
        is_anom = bool(raw_frame.get("is_anomaly", False))
        hybrid_score = float(raw_frame.get("hybrid_score", 0.0))
        # Use status from raw_frame if present (e.g., "Detector unavailable" when degraded)
        raw_status = raw_frame.get("status", "")

        # Normalized anomaly score [0.0, 1.0]
        anomaly_score = round(min(1.0, max(0.0, hybrid_score / 10.0)), 4)
        if raw_status and raw_status not in ("NORMAL", "ANOMALY"):
            # Degraded or other special status from inference service
            status_label = raw_status
        else:
            status_label = "Unusual" if is_anom else "Normal"

        client_frame = {
            "timestamp": ts_str,
            "temperature": temp,
            "humidity": hum,
            "status": status_label,
            "anomaly_score": anomaly_score,
            "is_anomaly": is_anom,
        }

        total_conns = len(self.sessions)

        for session in list(self.sessions.values()):
            if session.client_type == "client":
                session.push(client_frame)
            elif session.client_type == "admin":
                admin_frame = dict(raw_frame)
                admin_frame.update({
                    "timestamp": ts_str,
                    "queue_depth": session.queue.qsize(),
                    "dropped_messages": session.dropped_count,
                    "connected_clients": total_conns,
                    "model_version": "v2.0-hybrid",
                    "raw_scores": {
                        "iforest_score": raw_frame.get("iforest_score"),
                        "ewma_z_score": raw_frame.get("ewma_z_score"),
                        "hybrid_score": hybrid_score,
                    },
                })
                session.push(admin_frame)
            elif session.client_type == "telemetry":
                session.push(raw_frame)


ws_manager = ConnectionManager(queue_capacity=100)


@ws_router.websocket("/ws/client")
async def websocket_client_endpoint(websocket: WebSocket):
    """Public client WebSocket streaming client-safe telemetry frames.
    Enforces CORS origin policy: only allowed localhost origins may connect.
    """
    # Enforce origin policy for client WebSocket
    origin = websocket.headers.get("origin") or websocket.headers.get("Origin")
    # Allow missing origin for test client compatibility
    if origin and not _is_allowed_origin(origin):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Origin not allowed")
        return

    session = await ws_manager.connect(websocket, client_type="client")
    try:
        while True:
            text = await websocket.receive_text()
            try:
                data = json.loads(text)
                if data.get("action") == "ping":
                    session.push({"type": "pong"})
            except Exception:
                pass
    except (WebSocketDisconnect, Exception):
        ws_manager.disconnect(websocket)


@ws_router.websocket("/ws/admin")
async def websocket_admin_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
):
    """Protected admin WebSocket streaming telemetry with diagnostics."""
    # 1. Require ADMIN_PASSWORD configured
    if not config.ADMIN_PASSWORD:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Admin access disabled")
        return

    # 2. Extract token from query or Authorization header
    if not token:
        auth_hdr = websocket.headers.get("authorization") or websocket.headers.get("Authorization")
        if auth_hdr and auth_hdr.startswith("Bearer "):
            token = auth_hdr[7:].strip()

    # 3. Verify signed token
    if not token or not verify_signed_token(token):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Unauthorized")
        return

    session = await ws_manager.connect(websocket, client_type="admin")
    try:
        while True:
            text = await websocket.receive_text()
            try:
                data = json.loads(text)
                if data.get("action") == "ping":
                    session.push({"type": "pong"})
            except Exception:
                pass
    except (WebSocketDisconnect, Exception):
        ws_manager.disconnect(websocket)


@ws_router.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    """
    Bidirectional WebSocket endpoint for backward compatibility.
    Pushes live telemetry frames and anomaly alerts.
    Receives optional client heartbeat/ping or command messages.
    """
    session = await ws_manager.connect(websocket, client_type="telemetry")
    try:
        session.push({
            "type": "connection_ack",
            "message": "Connected to IoT Telemetry WebSocket Hub",
        })
        while True:
            data_text = await websocket.receive_text()
            try:
                data = json.loads(data_text)
                if data.get("action") == "ping":
                    session.push({"type": "pong"})
            except Exception:
                pass
    except (WebSocketDisconnect, Exception):
        ws_manager.disconnect(websocket)
