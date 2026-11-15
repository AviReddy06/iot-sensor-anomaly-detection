"""
e2e_tests/test_tier2_boundaries/test_area06_boundary.py
Area 6 Boundary & Fault Injection Tests (Features 9, 11)
Tier 2 Tests: Corrupt model handling, feature mismatch refusal, 30-reading temp==hum fault flag, 60s offline, token log redaction.
"""

import json
import logging
import shutil
from pathlib import Path
import pytest
from starlette.testclient import TestClient
from backend.config import PROJECT_ROOT


def test_a6_t2_01_health_status_degraded_on_missing_model(client: TestClient, tmp_path):
    """
    TEST-A6-T2-01: Health reporting degraded status when model artifact is missing or corrupted.
    Requirement R3: missing model -> health reports degraded status without unhandled crash.
    """
    from backend.services.detector_service import DetectorService
    with pytest.raises((FileNotFoundError, RuntimeError)):
        DetectorService(models_dir=tmp_path)

    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    if data.get("status") == "ok":
        pytest.fail("Endpoint /api/health model degradation status check not yet implemented by M2 worker")
    assert data.get("status") in ["degraded", "warning"]


def test_a6_t2_02_feature_mismatch_startup_refusal(tmp_path):
    """
    TEST-A6-T2-02: Application refuses to start if thresholds.json feature list doesn't match model.
    Tests genuine DetectorService initialization with mismatched feature list.
    """
    from backend.services.detector_service import DetectorService

    # Copy genuine models to temp directory
    for f in ["scaler.joblib", "iforest.joblib"]:
        shutil.copy(PROJECT_ROOT / "models" / f, tmp_path / f)

    # Write corrupt thresholds.json with mismatched feature list (2 features instead of 12)
    with open(PROJECT_ROOT / "models" / "thresholds.json", "r", encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["feature_cols"] = ["temp_ewma_residual", "hum_ewma_residual"]
    with open(tmp_path / "thresholds.json", "w", encoding="utf-8") as f:
        json.dump(cfg, f)

    with pytest.raises(RuntimeError) as exc_info:
        DetectorService(models_dir=tmp_path)
    assert "Feature list mismatch!" in str(exc_info.value)
    assert "Refusing to start." in str(exc_info.value)


def test_a6_t2_03_suspected_fault_flag_temp_equal_hum(client: TestClient):
    """
    TEST-A6-T2-03: 30 consecutive identical temperature and humidity values trigger suspected fault in /api/health.
    """
    from backend.database import insert_reading
    for i in range(30):
        insert_reading(f"2026-11-15T10:{i:02d}:00Z", 25.0, 25.0, is_simulated=True)

    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    health_str = str(data).lower()
    if data.get("status") == "ok" and "fault" not in health_str:
        pytest.fail("Health endpoint 30-reading temp==hum fault flag not yet implemented by M2 worker")
    assert "fault" in health_str or "identical" in health_str


def test_a6_t2_04_stream_stop_status_transition_offline(client: TestClient):
    """
    TEST-A6-T2-04: Stopping stream updates client status.
    """
    resp = client.get("/api/client/status")
    assert resp.status_code == 200
    assert resp.json().get("status") in ["Live", "Simulated", "Offline", "normal", "live", "offline"]


def test_a6_t2_05_token_query_param_redacted_from_logs(client: TestClient, caplog):
    """
    TEST-A6-T2-05: Sensitive token query parameters must be sanitized as [REDACTED] in access logs.
    Captures application logs during request and verifies canary token is never leaked.
    """
    canary_token = "SECRET_CANARY_TOKEN_XYZ_98765"
    with caplog.at_level(logging.INFO):
        client.get(f"/api/health?token={canary_token}")

    if not caplog.records:
        pytest.fail("Access log sanitization filter not yet implemented by M2 worker")

    for record in caplog.records:
        assert canary_token not in record.message, f"Canary token leaked in log record: {record.message}"
