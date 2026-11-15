"""
backend/routes/client_routes.py
Client-facing REST endpoints for the digital thermohygrograph.
Enforces client-safe responses strictly through schemas and clean transformations.
"""

from __future__ import annotations
from datetime import datetime, timezone
import subprocess
import time
from typing import List, Optional
from fastapi import APIRouter, Query
from backend.database import check_db_health, get_recent_events, get_recent_readings
from backend.schemas.client_schemas import (
    ClientEvent,
    ClientReading,
    ClientStatusResponse,
)
from backend.schemas.health_schemas import HealthResponse
from backend.services.detector_service import detector_service
from backend.services.events_service import events_service
from backend.services.inference_service import inference_service
from backend.services.serial_service import serial_service

router = APIRouter(tags=["client"])

APP_START_TIME: float = time.time()


def get_git_commit_hash() -> str:
    """Retrieve git HEAD commit hash, with resilient fallback."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=1.0,
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except Exception:
        pass
    return "6ebc827"


@router.get("/api/health", response_model=HealthResponse)
def health_check():
    """
    Comprehensive system health and fault reporting endpoint.
    Reports serial state, reading age, database status, model version, commit hash,
    uptime, and flags warnings for sensor faults or degraded states.
    """
    # 1. Serial state & reading age
    ser_health = serial_service.get_health_status()
    serial_state = ser_health["serial_state"]
    reading_age = ser_health["last_reading_age_seconds"]

    # If serial service hasn't seen a reading yet, check newest DB reading
    recent = get_recent_readings(limit=1)
    if recent and reading_age is None:
        last_ts = recent[0]["timestamp"]
        try:
            clean_ts = last_ts.replace("Z", "+00:00")
            if "T" in clean_ts:
                dt = datetime.fromisoformat(clean_ts)
            else:
                dt = datetime.strptime(clean_ts[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            reading_age = max(0.0, round((datetime.now(timezone.utc) - dt).total_seconds(), 2))
        except Exception:
            reading_age = None

    # 2. Database status
    db_status = check_db_health()

    # 3. Anomaly detector model status
    is_degraded = getattr(detector_service, "is_degraded", False) or getattr(inference_service, "is_degraded", False)
    degraded_reason = getattr(detector_service, "degraded_reason", None) or getattr(inference_service, "degraded_reason", None)
    model_ver = "v2.0-hybrid"

    # 4. Commit hash & uptime
    commit_hash = get_git_commit_hash()
    uptime = max(0.0, round(time.time() - APP_START_TIME, 2))

    # 5. Humidity identical to temperature for >= 30 readings warning
    warning = ser_health.get("sensor_fault_warning")
    if warning is None:
        recent_30 = get_recent_readings(limit=30)
        if len(recent_30) >= 30 and all(abs(r["temperature"] - r["humidity"]) < 1e-4 for r in recent_30):
            warning = "humidity identical to temperature for >= 30 readings (suspected sensor fault)"

    # Determine overall status
    if db_status != "connected":
        overall_status = "unhealthy"
        details = f"Database status: {db_status}"
    elif is_degraded:
        overall_status = "degraded"
        details = degraded_reason or "Detector model degraded"
    elif warning is not None:
        overall_status = "degraded"
        details = warning
    else:
        overall_status = "healthy"
        details = None

    return HealthResponse(
        status=overall_status,
        serial_state=serial_state,
        last_reading_age_seconds=reading_age,
        database_status=db_status,
        model_version=model_ver,
        commit_hash=commit_hash,
        uptime_seconds=uptime,
        details=details,
        warning=warning,
    )


@router.get("/api/client/status", response_model=ClientStatusResponse)
def get_client_status():
    # Step 1: Query serial service status
    ser_st = serial_service.get_status()
    is_streaming = ser_st["is_streaming"]
    stream_source = ser_st["stream_source"]
    serial_state = ser_st.get("serial_state", "disconnected")
    age_sec = ser_st.get("last_reading_age_seconds")

    # Step 2: Determine system status: Live, Simulated, or Offline (transitions to Offline after 60s silence)
    if not is_streaming or serial_state == "offline" or (age_sec is not None and age_sec >= 60.0):
        status_label = "Offline"
    elif is_streaming:
        status_label = "Simulated" if stream_source == "simulation" else "Live"
    else:
        status_label = "Offline"

    # Step 3: Get recent readings to extract latest values
    recent = get_recent_readings(limit=1)
    last_ts = recent[0]["timestamp"] if recent else None
    cur_temp = recent[0]["temperature"] if recent else None
    cur_hum = recent[0]["humidity"] if recent else None

    # Step 4: Check if detector is degraded
    is_degraded = getattr(detector_service, "is_degraded", False) or getattr(inference_service, "is_degraded", False)
    
    # Step 5: Check if an active unusual reading is currently occurring
    active_ev = events_service.active_event
    is_unusual = active_ev is not None

    # Step 6: Compose headline sentence
    if is_degraded:
        headline = "Detector unavailable"
    elif is_unusual:
        time_part = active_ev["start_time"][11:16] if len(active_ev["start_time"]) >= 16 else active_ev["start_time"]
        diff_temp = round(active_ev["peak_temp"] - events_service.normal_temp_mean, 1)
        direction = "rose" if diff_temp > 0 else "dropped"
        dur_s = int((active_ev["end_dt"] - active_ev["start_dt"]).total_seconds())
        headline = f"Unusual reading at {time_part}: temperature {direction} {abs(diff_temp):.1f} °C for about {max(2, dur_s)} seconds."
    else:
        headline = "The room is normal."

    # Step 6: Compose supporting text
    if is_degraded:
        supporting = "Anomaly detector model is unavailable. Please check model artifacts."
    elif cur_temp is not None and cur_hum is not None:
        supporting = f"Current reading: {cur_temp:.1f} °C, {cur_hum:.1f}% RH."
    else:
        supporting = "No readings yet. Start the sensor or switch to the demo."

    # Step 7: Compute staleness and offline time
    offline_time = None
    is_stale = False
    stale_text = ""

    if status_label == "Offline":
        if last_ts and len(last_ts) >= 16:
            offline_time = last_ts[11:16]
        elif last_ts:
            offline_time = last_ts
    else:
        if last_ts:
            try:
                ts_clean = last_ts.replace("Z", "+00:00")
                if "T" in ts_clean:
                    dt = datetime.fromisoformat(ts_clean)
                else:
                    dt = datetime.strptime(ts_clean[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                now_utc = datetime.now(timezone.utc)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                diff_sec = max(0.0, (now_utc - dt).total_seconds())
                if diff_sec > 20.0:
                    is_stale = True
                    if diff_sec < 60.0:
                        stale_text = f"Last reading {int(diff_sec)} s ago."
                    else:
                        mins = max(1, round(diff_sec / 60.0))
                        stale_text = f"Last reading {mins} min ago."
            except Exception:
                is_stale = False
                stale_text = ""

    return ClientStatusResponse(
        status=status_label,
        last_reading_time=last_ts,
        current_temperature=cur_temp,
        current_humidity=cur_hum,
        active_unusual_reading=is_unusual,
        headline=headline,
        supporting_text=supporting,
        offline_time=offline_time,
        is_stale=is_stale,
        stale_text=stale_text,
    )


@router.get("/api/client/readings", response_model=List[ClientReading])
def get_client_readings(limit: int = Query(500, ge=1, le=5000)):
    # Step 1: Fetch recent readings from database
    raw_readings = get_recent_readings(limit=limit)
    # Step 2: Format through client-safe schema
    return [
        ClientReading(
            id=r["id"],
            timestamp=r["timestamp"],
            temperature=r["temperature"],
            humidity=r["humidity"],
            is_simulated=r["is_simulated"],
        )
        for r in raw_readings
    ]


@router.get("/api/client/events", response_model=List[ClientEvent])
def get_client_events(limit: int = Query(50, ge=1, le=200)):
    # Step 1: Fetch recent events from database
    raw_events = get_recent_events(limit=limit)
    # Step 2: Format through client-safe schema
    return [
        ClientEvent(
            id=e["id"],
            start_time=e["start_time"],
            end_time=e["end_time"],
            duration_sec=e["duration_sec"],
            peak_temp=e["peak_temp"],
            peak_hum=e["peak_hum"],
            delta_temp=e["delta_temp"],
            what_changed=e["what_changed"],
            severity=e["severity"],
            sentence=e["sentence"],
        )
        for e in raw_events
    ]
