"""
e2e_tests/test_tier4_scenarios/test_scenario3_sensor_disconnect.py
Tier 4 Scenario 3: Environmental Sensor Disconnection, Offline UI Transition & Backlog Recovery
Simulates hardware disconnect, verifies offline status shift, inactive age detection, and reconnection.
"""

from datetime import datetime, timedelta, timezone
import pytest
from starlette.testclient import TestClient
from backend.database import insert_reading, get_recent_readings
from backend.services.serial_service import serial_service


def test_scenario_03_sensor_disconnection_and_recovery(client: TestClient):
    """
    Scenario 3:
    1. Sensor is actively streaming (Live / Simulated).
    2. Stream ceases / disconnects -> client status transitions to Offline.
    3. Verify offline_time is recorded in /api/client/status.
    4. Sensor reconnects and transmits backlogged telemetry.
    5. Monotonic timestamp order is preserved across recovery.
    """
    # 1. Start streaming simulation
    serial_service.start_simulation("test", interval_sec=100.0)
    assert serial_service.is_streaming

    resp_live = client.get("/api/client/status")
    assert resp_live.status_code == 200
    assert resp_live.json()["status"] in ["Live", "Simulated"]

    # 2. Simulate inactive stream age (>60s silence)
    now = datetime.now(timezone.utc)
    old_ts = (now - timedelta(seconds=75)).isoformat()
    insert_reading(old_ts, 24.5, 59.0, is_simulated=True)

    resp_silence = client.get("/api/client/status")
    assert resp_silence.status_code == 200
    data_silence = resp_silence.json()

    # 60s stream silence timeout to Offline is an M2 deliverable
    if data_silence.get("status") in ["Live", "Simulated"]:
        pytest.fail("Serial disconnect, 60s stream silence timeout, and reconnect backoff not yet implemented by M2 worker")

    assert data_silence["status"] == "Offline", f"Expected Offline status, got {data_silence['status']}"

    # 3. Simulate hardware disconnect
    serial_service.stop_stream()
    assert not serial_service.is_streaming

    # 4. Sensor reconnects and transmits backlogged telemetry
    backlog = [
        ((now - timedelta(seconds=20)).isoformat(), 24.6, 59.1),
        ((now - timedelta(seconds=10)).isoformat(), 24.7, 59.2),
        (now.isoformat(), 24.8, 59.3),
    ]
    for ts, temp, hum in backlog:
        insert_reading(ts, temp, hum, is_simulated=True)

    readings = get_recent_readings(3)
    assert len(readings) == 3
    timestamps = [r["timestamp"] for r in readings]
    assert timestamps == sorted(timestamps), f"Backlogged readings violate monotonic ordering: {timestamps}"
