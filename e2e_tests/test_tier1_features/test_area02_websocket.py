"""
e2e_tests/test_tier1_features/test_area02_websocket.py
Area 2: WebSocket Streaming & Monotonicity (Feature 4)
Tier 1 Tests: Connection handshake, monotonic timestamps, banned term audit, admin channel auth, client isolation.
"""

from datetime import datetime
import pytest
from starlette.testclient import TestClient

BANNED_ML_TERMS = [
    "iforest_score", "ewma_z", "z_score", "threshold", "model_type", "feature_cols"
]


def test_a2_t1_01_public_client_websocket_connection(client: TestClient):
    """
    TEST-A2-T1-01: Public Client WebSocket Connection (/ws/client or /ws/telemetry).
    Handshake succeeds without credentials.
    """
    ws_endpoint = "/ws/client"
    try:
        with client.websocket_connect(ws_endpoint) as ws:
            assert ws is not None
    except Exception:
        # Fallback to /ws/telemetry if /ws/client is still being migrated by M1
        with client.websocket_connect("/ws/telemetry") as ws:
            ack = ws.receive_json()
            assert ack.get("type") == "connection_ack"


def test_a2_t1_02_client_stream_timestamp_monotonicity(client: TestClient):
    """
    TEST-A2-T1-02: Broadcast frames maintain monotonic timestamps over live WebSocket.
    """
    import asyncio
    from backend.routes.ws_routes import ws_manager

    with client.websocket_connect("/ws/client") as ws:
        # Broadcast out-of-order and sequential frames to live connection
        test_frames = [
            {"timestamp": "2026-11-15T10:00:05.000Z", "temperature": 24.0, "humidity": 55.0},
            {"timestamp": "2026-11-15T10:00:02.000Z", "temperature": 24.1, "humidity": 55.1},  # Clock jump backward
            {"timestamp": "2026-11-15T10:00:06.000Z", "temperature": 24.2, "humidity": 55.2},
        ]
        for f in test_frames:
            asyncio.run(ws_manager.broadcast_json(f))

        received_timestamps = []
        for _ in range(len(test_frames)):
            msg = ws.receive_json()
            received_timestamps.append(msg["timestamp"])

        parsed = [datetime.fromisoformat(ts.replace("Z", "+00:00")) for ts in received_timestamps]
        for i in range(len(parsed) - 1):
            assert parsed[i + 1] >= parsed[i], f"Monotonicity violated: {parsed[i+1]} < {parsed[i]}"


def test_a2_t1_03_client_stream_payload_technical_term_ban(client: TestClient):
    """
    TEST-A2-T1-03: Client Stream Payload Technical Term Ban.
    Broadcasts raw frame with internal ML keys and asserts they are stripped from /ws/client.
    """
    import asyncio
    from backend.routes.ws_routes import ws_manager

    with client.websocket_connect("/ws/client") as ws:
        raw_frame = {
            "timestamp": "2026-11-15T10:00:00.000Z",
            "temperature": 24.2,
            "humidity": 55.4,
            "iforest_score": -0.22,
            "ewma_z_score": 1.5,
            "z_score": 1.2,
            "threshold": -0.1768,
            "model_type": "hybrid",
            "feature_cols": ["temp", "hum"],
            "hybrid_score": 2.1,
            "is_anomaly": False,
        }
        asyncio.run(ws_manager.broadcast_json(raw_frame))
        client_frame = ws.receive_json()

        for banned in BANNED_ML_TERMS:
            assert banned not in client_frame, f"Forbidden technical key '{banned}' leaked in client frame"
        assert "temperature" in client_frame
        assert "humidity" in client_frame
        assert "status" in client_frame
        assert "anomaly_score" in client_frame
        assert "is_anomaly" in client_frame


def test_a2_t1_04_authenticated_admin_websocket_connection(client: TestClient, admin_token: str):
    """
    TEST-A2-T1-04: Authenticated Admin WebSocket Connection (/ws/admin?token=...).
    """
    try:
        with client.websocket_connect(f"/ws/admin?token={admin_token}") as ws:
            assert ws is not None
    except Exception as e:
        # If /ws/admin not yet implemented in backend, fail honestly per QA reporting
        pytest.fail(f"/ws/admin endpoint not yet implemented or failed to connect: {e}")


def test_a2_t1_05_multi_client_broadcaster_isolation(client: TestClient):
    """
    TEST-A2-T1-05: Multi-Client Broadcaster Isolation on Mid-Stream Disconnect.
    One client disconnecting does not disrupt ping/pong operations for active clients.
    """
    ws_endpoint = "/ws/telemetry"
    with client.websocket_connect(ws_endpoint) as ws_b:
        # Client A connects and immediately closes
        with client.websocket_connect(ws_endpoint) as ws_a:
            pass  # Closes ws_a

        # Drain ack if present
        try:
            ws_b.receive_json(mode="text")
        except Exception:
            pass

        # ws_b sends ping and receives pong
        ws_b.send_text('{"action": "ping"}')
        resp = ws_b.receive_json()
        assert resp.get("type") == "pong"
