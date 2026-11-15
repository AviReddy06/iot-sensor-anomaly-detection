"""
e2e_tests/test_tier1_features/test_area08_auth_hardening.py
Area 8: Auth Hardening, Brute-Force & Secrecy (Feature 12)
Tier 1 Tests: Admin login, protected route access, credential secrecy.
"""

import pytest
from starlette.testclient import TestClient
from backend.database import get_audit_logs


def test_a8_t1_01_admin_login_success(client: TestClient, admin_password: str):
    """
    TEST-A8-T1-01: Admin login with correct password returns bearer token and 28800s expiry.
    """
    response = client.post("/api/auth/login", json={"password": admin_password})
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert data.get("token_type") == "bearer"
    assert data.get("expires_in_seconds") == 28800


def test_a8_t1_02_admin_login_wrong_password_fails(client: TestClient):
    """
    TEST-A8-T1-02: Admin login with wrong password returns 401 Unauthorized.
    """
    response = client.post("/api/auth/login", json={"password": "WrongAdminPassword123!"})
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert "WrongAdminPassword123!" not in response.text


def test_a8_t1_03_protected_admin_route_with_bearer_token(client: TestClient, admin_token: str):
    """
    TEST-A8-T1-03: Protected admin route grants access with valid Bearer token.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.get("/api/admin/model/details", headers=headers)
    assert response.status_code == 200
    assert "version" in response.json()


def test_a8_t1_04_protected_admin_route_missing_token_rejected(client: TestClient):
    """
    TEST-A8-T1-04: Protected admin route rejects request with missing token.
    """
    response = client.get("/api/admin/model/details")
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data


def test_a8_t1_05_password_never_logged_or_returned(client: TestClient):
    """
    TEST-A8-T1-05: Plaintext password is never reflected in response, audit log, or error body.
    """
    secret_canary = "CanarySecret98765!"
    response = client.post("/api/auth/login", json={"password": secret_canary})
    assert secret_canary not in response.text

    audit_logs = get_audit_logs(20)
    for entry in audit_logs:
        assert secret_canary not in entry.get("details", "")
        assert secret_canary not in entry.get("action", "")
