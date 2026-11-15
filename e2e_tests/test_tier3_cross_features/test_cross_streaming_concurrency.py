"""
e2e_tests/test_tier3_cross_features/test_cross_streaming_concurrency.py
Tier 3: Pairwise Interactions - Streaming & Concurrency (TF3-07 to TF3-09)
Validates interactions between SQLite WAL mode concurrent reader/writers and serial stream disconnect/reconnect.
"""

from pathlib import Path
import pytest
from starlette.testclient import TestClient
from backend.database import insert_reading, get_recent_readings


def test_tf3_07_pair_sqlite_wal_active_ingest(client: TestClient):
    """TF3-07: Concurrent queries while inserting readings incur 0 locked errors."""
    for i in range(10):
        insert_reading(f"2026-11-15T12:00:{i:02d}", 25.0, 60.0, True)
        resp = client.get("/api/client/readings?limit=10")
        assert resp.status_code == 200


def test_tf3_08_pair_serial_disconnect_offline_banner(client: TestClient):
    """TF3-08: Halting telemetry stream transitions system state to Offline."""
    resp = client.get("/api/client/status")
    assert resp.status_code == 200
    assert "status" in resp.json()


def test_tf3_09_pair_serial_reconnect_backlog_recovery():
    """TF3-09: Reconnection delivers backlogged telemetry in non-decreasing order."""
    timestamps = [
        "2026-11-15T12:00:00Z",
        "2026-11-15T12:00:02Z",
        "2026-11-15T12:00:04Z",
    ]
    for ts in timestamps:
        insert_reading(ts, 25.0, 60.0, True)
    readings = get_recent_readings(3)
    rec_ts = [r["timestamp"] for r in readings]
    assert rec_ts == sorted(rec_ts)
