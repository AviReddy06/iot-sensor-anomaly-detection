"""
backend/database.py
SQLite relational database storage for readings, unusual events, settings, and audit logs.
Uses standard sqlite3 with thread-safe connections.
"""

from __future__ import annotations
from datetime import datetime, timezone
import sqlite3
from typing import Any, Dict, List, Optional
from backend.config import DB_PATH


_initialized: bool = False


def get_db_connection() -> sqlite3.Connection:
    global _initialized
    # Step 1: Ensure the parent directory of the database exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Step 2: Open SQLite connection with row factory
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    if not _initialized:
        _init_db_with_conn(conn)
        _initialized = True
    return conn


def _init_db_with_conn(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            temperature REAL NOT NULL,
            humidity REAL NOT NULL,
            is_simulated INTEGER NOT NULL DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            duration_sec REAL NOT NULL,
            peak_temp REAL NOT NULL,
            peak_hum REAL NOT NULL,
            delta_temp REAL NOT NULL,
            what_changed TEXT NOT NULL,
            severity TEXT NOT NULL,
            sentence TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            action TEXT NOT NULL,
            actor TEXT NOT NULL,
            details TEXT NOT NULL
        )
    """)
    conn.commit()


def init_db() -> None:
    with get_db_connection() as conn:
        _init_db_with_conn(conn)


def insert_reading(timestamp: str, temperature: float, humidity: float, is_simulated: bool = False) -> int:
    # Step 1: Open connection and insert row
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO readings (timestamp, temperature, humidity, is_simulated) VALUES (?, ?, ?, ?)",
            (timestamp, round(temperature, 1), round(humidity, 1), 1 if is_simulated else 0),
        )
        conn.commit()
        return int(cursor.lastrowid)


def get_recent_readings(limit: int = 100) -> List[Dict[str, Any]]:
    # Step 1: Retrieve recent readings in chronological order
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, timestamp, temperature, humidity, is_simulated FROM readings ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        rows = cursor.fetchall()
        # Step 2: Reverse so chronological order is returned
        return [
            {
                "id": r["id"],
                "timestamp": r["timestamp"],
                "temperature": r["temperature"],
                "humidity": r["humidity"],
                "is_simulated": bool(r["is_simulated"]),
            }
            for r in reversed(rows)
        ]


def insert_event(
    start_time: str,
    end_time: str,
    duration_sec: float,
    peak_temp: float,
    peak_hum: float,
    delta_temp: float,
    what_changed: str,
    severity: str,
    sentence: str,
) -> int:
    # Step 1: Prevent duplicate event insertion for identical time range
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id FROM events 
            WHERE start_time = ? AND end_time = ?
            """,
            (start_time, end_time),
        )
        existing = cursor.fetchone()
        if existing:
            return int(existing["id"])

        cursor.execute(
            """
            INSERT INTO events (
                start_time, end_time, duration_sec, peak_temp, peak_hum, delta_temp, what_changed, severity, sentence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                start_time,
                end_time,
                round(duration_sec, 1),
                round(peak_temp, 1),
                round(peak_hum, 1),
                round(delta_temp, 1),
                what_changed,
                severity,
                sentence,
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)


def get_recent_events(limit: int = 50) -> List[Dict[str, Any]]:
    # Step 1: Retrieve events sorted by most recent
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, start_time, end_time, duration_sec, peak_temp, peak_hum, delta_temp, what_changed, severity, sentence
            FROM events ORDER BY id DESC LIMIT ?
            """,
            (limit,),
        )
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def log_audit(action: str, actor: str, details: str) -> None:
    # Step 1: Record timestamped action in audit_log
    now_str = datetime.now(timezone.utc).isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO audit_log (timestamp, action, actor, details) VALUES (?, ?, ?, ?)",
            (now_str, action, actor, details),
        )
        conn.commit()


def get_audit_logs(limit: int = 100) -> List[Dict[str, Any]]:
    # Step 1: Retrieve audit logs
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, timestamp, action, actor, details FROM audit_log ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in cursor.fetchall()]


def set_setting(key: str, value: str) -> None:
    # Step 1: Upsert setting key-value pair
    now_str = datetime.now(timezone.utc).isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (key, value, now_str),
        )
        conn.commit()


def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    # Step 1: Query setting value by key
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return str(row["value"]) if row else default
