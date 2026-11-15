"""
tests/test_regression.py
Regression tests for Step B.4 verification:
1. Two replays of test_data_with_labels.csv create exactly one event per pass
2. Missing/corrupt model -> /api/health says "degraded", client says "Detector unavailable", never "Normal"
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Generator
import pytest
from starlette.testclient import TestClient

import backend.config as bcfg
import backend.database as database
from backend.app import app
from backend.auth import generate_signed_token
from backend.database import (
    get_audit_logs,
    get_recent_events,
    get_recent_readings,
    get_setting,
    insert_event,
    insert_reading,
)
from backend.services.detector_service import detector_service
from backend.services.events_service import events_service
from backend.services.inference_service import inference_service
from backend.services.serial_service import serial_service


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    with TestClient(app, base_url="http://localhost:8000") as test_client:
        yield test_client


@pytest.fixture
def isolated_db(monkeypatch, tmp_path) -> Generator[Path, None, None]:
    """Provides a fresh isolated SQLite DB in tmp_path for each test."""
    db_file = tmp_path / "regression_test.db"
    monkeypatch.setenv("DB_PATH", str(db_file))
    monkeypatch.setattr(bcfg, "DB_PATH", db_file)
    monkeypatch.setattr(database, "DB_PATH", db_file)
    database._initialized_paths.discard(str(db_file.resolve()))

    # Ensure clean tables exist
    conn = database.get_db_connection()
    conn.close()

    # Reset in-memory services
    serial_service.stop_stream()
    serial_service.data_buffer.clear()
    serial_service.scored_history.clear()
    events_service.reset()

    yield db_file

    serial_service.stop_stream()
    serial_service.data_buffer.clear()
    serial_service.scored_history.clear()
    events_service.reset()


@pytest.fixture
def admin_headers(monkeypatch) -> dict:
    monkeypatch.setattr(bcfg, "ADMIN_PASSWORD", "regression_test_secret")
    token = generate_signed_token()
    return {"Authorization": f"Bearer {token}"}


class TestReplayCreatesExactlyOneEvent:
    """Test that two replays of test_data_with_labels.csv create exactly one event total
    (deduplication prevents duplicate events from identical replays)."""

    def test_replay_pass1_creates_one_event(self, isolated_db):
        """First replay produces exactly 1 aggregated event in DB."""
        res1 = serial_service.start_simulation("test", interval_sec=0.0, loop=False)
        assert res1["status"] == "started"
        assert res1["dataset"] == "test"
        assert res1["loop"] is False

        # Wait for thread termination
        if serial_service.worker_thread:
            serial_service.worker_thread.join(timeout=10.0)
            assert not serial_service.worker_thread.is_alive(), "Worker thread hung on Pass 1"

        assert serial_service.is_streaming is False

        # Verify exactly 1 aggregated event in DB
        events_pass1 = get_recent_events(limit=100)
        assert len(events_pass1) == 1, f"Expected exactly 1 aggregated event on Pass 1, got {len(events_pass1)}"
        assert events_pass1[0]["severity"] == "High"

    def test_two_replays_create_exactly_one_event_total(self, isolated_db):
        """Two replays produce exactly 1 event total (deduplication works)."""
        # First pass
        res1 = serial_service.start_simulation("test", interval_sec=0.0, loop=False)
        assert res1["status"] == "started"
        if serial_service.worker_thread:
            serial_service.worker_thread.join(timeout=10.0)

        # Second pass
        res2 = serial_service.start_simulation("test", interval_sec=0.0, loop=False)
        assert res2["status"] == "started"
        if serial_service.worker_thread:
            serial_service.worker_thread.join(timeout=10.0)

        assert serial_service.is_streaming is False

        # Verify exactly 1 aggregated event total (deduplication prevents duplicate)
        events = get_recent_events(limit=100)
        assert len(events) == 1, f"Expected exactly 1 event total after two replays, got {len(events)}"
        assert events[0]["severity"] == "High"


class TestMissingCorruptModelDegraded:
    """Test that missing or corrupt model artifacts result in degraded health
    and client page says 'Detector unavailable', never 'Normal'."""

    def test_missing_model_health_degraded(self, monkeypatch, client: TestClient):
        """Missing model artifacts -> /api/health status is 'degraded'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_dir = Path(tmpdir)
            # Create a fresh DetectorService with empty models dir
            from backend.services.detector_service import DetectorService
            from backend.services.inference_service import InferenceService

            degraded_detector = DetectorService(models_dir=empty_dir)
            degraded_inference = InferenceService(model_dir=empty_dir)

            # Monkeypatch the global services
            monkeypatch.setattr("backend.routes.client_routes.detector_service", degraded_detector)
            monkeypatch.setattr("backend.routes.client_routes.inference_service", degraded_inference)

            resp = client.get("/api/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "degraded", f"Expected degraded, got {data['status']}"
            assert data["details"] is not None
            assert "Missing model artifacts" in data["details"]

    def test_corrupt_model_health_degraded(self, monkeypatch, client: TestClient):
        """Corrupt model artifacts -> /api/health status is 'degraded'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dir_path = Path(tmpdir)
            # Create invalid zero-byte / corrupt files
            (dir_path / "scaler.joblib").write_bytes(b"NOT_A_VALID_JOBLIB_PICKLE")
            (dir_path / "iforest.joblib").write_bytes(b"CORRUPTED_BYTES")
            (dir_path / "thresholds.json").write_text("{}", encoding="utf-8")

            from backend.services.detector_service import DetectorService
            from backend.services.inference_service import InferenceService

            degraded_detector = DetectorService(models_dir=dir_path)
            degraded_inference = InferenceService(model_dir=dir_path)

            monkeypatch.setattr("backend.routes.client_routes.detector_service", degraded_detector)
            monkeypatch.setattr("backend.routes.client_routes.inference_service", degraded_inference)

            resp = client.get("/api/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "degraded", f"Expected degraded, got {data['status']}"
            assert data["details"] is not None
            assert "Corrupt model artifact" in data["details"]

    def test_client_status_never_says_normal_when_degraded(self, monkeypatch, client: TestClient):
        """When model is missing/corrupt, client status headline must be 'Detector unavailable',
        never 'The room is normal.'"""
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_dir = Path(tmpdir)
            from backend.services.detector_service import DetectorService
            from backend.services.inference_service import InferenceService

            degraded_detector = DetectorService(models_dir=empty_dir)
            degraded_inference = InferenceService(model_dir=empty_dir)

            monkeypatch.setattr("backend.routes.client_routes.detector_service", degraded_detector)
            monkeypatch.setattr("backend.routes.client_routes.inference_service", degraded_inference)

            resp = client.get("/api/client/status")
            assert resp.status_code == 200
            data = resp.json()
            # The headline should indicate detector is unavailable
            assert data["headline"] == "Detector unavailable", f"Expected 'Detector unavailable', got '{data['headline']}'"
            assert "normal" not in data["headline"].lower(), f"Headline must not contain 'normal': {data['headline']}"

    def test_inference_service_returns_degraded_status(self):
        """InferenceService returns 'Detector unavailable' status when degraded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_dir = Path(tmpdir)
            from backend.services.inference_service import InferenceService

            degraded_inference = InferenceService(model_dir=empty_dir)

            # Process a buffer to get a frame
            frame = degraded_inference.process_streaming_buffer([
                {"timestamp": "2026-11-15T12:00:00Z", "temperature": 25.0, "humidity": 60.0},
                {"timestamp": "2026-11-15T12:00:02Z", "temperature": 25.1, "humidity": 60.1},
            ])
            assert frame is not None
            assert frame["status"] == "Detector unavailable"
            assert frame["is_anomaly"] is False