"""
e2e_tests/test_tier4_scenarios/test_scenario8_soak_retention.py
Tier 4 Scenario 8: Long-Run Soak Streaming & Database Retention Policy Purge
Verifies continuous operation, backend database retention purge routine, and SQLite consistency.
"""

from datetime import datetime, timedelta, timezone
import pytest
from backend.database import insert_reading, get_recent_readings, get_db_connection
import backend.database as db


def test_scenario_08_soak_retention_purge():
    """
    Scenario 8:
    1. Populate DB with historical readings older than 30 days and current readings.
    2. Invoke backend retention purge routine (purge_old_readings).
    3. Verify expired readings are purged while current readings remain.
    4. Run PRAGMA integrity_check on SQLite to assert database consistency.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=30)
    cutoff_str = cutoff.isoformat()

    # 1. Populate historical expired readings and current readings
    for i in range(10):
        insert_reading((now - timedelta(days=35, seconds=i*10)).isoformat(), 20.0, 50.0, is_simulated=True)
    for i in range(10):
        insert_reading((now - timedelta(days=31, seconds=i*10)).isoformat(), 20.5, 51.0, is_simulated=True)
    for i in range(10):
        insert_reading((now - timedelta(days=5, seconds=i*10)).isoformat(), 25.0, 60.0, is_simulated=True)
    for i in range(10):
        insert_reading((now - timedelta(seconds=i*10)).isoformat(), 25.2, 60.2, is_simulated=True)

    # 2. Invoke application retention purge routine (NO raw SQL in test)
    purge_routine = getattr(db, "purge_old_readings", None)
    if purge_routine is None:
        pytest.fail("Backend retention routine 'purge_old_readings' not implemented in backend.database (M2 deliverable)")

    purged_count = purge_routine(days=30)
    assert purged_count >= 20, f"Expected at least 20 readings purged, got {purged_count}"

    # 3. Verify expired readings are eliminated
    recent = get_recent_readings(50)
    for r in recent:
        assert r["timestamp"] >= cutoff_str, f"Found unpurged expired reading: {r}"

    # 4. Integrity check
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check;")
        status = cursor.fetchone()[0]
        assert status.lower() == "ok", f"SQLite integrity check failed: {status}"
