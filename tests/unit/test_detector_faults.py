"""
tests/unit/test_detector_faults.py
Unit tests verifying detector fault resilience and startup refusal:
- Missing model artifacts -> degraded status with reason, no crash
- Corrupt model artifacts -> degraded status, safe fallback evaluation
- Feature list mismatch in thresholds.json -> RuntimeError startup refusal
"""

from __future__ import annotations
import json
from pathlib import Path
import tempfile
import pandas as pd
import pytest

from backend.services.detector_service import DetectorService
from backend.services.inference_service import InferenceService
from features.feature_engine import MODEL_FEATURE_COLS


def test_missing_model_artifacts_degraded():
    """Verify missing model artifacts set degraded health without crashing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Empty directory has no joblib or json files
        empty_dir = Path(tmpdir)
        detector = DetectorService(models_dir=empty_dir)
        assert detector.is_degraded is True
        assert detector.model_status == "degraded"
        assert detector.degraded_reason is not None
        assert "Missing model artifacts" in detector.degraded_reason

        # Safe fallback evaluation
        res = detector.evaluate_streaming_sample(pd.DataFrame([{"temperature": 25.0, "humidity": 60.0}]))
        assert res["degraded"] is True
        assert res["flag"] is False


def test_corrupt_model_artifacts_degraded():
    """Verify corrupt model artifacts (e.g. invalid bytes) set degraded status without crashing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dir_path = Path(tmpdir)
        # Create invalid zero-byte / corrupt files
        (dir_path / "scaler.joblib").write_bytes(b"NOT_A_VALID_JOBLIB_PICKLE")
        (dir_path / "iforest.joblib").write_bytes(b"CORRUPTED_BYTES")
        (dir_path / "thresholds.json").write_text("{}", encoding="utf-8")

        detector = DetectorService(models_dir=dir_path)
        assert detector.is_degraded is True
        assert detector.model_status == "degraded"
        assert "Corrupt model artifact" in detector.degraded_reason


def test_feature_list_mismatch_refuses_startup():
    """Verify that a mismatch between thresholds.json and MODEL_FEATURE_COLS raises RuntimeError refusing startup."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dir_path = Path(tmpdir)
        from backend.config import PROJECT_ROOT
        real_models = PROJECT_ROOT / "models"

        # Copy real scaler and iforest
        (dir_path / "scaler.joblib").write_bytes((real_models / "scaler.joblib").read_bytes())
        (dir_path / "iforest.joblib").write_bytes((real_models / "iforest.joblib").read_bytes())

        # Create thresholds with deliberately mismatched feature columns
        bad_thresholds = {
            "feature_cols": ["temperature", "humidity", "INVALID_EXTRA_FEATURE"],
            "iforest_threshold": -0.17,
        }
        (dir_path / "thresholds.json").write_text(json.dumps(bad_thresholds), encoding="utf-8")

        with pytest.raises(RuntimeError) as exc_info:
            DetectorService(models_dir=dir_path)

        assert "Feature list mismatch!" in str(exc_info.value)
        assert "Refusing to start." in str(exc_info.value)


def test_inference_service_degraded_handling():
    """Verify InferenceService graceful degradation when model directory is invalid."""
    with tempfile.TemporaryDirectory() as tmpdir:
        infer = InferenceService(model_dir=Path(tmpdir))
        assert infer.is_degraded is True
        assert infer.model_status == "degraded"

        # Safe streaming evaluation
        frame = infer.process_streaming_buffer([
            {"timestamp": "2026-11-15T12:00:00Z", "temperature": 25.0, "humidity": 60.0},
            {"timestamp": "2026-11-15T12:00:02Z", "temperature": 25.1, "humidity": 60.1},
        ])
        assert frame is not None
        assert frame["is_anomaly"] is False
        assert frame["status"] == "Detector unavailable"
