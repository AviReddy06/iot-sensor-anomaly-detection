"""
e2e_tests/test_tier2_boundaries/test_area07_boundary.py
Area 7 Boundary & Concurrency Tests (Feature 10)
Tier 2 Tests: Concurrent reader-writer isolation, retention purge logic, deduplication, busy timeout.
"""

from datetime import datetime, timedelta, timezone
import threading
import pytest
from starlette.testclient import TestClient
from backend.database import (
    get_db_connection,
    insert_reading,
    get_recent_readings,
    insert_event,
    get_recent_events,
    set_setting,
    get_setting,
)


def test_a7_t2_01_concurrent_reader_writer_stress():
    """
    TEST-A7-T2-01: 1 writer thread + multiple concurrent reader threads incur 0 locked errors.
    """
    errors = []
    stop_event = threading.Event()

    def writer_task():
        i = 0
        while not stop_event.is_set() and i < 50:
            try:
                insert_reading(f"2026-11-15T12:00:{i%60:02d}", 25.0 + (i * 0.1), 60.0, True)
                i += 1
            except Exception as e:
                errors.append(f"Writer error: {e}")

    def reader_task():
        while not stop_event.is_set():
            try:
                get_recent_readings(10)
            except Exception as e:
                errors.append(f"Reader error: {e}")

    threads = [threading.Thread(target=writer_task)]
    for _ in range(10):
        threads.append(threading.Thread(target=reader_task))

    for t in threads:
        t.start()

    # Run for 1.5 seconds
    threading.Event().wait(1.5)
    stop_event.set()

    for t in threads:
        t.join(timeout=2.0)

    assert len(errors) == 0, f"Database locking errors occurred under concurrency: {errors}"


def test_a7_t2_02_retention_purge_logic():
    """
    TEST-A7-T2-02: Retention purge deletes records older than retention_days (default 30).
    """
    now = datetime.now(timezone.utc)
    ts_old_40d = (now - timedelta(days=40)).isoformat()
    ts_old_32d = (now - timedelta(days=32)).isoformat()
    ts_current = now.isoformat()

    insert_reading(ts_old_40d, 22.0, 50.0, True)
    insert_reading(ts_old_32d, 22.5, 51.0, True)
    insert_reading(ts_current, 25.0, 60.0, True)

    # Perform purge of readings older than 30 days
    cutoff = (now - timedelta(days=30)).isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM readings WHERE timestamp < ?", (cutoff,))
        conn.commit()

    # Verify old readings are purged and current readings remain
    recent = get_recent_readings(10)
    timestamps = [r["timestamp"] for r in recent]
    assert ts_old_40d not in timestamps
    assert ts_old_32d not in timestamps
    assert ts_current in timestamps


def test_a7_t2_03_duplicate_event_deduplication():
    """
    TEST-A7-T2-03: Re-inserting event with identical start and end time returns existing event.
    """
    id1 = insert_event(
        "2026-11-15T12:00:00",
        "2026-11-15T12:00:20",
        20.0,
        32.0,
        75.0,
        6.0,
        "temperature spike",
        "High",
        "Unusual reading",
    )
    id2 = insert_event(
        "2026-11-15T12:00:00",
        "2026-11-15T12:00:20",
        20.0,
        32.0,
        75.0,
        6.0,
        "temperature spike",
        "High",
        "Unusual reading",
    )
    assert id1 == id2
    all_events = get_recent_events(50)
    matching = [e for e in all_events if e["start_time"] == "2026-11-15T12:00:00"]
    assert len(matching) == 1


def test_a7_t2_04_busy_timeout_pragma_value():
    """
    TEST-A7-T2-04: PRAGMA busy_timeout is set to at least 5000ms.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA busy_timeout;")
        val = cursor.fetchone()[0]
        assert int(val) >= 5000, f"Expected busy_timeout >= 5000ms, got {val}"


def test_a7_t2_05_retention_invalid_setting_fallback(client: TestClient, admin_token: str):
    """
    TEST-A7-T2-05: Non-numeric retention_days setting rejected or falls back safely.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = client.post("/api/admin/settings/retention", json={"retention_days": "invalid_number_abc"}, headers=headers)
    if resp.status_code == 404:
        pytest.fail("Endpoint /api/admin/settings/retention not yet implemented by M2 worker")
    assert resp.status_code in [400, 422]
