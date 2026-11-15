"""
backend/database.py
SQLite relational database storage for readings, unusual events, settings, and audit logs.
Hardened for high-concurrency WAL mode, 1 writer + 50 readers resilience, timestamp indexing,
and 30-day data retention purge.
"""

from __future__ import annotations
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import sqlite3
import threading
from typing import Any, Dict, List, Optional, Set
from backend.config import DB_PATH, DEFAULT_DB_PATH

# Synchronization primitives
_local = threading.local()
_write_lock = threading.Lock()
_init_lock = threading.Lock()
_registry_lock = threading.Lock()

_initialized_paths: Set[str] = set()
_open_connections: Set[sqlite3.Connection] = set()


def _get_current_db_path() -> Path:
    if os.environ.get("DB_PATH"):
        p = Path(os.environ["DB_PATH"])
    elif DB_PATH != DEFAULT_DB_PATH:
        p = Path(str(DB_PATH))
    else:
        p = DEFAULT_DB_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def get_db_connection() -> sqlite3.Connection:
    """
    Returns a thread-local SQLite connection configured with WAL mode,
    busy_timeout=5000, synchronous=NORMAL, and row factory.
    Reuses connection per thread to avoid descriptor churn and handle leaks.
    """
    current_path = _get_current_db_path()
    resolved_str = str(current_path.resolve())

    # Detect if cached connection belongs to a different database path (e.g. test isolation)
    cached_path = getattr(_local, "db_path_str", None)
    cached_conn: Optional[sqlite3.Connection] = getattr(_local, "conn", None)

    if cached_conn is not None:
        if cached_path != resolved_str:
            try:
                cached_conn.close()
            except Exception:
                pass
            with _registry_lock:
                _open_connections.discard(cached_conn)
            cached_conn = None
            _local.conn = None
        else:
            try:
                cached_conn.total_changes
                return cached_conn
            except (sqlite3.ProgrammingError, sqlite3.OperationalError):
                cached_conn = None
                _local.conn = None

    # Create new connection for current thread
    conn = sqlite3.connect(
        str(current_path),
        timeout=5.0,
        check_same_thread=False,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA foreign_keys = ON;")

    _local.conn = conn
    _local.db_path_str = resolved_str

    with _registry_lock:
        _open_connections.add(conn)

    # Initialize schema once per resolved database path with double-checked locking
    if resolved_str not in _initialized_paths:
        with _init_lock:
            if resolved_str not in _initialized_paths:
                _init_db_with_conn(conn)
                _initialized_paths.add(resolved_str)

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
    # Schema Indexes on Timestamps for fast queries and purge
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_readings_timestamp ON readings(timestamp);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_start_time ON events(start_time);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp);")
    conn.commit()


def init_db() -> None:
    conn = get_db_connection()
    with _init_lock:
        _init_db_with_conn(conn)


def check_db_health() -> str:
    """Returns 'connected', 'locked', or 'error' for /api/health."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        cur.fetchone()
        return "connected"
    except sqlite3.OperationalError as exc:
        err_msg = str(exc).lower()
        if "locked" in err_msg or "busy" in err_msg:
            return "locked"
        return "error"
    except Exception:
        return "error"


def close_db() -> None:
    """Orderly closes all tracked connections and checkpoints WAL on shutdown."""
    with _registry_lock:
        conns = list(_open_connections)
        _open_connections.clear()

    # Attempt checkpoint before closing connections
    if conns:
        try:
            conns[0].execute("PRAGMA wal_checkpoint(TRUNCATE);")
            conns[0].execute("PRAGMA optimize;")
        except Exception:
            pass

    for conn in conns:
        try:
            conn.close()
        except Exception:
            pass

    if hasattr(_local, "conn"):
        _local.conn = None
        _local.db_path_str = None


def insert_reading(timestamp: str, temperature: float, humidity: float, is_simulated: bool = False) -> int:
    with _write_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO readings (timestamp, temperature, humidity, is_simulated) VALUES (?, ?, ?, ?)",
            (timestamp, round(temperature, 1), round(humidity, 1), 1 if is_simulated else 0),
        )
        conn.commit()
        return int(cursor.lastrowid)


def get_recent_readings(limit: int = 100) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, timestamp, temperature, humidity, is_simulated FROM readings ORDER BY id DESC LIMIT ?",
        (limit,),
    )
    rows = cursor.fetchall()
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
    with _write_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        st_norm = start_time.replace("T", " ")[:19]
        cursor.execute(
            """
            SELECT id FROM events 
            WHERE replace(substr(start_time, 1, 19), 'T', ' ') = ?
            """,
            (st_norm,),
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
    conn = get_db_connection()
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
    now_str = datetime.now(timezone.utc).isoformat()
    with _write_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO audit_log (timestamp, action, actor, details) VALUES (?, ?, ?, ?)",
            (now_str, action, actor, details),
        )
        conn.commit()


def get_audit_logs(limit: int = 100) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, timestamp, action, actor, details FROM audit_log ORDER BY id DESC LIMIT ?",
        (limit,),
    )
    return [dict(r) for r in cursor.fetchall()]


def set_setting(key: str, value: str) -> None:
    now_str = datetime.now(timezone.utc).isoformat()
    with _write_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (key, value, now_str),
        )
        conn.commit()


def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    return str(row["value"]) if row else default


# Data Retention & Purge
def get_retention_days() -> int:
    val = get_setting("retention_days")
    if val is not None:
        try:
            ret = int(val)
            if ret >= 1:
                return ret
        except ValueError:
            pass
    try:
        ret = int(os.environ.get("DATA_RETENTION_DAYS", "30"))
        if ret >= 1:
            return ret
        return 30
    except ValueError:
        return 30


def set_retention_days(days: int) -> None:
    if days < 1:
        raise ValueError(f"Retention days must be at least 1, got {days}")
    set_setting("retention_days", str(days))


def purge_old_readings(days: Optional[int] = None, cutoff_timestamp: Optional[str] = None) -> int:
    """
    Purges readings older than specified days (default: get_retention_days())
    or an explicit cutoff timestamp. Uses idx_readings_timestamp for efficient index range delete.
    Returns count of deleted rows.
    """
    if days is not None and days < 1:
        raise ValueError(f"Purge retention days must be at least 1, got {days}")

    if cutoff_timestamp is None:
        if days is None:
            days = get_retention_days()
            if days < 1:
                days = 30
        cutoff_dt = datetime.now(timezone.utc) - timedelta(days=days)
        cutoff_timestamp = cutoff_dt.isoformat()
    else:
        try:
            _ = datetime.fromisoformat(cutoff_timestamp.replace("Z", "+00:00"))
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Invalid cutoff_timestamp: '{cutoff_timestamp}'. Must be a valid ISO 8601 string.") from exc

    with _write_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM readings WHERE timestamp < ?", (cutoff_timestamp,))
        deleted_count = cursor.rowcount
        conn.commit()

    if deleted_count > 0:
        log_audit("DATA_PURGED", "system", f"Purged {deleted_count} readings older than {cutoff_timestamp}")

    return int(deleted_count)
