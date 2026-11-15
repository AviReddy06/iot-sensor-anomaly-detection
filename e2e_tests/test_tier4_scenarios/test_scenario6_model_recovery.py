"""
e2e_tests/test_tier4_scenarios/test_scenario6_model_recovery.py
Tier 4 Scenario 6: Corrupted Model Artifact Startup Recovery to Degraded Operational Mode
Validates fault handling when ML model artifact is corrupted on disk, returning degraded health without crash.
"""

from pathlib import Path
import tempfile
import pytest
from starlette.testclient import TestClient


def test_scenario_06_corrupted_model_degraded_recovery(client: TestClient):
    """
    Scenario 6:
    1. Points to an ephemeral corrupted model artifact.
    2. Backend handles fault gracefully without uncaught 500 crash on /api/health.
    3. Health status reflects degraded operational capability.
    4. Client telemetry endpoints remain operational.
    """
    from backend.services.detector_service import detector_service

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_models = Path(tmp_dir)
        # Create corrupted artifact
        (tmp_models / "iforest.joblib").write_bytes(b"CORRUPTED_MODEL_BYTECODE_GARBAGE")
        (tmp_models / "scaler.joblib").write_bytes(b"CORRUPTED_SCALER_BYTECODE_GARBAGE")
        (tmp_models / "thresholds.json").write_text("{}", encoding="utf-8")

        orig_dir = detector_service.models_dir
        try:
            detector_service.models_dir = tmp_models

            # 1. Query health endpoint
            resp = client.get("/api/health")
            assert resp.status_code == 200, f"Health endpoint crashed with status {resp.status_code}"
            data = resp.json()

            # 2. Assert degraded status
            if data.get("status") == "ok":
                pytest.fail("Corrupted model degraded recovery not yet implemented by M2 worker")

            assert data.get("status") == "degraded", f"Expected degraded status on corrupted model, got: {data}"
            assert "model" in str(data).lower(), f"Expected model diagnostic failure details in: {data}"

            # 3. Client endpoints continue responding
            status_resp = client.get("/api/client/status")
            assert status_resp.status_code == 200
            readings_resp = client.get("/api/client/readings?limit=5")
            assert readings_resp.status_code == 200
        finally:
            detector_service.models_dir = orig_dir
