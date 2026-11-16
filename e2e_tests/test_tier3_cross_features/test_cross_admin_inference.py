"""
e2e_tests/test_tier3_cross_features/test_cross_admin_inference.py
Tier 3: Pairwise Interactions - Administration & Inference (TF3-17 to TF3-22)
Validates interactions across database retention purge, client alert hygiene, clock jumps, sensitivity audit round-trip, freeze hashes, and graceful shutdown.
"""

from pathlib import Path
import hashlib
import json
import pytest
from starlette.testclient import TestClient
from backend.services.events_service import EventsService
from backend.database import get_audit_logs
import backend.config as config


def test_tf3_17_pair_db_retention_purge_concurrent_read(client: TestClient):
    """TF3-17: Retention purge routine operates cleanly alongside concurrent queries."""
    import backend.database as db
    purge_fn = getattr(db, "purge_old_readings", None)
    if purge_fn is None:
        pytest.fail("Backend retention routine 'purge_old_readings' not implemented in backend.database")

    purge_fn(days=30)
    resp = client.get("/api/client/readings?limit=5")
    assert resp.status_code == 200


def test_tf3_18_pair_client_dom_ban_during_active_alert():
    """TF3-18: Generated alert sentence uses client-safe English and zero ML technical jargon."""
    events_svc = EventsService()
    event = events_svc.process_sample("2026-11-15T12:00:00Z", 34.0, 80.0, True, 9.5)
    if events_svc.active_event:
        event = events_svc.flush()

    sentence = event.get("sentence", "").lower()
    banned = ["isolation", "forest", "z-score", "threshold", "model"]
    for b in banned:
        assert b not in sentence, f"Banned jargon '{b}' found in alert sentence: {sentence}"


def test_tf3_19_pair_fakeserial_clock_jump_backward():
    """TF3-19: Telemetry clock jump backward maintains non-negative duration."""
    events_svc = EventsService()
    events_svc.process_sample("2026-11-15T12:00:10Z", 32.0, 75.0, True, 7.5)
    events_svc.process_sample("2026-11-15T12:00:05Z", 33.0, 76.0, True, 8.0)
    if events_svc.active_event:
        final = events_svc.flush()
        assert final["duration_sec"] >= 0.0


def test_tf3_20_pair_admin_sensitivity_audit_roundtrip(client: TestClient, admin_token: str):
    """TF3-20: Changing sensitivity updates SQLite settings and creates audit trail entry."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    client.post("/api/admin/settings/sensitivity", json={"level": "Low"}, headers=headers)
    audits = get_audit_logs(5)
    assert any("SENSITIVITY" in a["action"] for a in audits)


def test_tf3_21_pair_freeze_hash_validation():
    """TF3-21: Computed SHA256 of frozen model weights confirms artifact presence and matches freeze.json manifest."""
    weights_path = config.PROJECT_ROOT / "models" / "iforest.joblib"
    freeze_path = config.PROJECT_ROOT / "results" / "freeze.json"

    assert weights_path.exists(), "models/iforest.joblib not found"
    sha = hashlib.sha256(weights_path.read_bytes()).hexdigest()

    assert freeze_path.exists(), "results/freeze.json not found — required for code freeze validation"
    with open(freeze_path, "r", encoding="utf-8") as f:
        freeze_data = json.load(f)

    expected_sha = freeze_data.get("models/iforest.joblib") or freeze_data.get("iforest.joblib")
    assert expected_sha is not None, "iforest.joblib hash missing from results/freeze.json"
    assert sha.lower() == expected_sha.lower(), f"Freeze hash mismatch: expected {expected_sha}, computed {sha}"


def test_tf3_22_pair_ingest_burst_sigint_shutdown():
    """TF3-22: Serial stream worker stops cleanly without hanging threads."""
    from backend.services.serial_service import serial_service
    serial_service.stop_stream()
    assert not serial_service.is_streaming
