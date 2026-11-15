"""
e2e_tests/test_tier1_features/test_area07_sqlite_retention.py
Area 7: SQLite Concurrency & Data Retention (Feature 10)
Tier 1 Tests: WAL mode, busy timeout, indexes, and database CRUD operations.
"""

import sqlite3
import pytest
from backend.database import (
    get_db_connection,
    insert_reading,
    get_recent_readings,
    insert_event,
    get_recent_events,
    set_setting,
    get_setting,
)


def test_a7_t1_01_sqlite_wal_mode_or_configured():
    """
    TEST-A7-T1-01: SQLite WAL mode contract.
    Under concurrent production, journal_mode must strictly be WAL.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode;")
    mode = cursor.fetchone()[0]
    conn.close()
    assert mode.lower() == "wal", f"Mandatory WAL journal_mode not active: {mode}"


def test_a7_t1_02_sqlite_busy_timeout_configured():
    """
    TEST-A7-T1-02: SQLite busy_timeout configuration contract.
    Mandates busy_timeout >= 5000 ms to prevent lock errors under concurrent readers.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA busy_timeout;")
    timeout = cursor.fetchone()[0]
    conn.close()
    assert int(timeout) >= 5000, f"Mandatory busy_timeout of 5000ms not met: {timeout}"


def test_a7_t1_03_sqlite_tables_exist():
    """
    TEST-A7-T1-03: Required schema tables (readings, events, settings, audit_log) exist.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row["name"] for row in cursor.fetchall()]
    conn.close()

    required_tables = ["readings", "events", "settings", "audit_log"]
    for t in required_tables:
        assert t in tables, f"Required table '{t}' missing from SQLite database"


def test_a7_t1_04_readings_and_events_crud_roundtrip():
    """
    TEST-A7-T1-04: Full CRUD round-trip for readings and events in SQLite.
    """
    # Insert reading
    reading_id = insert_reading("2026-11-15T12:00:00", 25.4, 60.1, False)
    assert reading_id > 0
    readings = get_recent_readings(1)
    assert len(readings) == 1
    assert readings[0]["temperature"] == 25.4

    # Insert event
    event_id = insert_event(
        "2026-11-15T12:00:00",
        "2026-11-15T12:01:00",
        60.0,
        31.0,
        75.0,
        5.3,
        "temperature rose 5.3 °C",
        "High",
        "Unusual reading at 12:00: temperature rose 5.3 °C.",
    )
    assert event_id > 0
    events = get_recent_events(1)
    assert len(events) == 1
    assert events[0]["severity"] == "High"


def test_a7_t1_05_settings_persistence_and_retention_defaults():
    """
    TEST-A7-T1-05: Settings table persists and updates key-value entries.
    """
    set_setting("retention_days", "30")
    val = get_setting("retention_days")
    assert val == "30"

    set_setting("retention_days", "45")
    val_updated = get_setting("retention_days")
    assert val_updated == "45"
