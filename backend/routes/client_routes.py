"""
backend/routes/client_routes.py
Client-facing REST endpoints for the digital thermohygrograph.
Enforces client-safe responses strictly through schemas and clean transformations.
"""

from __future__ import annotations
from typing import List
from fastapi import APIRouter, Query
from backend.database import get_recent_events, get_recent_readings
from backend.schemas.client_schemas import (
    ClientEvent,
    ClientReading,
    ClientStatusResponse,
)
from backend.services.events_service import events_service
from backend.services.serial_service import serial_service

router = APIRouter(tags=["client"])


@router.get("/api/health")
def health_check():
    # Step 1: Simple health ping
    return {"status": "ok"}


@router.get("/api/client/status", response_model=ClientStatusResponse)
def get_client_status():
    # Step 1: Query serial service status
    ser_st = serial_service.get_status()
    is_streaming = ser_st["is_streaming"]
    stream_source = ser_st["stream_source"]

    # Step 2: Determine system status: Live, Simulated, or Offline
    if is_streaming:
        status_label = "Simulated" if stream_source == "simulation" else "Live"
    else:
        status_label = "Offline"

    # Step 3: Get recent readings to extract latest values
    recent = get_recent_readings(limit=1)
    last_ts = recent[0]["timestamp"] if recent else None
    cur_temp = recent[0]["temperature"] if recent else None
    cur_hum = recent[0]["humidity"] if recent else None

    # Step 4: Check if an active unusual reading is currently occurring
    active_ev = events_service.active_event
    is_unusual = active_ev is not None

    # Step 5: Compose headline sentence
    if is_unusual:
        time_part = active_ev["start_time"][11:16] if len(active_ev["start_time"]) >= 16 else active_ev["start_time"]
        diff_temp = round(active_ev["peak_temp"] - events_service.normal_temp_mean, 1)
        direction = "rose" if diff_temp > 0 else "dropped"
        dur_s = int((active_ev["end_dt"] - active_ev["start_dt"]).total_seconds())
        headline = f"Unusual reading at {time_part}: temperature {direction} {abs(diff_temp):.1f} °C for about {max(2, dur_s)} seconds."
    else:
        headline = "The room is normal."

    # Step 6: Compose supporting text
    if cur_temp is not None and cur_hum is not None:
        supporting = f"Current reading: {cur_temp:.1f} °C, {cur_hum:.1f}% RH."
    else:
        supporting = "No readings yet. Start the sensor or switch to the demo."

    return ClientStatusResponse(
        status=status_label,
        last_reading_time=last_ts,
        current_temperature=cur_temp,
        current_humidity=cur_hum,
        active_unusual_reading=is_unusual,
        headline=headline,
        supporting_text=supporting,
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
