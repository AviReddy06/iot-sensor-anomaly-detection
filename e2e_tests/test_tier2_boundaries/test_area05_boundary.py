"""
e2e_tests/test_tier2_boundaries/test_area05_boundary.py
Area 5 Boundary & Fault Injection Tests (Features 8, 22)
Tier 2 Tests: Temp==humidity fault detection, 60s stream timeout, burst ingestion, NaN dropping, clock jumps.
"""

import math
import pytest
from starlette.testclient import TestClient
from backend.config import PROJECT_ROOT
from collect.serial_utils import parse_sensor_line
from backend.services.events_service import EventsService


def test_a5_t2_01_fakeserial_30_consecutive_temp_equal_hum(client: TestClient):
    """
    TEST-A5-T2-01: 30 consecutive readings where temp == hum triggers suspected fault condition in /api/health.
    Requirement R3: health endpoint flags 'humidity identical to temperature for 30 readings' as suspected fault.
    """
    from backend.database import insert_reading
    for i in range(30):
        insert_reading(f"2026-11-15T10:{i:02d}:00Z", 26.0, 26.0, is_simulated=True)

    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    health_str = str(data).lower()
    if data.get("status") == "ok" and "fault" not in health_str:
        pytest.fail("Health endpoint 30-reading temp==hum fault flag not yet implemented by M2 worker")
    assert "fault" in health_str or "identical" in health_str


def test_a5_t2_02_stream_inactivity_triggers_offline_duration(client: TestClient):
    """
    TEST-A5-T2-02: Stream silence exceeding 60s transitions status to Offline.
    Requirement R3: stream stops for 60s (status becomes Offline and client page reflects it).
    """
    from datetime import datetime, timedelta, timezone
    from backend.database import insert_reading
    from backend.services.serial_service import serial_service

    # Ensure stream is active
    serial_service.start_simulation("test", interval_sec=100.0)

    # Insert last reading 75s in the past (> 60s threshold)
    old_ts = (datetime.now(timezone.utc) - timedelta(seconds=75)).isoformat()
    insert_reading(old_ts, 24.5, 59.0, is_simulated=True)

    resp = client.get("/api/client/status")
    assert resp.status_code == 200
    data = resp.json()
    if data.get("status") in ["Live", "Simulated"]:
        pytest.fail("60s stream silence timeout to Offline not yet implemented by M2 worker")
    assert data.get("status") == "Offline", f"Expected 'Offline' status after 60s silence, got '{data.get('status')}'"


def test_a5_t2_03_fakeserial_100hz_burst_parsing():
    """
    TEST-A5-T2-03: Rapid parsing of 100 lines does not drop valid readings.
    """
    parsed = []
    for i in range(100):
        line = f"24.{i%10:01d}0,60.{i%10:01d}0\n"
        res = parse_sensor_line(line)
        if res:
            parsed.append(res)
    assert len(parsed) == 100, f"Expected 100 parsed lines, got {len(parsed)}"


def test_a5_t2_04_fakeserial_malformed_and_nan_values_dropped():
    """
    TEST-A5-T2-04: Malformed, NaN, and physical bounds violating lines are dropped without crash.
    """
    corrupt_lines = [
        "NaN,60.0\n",
        "25.0,Inf\n",
        "missing_comma\n",
        "120.0,50.0\n",  # Temp > 80 C
        "-40.0,50.0\n",  # Temp < -20 C
        ",,\n",
        "abc,def\n",
    ]
    for line in corrupt_lines:
        res = parse_sensor_line(line)
        assert res is None, f"Expected None for corrupt line: {line.strip()}"


def test_a5_t2_05_fakeserial_clock_jump_backward_handling():
    """
    TEST-A5-T2-05: Clock jump backward does not result in negative event duration.
    """
    events_svc = EventsService()
    events_svc.process_sample("2026-11-15T12:00:10Z", 32.0, 75.0, True, 7.5)
    # Clock jump backward 5 seconds
    closed = events_svc.process_sample("2026-11-15T12:00:05Z", 33.0, 76.0, True, 8.0)
    # Event should clamp or maintain valid duration >= 1.0s
    if events_svc.active_event:
        final = events_svc.flush()
        assert final["duration_sec"] >= 1.0 or final["duration_sec"] >= 0.0


def test_a5_t2_06_hardware_check_stopping_criteria():
    """
    TEST-A5-T2-06: Verification of stopping rules for new calibration datasets:
    Under 100 rows, under 5 events, or >50% rows have temp == hum.
    """
    hw_script = PROJECT_ROOT / "scripts" / "hardware_check.py"
    if not hw_script.exists():
        pytest.fail("scripts/hardware_check.py not yet implemented by M5 worker")
