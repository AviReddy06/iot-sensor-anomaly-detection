"""
e2e_tests/test_tier4_scenarios/test_scenario2_operator_workflow.py
Tier 4 Scenario 2: End-to-End Operator Workflow
Login, Sensitivity Tuning, Replay, and Sanitized Audit & Alerts CSV Export.
"""

import pytest
from starlette.testclient import TestClient
from backend.database import insert_event, get_audit_logs


def test_scenario_02_operator_workflow(client: TestClient, admin_password: str):
    """
    Scenario 2:
    1. Operator attempts login with wrong password -> 401.
    2. Operator logs in with valid password -> receives JWT bearer token.
    3. Operator inspects /api/admin/model/details.
    4. Operator updates sensitivity to "High" -> receives updated threshold.
    5. Operator reviews audit log -> finds SENSITIVITY_CHANGED.
    6. Operator downloads alerts export -> verifies CSV format & CWE-1236 formula escaping.
    """
    # Step 1: Wrong password fails
    resp_bad = client.post("/api/auth/login", json={"password": "WrongPassword"})
    assert resp_bad.status_code == 401

    # Step 2: Valid login
    resp_login = client.post("/api/auth/login", json={"password": admin_password})
    assert resp_login.status_code == 200
    token = resp_login.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Step 3: Model details inspection
    resp_details = client.get("/api/admin/model/details", headers=headers)
    assert resp_details.status_code == 200

    # Step 4: Sensitivity tuning
    resp_sens = client.post("/api/admin/settings/sensitivity", json={"level": "High"}, headers=headers)
    assert resp_sens.status_code == 200
    assert resp_sens.json().get("sensitivity") == "High"

    # Step 5: Audit log inspection
    audits = get_audit_logs(10)
    assert any("SENSITIVITY" in a.get("action", "") for a in audits)

    # Step 6: Alerts export
    insert_event(
        start_time="2026-11-15T12:00:00Z",
        end_time="2026-11-15T12:00:20Z",
        duration_sec=20.0,
        peak_temp=33.5,
        peak_hum=75.0,
        delta_temp=8.0,
        what_changed="=1+1 Formula Injection Attempt",
        severity="High",
        sentence="@SUM(B1:B10) Unusual reading",
    )
    resp_export = client.get("/api/admin/alerts/export", headers=headers)
    assert resp_export.status_code == 200
    assert "text/csv" in resp_export.headers.get("content-type", "")
    content = resp_export.text
    for line in content.splitlines():
        if "=1+1" in line:
            assert "'=1+1" in line
        if "@SUM" in line:
            assert "'@SUM" in line
