"""
e2e_tests/test_tier1_features/test_area04_network_security.py
Area 4: Network Security, CORS & Static Serving Headers (Features 6, 15)
Tier 1 Tests: Localhost-only CORS enforcement, preflight headers, and static asset security headers.
"""

import pytest
from starlette.testclient import TestClient


def test_a4_t1_01_disallowed_origin_cors_rejection(client: TestClient):
    """
    TEST-A4-T1-01: Requests from disallowed origins must not receive CORS allow headers.
    """
    response = client.get("/api/client/status", headers={"Origin": "http://evil.com"})
    # HTTP status may be 200, but CORS header must NOT allow evil.com or wildcard
    allow_origin = response.headers.get("access-control-allow-origin")
    assert allow_origin != "http://evil.com", "Disallowed origin http://evil.com was granted CORS access"
    assert allow_origin != "*", "Wildcard '*' origin is strictly forbidden"


def test_a4_t1_02_allowed_localhost_cors_acceptance(client: TestClient):
    """
    TEST-A4-T1-02: Requests from allowed localhost origins receive proper CORS headers.
    """
    allowed_origin = "http://localhost:5173"
    response = client.get("/api/client/status", headers={"Origin": allowed_origin})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == allowed_origin
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_a4_t1_03_cors_preflight_options_for_allowed_origin(client: TestClient):
    """
    TEST-A4-T1-03: CORS Preflight OPTIONS Request Validation for Allowed Origin.
    """
    allowed_origin = "http://localhost:5173"
    headers = {
        "Origin": allowed_origin,
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "authorization,content-type",
    }
    response = client.options("/api/client/status", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == allowed_origin
    assert "GET" in response.headers.get("access-control-allow-methods", "")


def test_a4_t1_04_static_serving_csp_header(client: TestClient):
    """
    TEST-A4-T1-04: Static Serving Content-Security-Policy (CSP) Self-Only Header.
    Mandatory R4 security header must be present on static root.
    """
    response = client.get("/")
    csp = response.headers.get("content-security-policy")
    assert csp is not None, "Mandatory Content-Security-Policy header is missing on static root"
    assert "'self'" in csp, "Content-Security-Policy must enforce 'self'"
    assert "cdn.jsdelivr.net" not in csp, "External CDN cdn.jsdelivr.net forbidden in CSP"
    assert "fonts.googleapis.com" not in csp, "External CDN fonts.googleapis.com forbidden in CSP"


def test_a4_t1_05_mime_sniffing_and_referrer_headers(client: TestClient):
    """
    TEST-A4-T1-05: MIME Sniffing & Referrer Policy Headers on Web Responses.
    Mandatory R4 security headers must be present on static root.
    """
    response = client.get("/")
    headers = response.headers
    nosniff = headers.get("x-content-type-options")
    referrer = headers.get("referrer-policy")

    assert nosniff is not None, "Mandatory X-Content-Type-Options header is missing on static root"
    assert nosniff.lower() == "nosniff", f"Expected 'nosniff', got '{nosniff}'"
    assert referrer is not None, "Mandatory Referrer-Policy header is missing on static root"
    assert referrer.lower() in ["no-referrer", "same-origin", "strict-origin-when-cross-origin"], f"Disallowed Referrer-Policy: '{referrer}'"
