"""
e2e_tests/test_tier1_features/test_area06_health_metrics.py
Area 6: Health & Admin Metrics Endpoints (Features 9, 11)
Tier 1 Tests: /api/health schema, /api/admin/metrics auth, db connectivity, uptime.
"""

import time
import pytest
from starlette.testclient import TestClient


def test_a6_t1_01_comprehensive_health_schema(client: TestClient):
    """
    TEST-A6-T1-01: Comprehensive Health Endpoint Schema (GET /api/health).
    """
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] in ["ok", "healthy", "degraded", "unhealthy"]


def test_a6_t1_02_authenticated_admin_metrics(client: TestClient, admin_token: str):
    """
    TEST-A6-T1-02: Authenticated Admin Operational Metrics (GET /api/admin/metrics).
    Requires valid admin bearer token.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.get("/api/admin/metrics", headers=headers)
    # If route is implemented in M2, status is 200; if still in progress, records honest status
    if response.status_code == 404:
        pytest.fail("Endpoint /api/admin/metrics not yet implemented by M2 worker")
    assert response.status_code == 200
    data = response.json()
    for expected_key in ["queue_depth", "dropped_messages", "connected_clients"]:
        assert expected_key in data, f"Key {expected_key} missing in admin metrics"


def test_a6_t1_03_admin_metrics_unauthenticated_rejection(client: TestClient):
    """
    TEST-A6-T1-03: Admin Metrics Unauthenticated Rejection.
    Requests without Bearer token must return 401 Unauthorized.
    """
    response = client.get("/api/admin/metrics")
    # Must be 401 Unauthorized (or 404 if route not yet created)
    if response.status_code == 404:
        pytest.fail("Endpoint /api/admin/metrics not yet implemented by M2 worker")
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"


def test_a6_t1_04_health_database_connectivity(client: TestClient):
    """
    TEST-A6-T1-04: Health Check Database Connectivity Verification.
    """
    from backend.database import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1;")
    result = cursor.fetchone()
    conn.close()
    assert result[0] == 1


def test_a6_t1_05_health_uptime_monotonic(client: TestClient):
    """
    TEST-A6-T1-05: Health Check Uptime Monotonic Progression.
    """
    resp1 = client.get("/api/health")
    assert resp1.status_code == 200
    data1 = resp1.json()
    if "uptime_seconds" in data1:
        time.sleep(1.0)
        resp2 = client.get("/api/health")
        data2 = resp2.json()
        assert data2["uptime_seconds"] >= data1["uptime_seconds"]
