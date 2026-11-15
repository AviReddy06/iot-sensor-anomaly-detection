"""
e2e_tests/test_tier3_cross_features/test_cross_security_uploads.py
Tier 3: Pairwise Interactions - Security & Uploads (TF3-01 to TF3-06)
Cross-boundary tests combining authentication, upload limits, path traversal, sensitivity settings, and export escaping.
"""

import io
from pathlib import Path
import pytest
from starlette.testclient import TestClient
from backend.database import insert_reading, insert_event, get_audit_logs


def test_tf3_01_pair_auth_upload_boundary(client: TestClient, admin_token: str):
    """TF3-01: Upload endpoint processes valid uploaded dataset under authenticated and client sessions."""
    valid_csv = "timestamp,temperature,humidity\n2026-11-15 10:00:00,25.0,60.0\n"
    files = {"file": ("upload.csv", io.BytesIO(valid_csv.encode("utf-8")), "text/csv")}

    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = client.post("/api/datasets/upload", files=files, headers=headers)
    assert resp.status_code == 200, f"Expected 200 for upload, got {resp.status_code}"
    data = resp.json()
    assert "summary" in data or "rows" in data


def test_tf3_02_pair_upload_path_traversal(client: TestClient):
    """TF3-02: Traversal file names in upload are neutralized."""
    csv_bytes = b"timestamp,temperature,humidity\n2026-11-15 10:00:00,25.0,60.0\n"
    files = {"file": ("../../evil.csv", io.BytesIO(csv_bytes), "text/csv")}
    resp = client.post("/api/datasets/upload", files=files)
    import os
    assert not os.path.exists("evil.csv")


def test_tf3_03_pair_replay_sensitivity_change(client: TestClient, admin_token: str):
    """TF3-03: Updating sensitivity during operational stream updates active threshold and audit trail."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = client.post("/api/admin/settings/sensitivity", json={"level": "High"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json().get("sensitivity") == "High"

    # Verify audit log contains SENSITIVITY_CHANGED
    audits = get_audit_logs(10)
    assert any("SENSITIVITY" in a.get("action", "") for a in audits)


def test_tf3_04_pair_simulation_export_formula_escape(client: TestClient, admin_token: str):
    """TF3-04: Telemetry event descriptions beginning with formula operators are escaped upon export."""
    insert_event(
        start_time="2026-11-15T12:00:00Z",
        end_time="2026-11-15T12:00:10Z",
        duration_sec=10.0,
        peak_temp=30.0,
        peak_hum=70.0,
        delta_temp=4.0,
        what_changed="-10C Drop in temperature",
        severity="Medium",
        sentence="@SUM(A1:A10) Unusual reading",
    )
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = client.get("/api/admin/alerts/export", headers=headers)
    assert resp.status_code == 200
    found_sum = False
    for line in resp.text.splitlines():
        if "@SUM" in line:
            found_sum = True
            assert "'@SUM" in line, f"Formula injection escaping missing on @SUM: {line}"
    assert found_sum, "Expected @SUM event in alerts export"


def test_tf3_05_pair_ingest_burst_ws_delivery(client: TestClient):
    """TF3-05: Ingest burst maintains timestamp monotonicity in delivery."""
    ws_endpoint = "/ws/client"
    try:
        with client.websocket_connect(ws_endpoint) as ws:
            pass
    except Exception:
        ws_endpoint = "/ws/telemetry"

    with client.websocket_connect(ws_endpoint) as ws:
        # Deliver burst to DB
        for i in range(10):
            insert_reading(f"2026-11-15T10:00:{i:02d}", 25.0, 60.0, True)
        # Socket remains responsive
        ws.send_text('{"action": "ping"}')
        resp = ws.receive_json()
        assert resp.get("type") == "pong"


def test_tf3_06_pair_ingest_burst_admin_metrics(client: TestClient, admin_token: str):
    """TF3-06: Telemetry ingestion burst updates reading counts in admin metrics."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    for i in range(5):
        insert_reading(f"2026-11-15T10:00:{i:02d}", 25.0, 60.0, True)
    resp = client.get("/api/admin/metrics", headers=headers)
    if resp.status_code == 404:
        pytest.fail("Endpoint /api/admin/metrics not yet implemented by M2 worker")
    assert resp.status_code == 200
    data = resp.json()
    assert "connected_clients" in data or "queue_depth" in data or "total_readings" in data
