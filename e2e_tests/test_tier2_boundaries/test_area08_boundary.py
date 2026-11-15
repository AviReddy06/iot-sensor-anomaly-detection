"""
e2e_tests/test_tier2_boundaries/test_area08_boundary.py
Area 8 Boundary & Attack Resistance Tests (Feature 12)
Tier 2 Tests: Rate limiting lockout (429 on 6th attempt), counter reset on success, tampered/expired tokens, unset password 503.
"""

import time
import pytest
from starlette.testclient import TestClient
import backend.config as config
import backend.auth as auth


def test_a8_t2_01_rate_limiting_6th_failed_login_returns_429(client: TestClient):
    """
    TEST-A8-T2-01: 5 failed logins return 401; 6th attempt within 60s returns 429 Too Many Requests.
    """
    auth._LOGIN_ATTEMPTS.clear()
    for i in range(5):
        resp = client.post("/api/auth/login", json={"password": f"bad_pwd_{i}"})
        assert resp.status_code == 401, f"Attempt {i+1} returned {resp.status_code} instead of 401"

    # 6th attempt must be blocked by rate limiter
    resp6 = client.post("/api/auth/login", json={"password": "bad_pwd_6"})
    assert resp6.status_code == 429, f"6th attempt expected 429, got {resp6.status_code}"
    assert "Too many failed login attempts" in resp6.json().get("detail", "")


def test_a8_t2_02_rate_limit_cleared_on_successful_login(client: TestClient, admin_password: str):
    """
    TEST-A8-T2-02: Rate limit counter is reset immediately upon a successful login.
    """
    auth._LOGIN_ATTEMPTS.clear()
    # 3 failed attempts
    for i in range(3):
        client.post("/api/auth/login", json={"password": f"bad_pwd_{i}"})

    # Successful login clears the counter
    success_resp = client.post("/api/auth/login", json={"password": admin_password})
    assert success_resp.status_code == 200

    # Subsequent failed attempts start count anew (do not immediately hit 429)
    resp = client.post("/api/auth/login", json={"password": "bad_pwd_new"})
    assert resp.status_code == 401


def test_a8_t2_03_tampered_token_signature_rejected(client: TestClient, admin_token: str):
    """
    TEST-A8-T2-03: Modifying single character in token payload or signature returns 401.
    """
    tampered_token = admin_token[:-4] + "ABCD"
    headers = {"Authorization": f"Bearer {tampered_token}"}
    resp = client.get("/api/admin/model/details", headers=headers)
    assert resp.status_code == 401


def test_a8_t2_04_expired_token_rejected(client: TestClient):
    """
    TEST-A8-T2-04: Signed token with past expiry timestamp is rejected with 401.
    """
    import base64, hmac, hashlib
    expired_time = int(time.time()) - 3600  # 1 hour in the past
    secret = auth._get_token_secret()
    payload = f"admin:{expired_time}".encode("utf-8")
    sig = hmac.new(secret, payload, hashlib.sha256).hexdigest()
    token_str = f"{expired_time}:{sig}"
    expired_token = base64.urlsafe_b64encode(token_str.encode("utf-8")).decode("utf-8")

    headers = {"Authorization": f"Bearer {expired_token}"}
    resp = client.get("/api/admin/model/details", headers=headers)
    assert resp.status_code == 401


def test_a8_t2_05_unset_admin_password_returns_503(client: TestClient):
    """
    TEST-A8-T2-05: When ADMIN_PASSWORD is unset, admin endpoints return 503 Service Unavailable.
    """
    orig_pwd = config.ADMIN_PASSWORD
    try:
        config.ADMIN_PASSWORD = None
        resp_login = client.post("/api/auth/login", json={"password": "any"})
        assert resp_login.status_code == 503

        resp_admin = client.get("/api/admin/model/details")
        assert resp_admin.status_code == 503
    finally:
        config.ADMIN_PASSWORD = orig_pwd


def test_a8_t2_06_constant_time_comparison_used():
    """
    TEST-A8-T2-06: Verification that constant-time compare (hmac.compare_digest) is utilized.
    Inspects backend auth services to ensure tokens and passwords cannot be checked via '=='.
    """
    import inspect
    from backend import auth
    from backend.routes import auth_routes

    auth_src = inspect.getsource(auth)
    routes_src = inspect.getsource(auth_routes)

    assert "hmac.compare_digest" in auth_src, "backend/auth.py must use hmac.compare_digest for token verification"
    assert "hmac.compare_digest" in routes_src, "backend/routes/auth_routes.py must use hmac.compare_digest for password checking"
