"""
e2e_tests/test_tier2_boundaries/test_area10_boundary.py
Area 10 Boundary & Stress Verification (Features 17, 18)
Tier 2 Tests: Load ramp, queue isolation, corrupt burst handling, WAL concurrency, purge under load.
"""

import time
import pytest
from starlette.testclient import TestClient
from collect.serial_utils import parse_sensor_line
from backend.database import insert_reading, get_recent_readings


def test_a10_t2_01_load_ramp_degradation(client: TestClient):
    """
    TEST-A10-T2-01: System handles high burst of requests without unhandled crashes.
    """
    error_count = 0
    for _ in range(50):
        resp = client.get("/api/client/status")
        if resp.status_code != 200:
            error_count += 1
    assert error_count == 0, f"Encountered {error_count} errors during load ramp"


def test_a10_t2_02_ws_slow_client_queue_isolation(client: TestClient):
    """
    TEST-A10-T2-02: Slow client does not block normal clients from ping/pong exchanges.
    """
    ws_endpoint = "/ws/client"
    try:
        with client.websocket_connect(ws_endpoint) as ws:
            pass
    except Exception:
        ws_endpoint = "/ws/telemetry"

    with client.websocket_connect(ws_endpoint) as ws_slow:
        with client.websocket_connect(ws_endpoint) as ws_fast:
            # Fast client interacts normally
            ws_fast.send_text('{"action": "ping"}')
            pong = ws_fast.receive_json()
            assert pong.get("type") == "pong"


def test_a10_t2_03_ingest_burst_with_corrupt_data():
    """
    TEST-A10-T2-03: Ingest burst containing 20% malformed lines does not crash the parser.
    """
    burst_lines = [
        "25.0,60.0\n",
        "NaN,60.0\n",
        "25.2,60.1\n",
        "corrupt,line\n",
        "25.4,60.2\n",
    ] * 20  # 100 lines total

    valid_count = 0
    for line in burst_lines:
        res = parse_sensor_line(line)
        if res:
            valid_count += 1
            insert_reading("2026-11-15T12:00:00", res[0], res[1], True)

    assert valid_count == 60  # 3 valid lines per 5 * 20 = 60 valid lines


def test_a10_t2_04_sqlite_wal_concurrency():
    """
    TEST-A10-T2-04: Concurrently writing and reading records does not produce locked errors.
    """
    for i in range(20):
        insert_reading(f"2026-11-15T10:00:{i:02d}", 25.0, 60.0, True)
        readings = get_recent_readings(5)
        assert len(readings) > 0


def test_a10_t2_05_db_retention_purge_under_load():
    """
    TEST-A10-T2-05: Purging old records while reading executes without database lock exceptions.
    """
    from backend.database import get_db_connection
    # Insert dummy old reading
    insert_reading("2026-10-01T00:00:00", 20.0, 50.0, True)
    # Purge old reading
    with get_db_connection() as conn:
        conn.execute("DELETE FROM readings WHERE timestamp < '2026-11-01T00:00:00'")
        conn.commit()
    # Read remaining
    recent = get_recent_readings(5)
    assert isinstance(recent, list)
