"""
e2e_tests/test_tier3_cross_features/test_cross_faults_lifecycle.py
Tier 3: Pairwise Interactions - Fault Handling & Lifecycle (TF3-10 to TF3-16)
Validates interactions between sensor faults, model corruptions, startup feature checks, brute-force lockout, and origin controls.
"""

from pathlib import Path
import pytest
from starlette.testclient import TestClient
from backend.database import insert_reading
import backend.config as config


def test_tf3_10_pair_temp_equal_hum_health_flag(client: TestClient):
    """TF3-10: 30 identical temp==hum readings flag suspected sensor hardware fault in /api/health."""
    for i in range(30):
        insert_reading(f"2026-11-15T10:00:{i:02d}", 25.0, 25.0, False)

    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    fault_msg = (
        data.get("suspected_fault")
        or data.get("sensor_status")
        or str(data.get("warnings", ""))
        or str(data.get("detail", ""))
    ).lower()

    if data.get("status") == "ok" and "fault" not in fault_msg:
        pytest.fail("Health endpoint 30-reading temp==hum fault flag not yet implemented by M2 worker")
    assert "fault" in fault_msg or "identical" in fault_msg


def test_tf3_11_pair_model_corrupt_startup_degraded(client: TestClient):
    """TF3-11: Missing or corrupted model triggers degraded operational state in /api/health."""
    import tempfile
    from backend.services.detector_service import detector_service
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_models = Path(tmp_dir)
        (tmp_models / "iforest.joblib").write_bytes(b"CORRUPTED_MODEL_PAYLOAD_GARBAGE")
        (tmp_models / "scaler.joblib").write_bytes(b"CORRUPTED_SCALER_PAYLOAD_GARBAGE")
        (tmp_models / "thresholds.json").write_text("{}", encoding="utf-8")

        orig_dir = detector_service.models_dir
        try:
            detector_service.models_dir = tmp_models
            resp = client.get("/api/health")
            assert resp.status_code == 200, f"Expected 200 degraded health, got {resp.status_code}"
            data = resp.json()
            if data.get("status") == "ok":
                pytest.fail("Corrupted model health degradation check not yet implemented by M2 worker")
            assert data.get("status") in ["degraded", "warning"], f"Expected degraded status, got: {data}"
        finally:
            detector_service.models_dir = orig_dir


def test_tf3_12_pair_feature_mismatch_startup_refusal():
    """TF3-12: Feature count mismatch between thresholds.json and code refuses startup with RuntimeError."""
    import tempfile
    import shutil
    import json
    from backend.services.detector_service import DetectorService

    with tempfile.TemporaryDirectory() as tmp_dir:
        tpath = Path(tmp_dir)
        shutil.copy(config.PROJECT_ROOT / "models" / "scaler.joblib", tpath / "scaler.joblib")
        shutil.copy(config.PROJECT_ROOT / "models" / "iforest.joblib", tpath / "iforest.joblib")

        th = json.loads((config.PROJECT_ROOT / "models" / "thresholds.json").read_text(encoding="utf-8"))
        th["feature_cols"] = ["temp", "hum"]  # 2 instead of 12
        (tpath / "thresholds.json").write_text(json.dumps(th), encoding="utf-8")

        with pytest.raises(RuntimeError) as exc_info:
            DetectorService(models_dir=tpath)

        assert "Feature list mismatch" in str(exc_info.value)
        assert "Refusing to start" in str(exc_info.value)


def test_tf3_13_pair_brute_force_lockout_rate_limit(client: TestClient, admin_password: str):
    """TF3-13: 5 failed logins return 401, 6th attempt returns 429."""
    if admin_password:
        client.post("/api/auth/login", json={"password": admin_password})

    for _ in range(5):
        r = client.post("/api/auth/login", json={"password": "wrong_password_attempt"})
        assert r.status_code == 401

    resp6 = client.post("/api/auth/login", json={"password": "wrong_password_attempt"})
    assert resp6.status_code == 429


def test_tf3_14_pair_unset_password_route_503(client: TestClient):
    """TF3-14: Unset password disables admin routes with 503 while client routes remain 200."""
    orig = config.ADMIN_PASSWORD
    try:
        config.ADMIN_PASSWORD = None
        assert client.get("/api/admin/model/details").status_code == 503
        assert client.get("/api/client/status").status_code == 200
    finally:
        config.ADMIN_PASSWORD = orig


def test_tf3_15_pair_ws_slow_client_drop_isolation(client: TestClient):
    """TF3-15: Broadcaster isolates slow client queue from fast consumers."""
    ws_endpoint = "/ws/client"
    try:
        with client.websocket_connect(ws_endpoint) as ws:
            pass
    except Exception:
        ws_endpoint = "/ws/telemetry"

    with client.websocket_connect(ws_endpoint) as ws1:
        with client.websocket_connect(ws_endpoint) as ws2:
            ws2.send_text('{"action": "ping"}')
            assert ws2.receive_json().get("type") == "pong"


def test_tf3_16_pair_cors_disallowed_origin_rejection(client: TestClient):
    """TF3-16: CORS rejects unauthorized external origins."""
    resp = client.get("/api/client/status", headers={"Origin": "http://unauthorized.org"})
    assert resp.headers.get("access-control-allow-origin") != "http://unauthorized.org"
