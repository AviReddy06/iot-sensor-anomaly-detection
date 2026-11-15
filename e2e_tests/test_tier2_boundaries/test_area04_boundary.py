"""
e2e_tests/test_tier2_boundaries/test_area04_boundary.py
Area 4 Boundary & Corner Cases (Features 6, 15)
Tier 2 Tests: Disallowed origin preflights, spoofed origin variations, SPA 404 isolation, cache-control.
"""

import pytest
from starlette.testclient import TestClient


def test_a4_t2_01_disallowed_origin_preflight_rejection(client: TestClient):
    """
    TEST-A4-T2-01: Preflight OPTIONS request from disallowed origin does not return allow headers.
    """
    headers = {
        "Origin": "https://attacker.example.org",
        "Access-Control-Request-Method": "POST",
    }
    response = client.options("/api/admin/settings/sensitivity", headers=headers)
    allow = response.headers.get("access-control-allow-origin")
    assert allow != "https://attacker.example.org"


def test_a4_t2_02_spoofed_origin_variations_rejected(client: TestClient):
    """
    TEST-A4-T2-02: Spoofed non-localhost origins (e.g. localhost.evil.com) are rejected.
    """
    spoofed = [
        "http://localhost:8000.evil.com",
        "http://evil.localhost.com",
        "https://attacker.com",
        "https://fake-localhost.org",
    ]
    for origin in spoofed:
        resp = client.get("/api/client/status", headers={"Origin": origin})
        allow = resp.headers.get("access-control-allow-origin")
        assert allow != origin, f"Spoofed origin '{origin}' was granted CORS access"


def test_a4_t2_03_spa_fallback_route_guard_no_html_leak(client: TestClient):
    """
    TEST-A4-T2-03: Unmapped /api/* and /ws/* routes return JSON 404, NEVER HTML index fallback.
    """
    for bad_route in ["/api/nonexistent_route_123", "/api/v1/missing", "/ws/invalid_route"]:
        resp = client.get(bad_route)
        assert resp.status_code == 404
        content_type = resp.headers.get("content-type", "")
        assert "application/json" in content_type, f"Route {bad_route} returned non-JSON content-type: {content_type}"
        assert "<!doctype html>" not in resp.text.lower()
        assert "<html" not in resp.text.lower()


def test_a4_t2_04_spa_cache_control_headers(client: TestClient):
    """
    TEST-A4-T2-04: HTML entrypoint enforces no-cache headers.
    """
    resp = client.get("/")
    if resp.headers.get("content-type", "").startswith("text/html"):
        cc = resp.headers.get("cache-control", "")
        assert "no-cache" in cc or "no-store" in cc


def test_a4_t2_05_cross_origin_websocket_restrictions(client: TestClient):
    """
    TEST-A4-T2-05: WebSocket connection attempt from unauthorized cross-site origin must be rejected.
    Requirement R2: CORS allows only localhost origins.
    """
    headers = {"Origin": "http://evil.com"}
    ws_endpoint = "/ws/client"
    try:
        with client.websocket_connect(ws_endpoint, headers=headers) as ws:
            pytest.fail("Connection to /ws/client succeeded with disallowed origin http://evil.com")
    except Exception as e:
        # Verify that failure is not the pytest.fail itself
        if isinstance(e, pytest.fail.Exception):
            raise
        # Connection rejection (HTTP 403, 1008, or connection drop) is the expected secure behavior
        pass
