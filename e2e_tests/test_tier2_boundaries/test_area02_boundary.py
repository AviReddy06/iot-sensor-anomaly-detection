"""
e2e_tests/test_tier2_boundaries/test_area02_boundary.py
Area 2 Boundary & Corner Cases (Feature 4)
Tier 2 Tests: Admin WebSocket auth rejections, tampered/expired tokens, slow client queue bounds, ping/pong protocol.
"""

import pytest
from starlette.testclient import TestClient
from backend.app import app


def test_a2_t2_01_admin_websocket_missing_token_rejection(client: TestClient):
    """
    TEST-A2-T2-01: Admin WebSocket connection without token is rejected.
    """
    try:
        with client.websocket_connect("/ws/admin") as ws:
            pytest.fail("Connection to /ws/admin succeeded without auth token")
    except Exception as e:
        if isinstance(e, pytest.fail.Exception):
            raise
        pass


def test_a2_t2_02_admin_websocket_tampered_and_expired_token(client: TestClient):
    """
    TEST-A2-T2-02: Admin WebSocket connection with tampered or expired token is rejected.
    """
    for bad_token in ["fake_token_12345", "1000000000:bad_signature"]:
        try:
            with client.websocket_connect(f"/ws/admin?token={bad_token}") as ws:
                pytest.fail(f"Connection succeeded with invalid token: {bad_token}")
        except Exception as e:
            if isinstance(e, pytest.fail.Exception):
                raise
            pass


def test_a2_t2_03_websocket_ping_pong_protocol(client: TestClient):
    """
    TEST-A2-T2-03: WebSocket Bidirectional Ping/Pong protocol.
    Sending {"action": "ping"} receives {"type": "pong"}.
    """
    ws_endpoint = "/ws/telemetry"
    with client.websocket_connect(ws_endpoint) as ws:
        # Drain welcome message
        try:
            ws.receive_json(mode="text")
        except Exception:
            pass
        ws.send_text('{"action": "ping"}')
        resp = ws.receive_json()
        assert resp.get("type") == "pong"


def test_a2_t2_04_websocket_malformed_text_handling(client: TestClient):
    """
    TEST-A2-T2-04: Non-JSON garbled text frames are handled gracefully without socket crash.
    """
    ws_endpoint = "/ws/telemetry"
    with client.websocket_connect(ws_endpoint) as ws:
        # Drain initial connection ack
        try:
            ws.receive_json(mode="text")
        except Exception:
            pass
        # Send raw non-JSON text
        ws.send_text("this is completely invalid non-json text frame ::: !!!")
        # Send ping to confirm socket is still alive and healthy
        ws.send_text('{"action": "ping"}')
        resp = ws.receive_json()
        assert resp.get("type") == "pong"


def test_a2_t2_05_rapid_connection_teardown(client: TestClient):
    """
    TEST-A2-T2-05: Rapid connection and immediate closure does not lock socket worker.
    """
    ws_endpoint = "/ws/telemetry"
    for _ in range(5):
        with client.websocket_connect(ws_endpoint) as ws:
            pass
