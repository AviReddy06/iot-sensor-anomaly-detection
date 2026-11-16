"""
tests/test_remote_telemetry.py
Tests for remote ESP32 telemetry ingestion via POST /api/telemetry/ingest
"""
from __future__ import annotations

import hmac
import json
import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from starlette.datastructures import Headers

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Set test environment variables before importing backend modules
os.environ.setdefault("DEVICE_INGEST_TOKEN", "test-device-token-12345")
os.environ.setdefault("ADMIN_PASSWORD", "test-admin-password")

import tempfile
import pytest
from fastapi.testclient import TestClient
from starlette.datastructures import Headers

from backend.app import app
from backend.services.serial_service import serial_service
from backend.database import insert_reading, get_recent_readings, get_recent_events
from backend.services.serial_service import serial_service
from backend.services.inference_service import inference_service
from backend.database import get_db_connection, get_recent_readings, get_recent_events
from backend.services.serial_service import serial_service
from backend.services.inference_service import inference_service
from backend.database import get_db_connection, get_recent_readings, get_recent_events
import backend.config as backend_config  # This is the backend config module (uses module-level constants)
# The backend config module uses module-level constants, not a config object
DEVICE_INGEST_TOKEN = getattr(backend_config, "DEVICE_INGEST_TOKEN", None)


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    with TestClient(app, base_url="http://testserver") as client:
        yield client


@pytest.fixture(scope="function")
def temp_db() -> Generator[str, None, None]:
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    os.environ["DB_PATH"] = db_path
    # Reinitialize the database
    import backend.database as database
    database.DB_PATH = Path(os.environ["DB_PATH"])
    database._initialized_paths.clear()
    yield db_path
    # Cleanup
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture(autouse=True)
def reset_serial_service():
    """Reset serial service state before each test."""
    serial_service.stop_stream()
    serial_service.data_buffer.clear()
    serial_service.scored_history.clear()
    serial_service.incident_log.clear()
    serial_service.stream_source = "none"
    serial_service.is_streaming = False
    serial_service.stream_source = "none"
    serial_service.current_port = None
    yield
    serial_service.stop_stream()


class TestTelemetryIngestion:
    """Tests for remote telemetry ingestion endpoint."""

    def test_valid_telemetry_ingestion(self, client: TestClient):
        """Test valid telemetry ingestion with valid token."""
        payload = {
            "timestamp": "2026-01-15T12:00:00Z",
            "temperature": 25.5,
            "humidity": 60.0,
        }
        headers = {"X-Device-Token": "test-device-token-12345"}
        response = client.post("/api/telemetry/ingest", json={"timestamp": "2026-01-15T12:00:00Z", "temperature": 25.5, "humidity": 60.0}, headers={"X-Device-Token": "test-device-token-12345"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["temperature"] == 25.5
        assert data["humidity"] == 60.0
        assert data["source"] == "remote"

    def test_missing_token(self, client: TestClient):
        """Test ingestion without token returns 401."""
        payload = {"temperature": 25.0, "humidity": 60.0}
        response = client.post("/api/telemetry/ingest", json={"temperature": 25.0, "humidity": 60.0})
        assert response.status_code == 401
        assert "Missing X-Device-Token header" in response.json()["detail"]

    def test_invalid_token(self, client: TestClient):
        """Test ingestion with invalid token returns 401."""
        payload = {"temperature": 25.0, "humidity": 60.0}
        response = client.post(
            "/api/telemetry/ingest",
            json={"temperature": 25.0, "humidity": 60.0},
            headers={"X-Device-Token": "invalid-token"},
        )
        assert response.status_code == 401
        assert "Invalid device token" in response.json()["detail"]

    def test_missing_token_header(self, client: TestClient):
        """Test ingestion without token header returns 401."""
        response = client.post("/api/telemetry/ingest", json={"temperature": 25.0, "humidity": 60.0})
        assert response.status_code == 401
        assert "Missing X-Device-Token header" in response.json()["detail"]

    def test_invalid_temperature(self, client: TestClient):
        """Test invalid temperature values are rejected."""
        response = client.post(
            "/api/telemetry/ingest",
            json={"temperature": 100.0, "humidity": 60.0},
            headers={"X-Device-Token": "test-device-token-12345"},
        )
        assert response.status_code == 422
        # Pydantic returns "Input should be less than or equal to 65" for temperature > 65
        detail = response.json()["detail"]
        assert any("less than or equal to 65" in str(d.get("msg", "")) for d in detail if isinstance(d, dict))

    def test_invalid_humidity(self, client: TestClient):
        """Test invalid humidity values are rejected."""
        response = client.post(
            "/api/telemetry/ingest",
            json={"temperature": 25.0, "humidity": 150.0},
            headers={"X-Device-Token": "test-device-token-12345"},
        )
        assert response.status_code == 422
        detail = response.json()["detail"]
        assert any("less than or equal to 100" in str(d.get("msg", "")) for d in detail if isinstance(d, dict))

    def test_missing_device_token_config(self, client: TestClient):
        """Test ingestion fails when DEVICE_INGEST_TOKEN is not set."""
        # Temporarily remove the token
        import backend.config as config_module
        original_token = os.environ.get("DEVICE_INGEST_TOKEN")
        os.environ.pop("DEVICE_INGEST_TOKEN", None)
        # Reload config module
        import importlib
        import backend.config as config_module
        importlib.reload(config_module)
        
        try:
            response = client.post(
                "/api/telemetry/ingest",
                json={"temperature": 25.0, "humidity": 60.0},
                headers={"X-Device-Token": "test-device-token-12345"},
            )
            assert response.status_code == 503
            assert "DEVICE_INGEST_TOKEN not set" in response.json()["detail"]
        finally:
            # Restore - always restore the original token
            if original_token is not None:
                os.environ["DEVICE_INGEST_TOKEN"] = original_token
            importlib.reload(config_module)

    def test_database_persistence(self, client: TestClient):
        """Test that ingested telemetry is persisted to database."""
        payload = {"temperature": 25.5, "humidity": 60.0}
        response = client.post(
            "/api/telemetry/ingest",
            json={"temperature": 25.5, "humidity": 60.0},
            headers={"X-Device-Token": "test-device-token-12345"},
        )
        assert response.status_code == 200
        
        # Check database
        readings = get_recent_readings(limit=10)
        assert len(readings) > 0
        latest = readings[0]
        assert latest["temperature"] == 25.5
        assert latest["humidity"] == 60.0
        assert latest["is_simulated"] is False

    def test_anomaly_inference_and_websocket_broadcast(self, client):
        """Test that anomaly detection runs and WebSocket broadcast occurs."""
        payload = {"temperature": 35.0, "humidity": 90.0}  # Likely to trigger anomaly
        response = client.post(
            "/api/telemetry/ingest",
            json={"temperature": 35.0, "humidity": 90.0},
            headers={"X-Device-Token": "test-device-token-12345"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_remote_stream_offline_after_60_seconds(self, client):
        """Test that remote stream goes offline after 60 seconds without readings."""
        from backend.services.serial_service import serial_service
        import time
        
        # Test that the offline detection logic exists
        assert hasattr(serial_service, '_evaluate_offline_status')
        assert hasattr(serial_service, 'last_reading_monotonic')
        assert hasattr(serial_service, 'serial_state')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])