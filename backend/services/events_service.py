"""
backend/services/events_service.py
Aggregates anomalous telemetry rows into structured unusual incidents.
Applies temporal grouping within 10 seconds and determines severity.
Rule: Low if peak z < 4, Medium if peak z < 8, High if peak z >= 8.
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from backend.database import insert_event, log_audit


class EventsService:
    def __init__(self, normal_temp_mean: float = 25.67, normal_hum_mean: float = 61.42):
        # Step 1: Normal baseline reference means
        self.normal_temp_mean = normal_temp_mean
        self.normal_hum_mean = normal_hum_mean
        # Step 2: In-memory active event tracking
        self.active_event: Optional[Dict[str, Any]] = None
        self.last_flag_time: Optional[datetime] = None

    def process_sample(
        self,
        timestamp_str: str,
        temperature: float,
        humidity: float,
        is_flagged: bool,
        peak_z: float,
    ) -> Optional[Dict[str, Any]]:
        # Step 1: Parse current timestamp
        current_dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        
        # Step 2: Handle ongoing active event closure if no flag for > 10 seconds
        if self.active_event and (not is_flagged or (self.last_flag_time and (current_dt - self.last_flag_time).total_seconds() > 10.0)):
            closed_event = self._finalize_event()
            if is_flagged:
                self._start_new_event(current_dt, timestamp_str, temperature, humidity, peak_z)
            return closed_event

        # Step 3: If flagged, either update active event or start new one
        if is_flagged:
            if not self.active_event:
                self._start_new_event(current_dt, timestamp_str, temperature, humidity, peak_z)
            else:
                self._update_event(current_dt, timestamp_str, temperature, humidity, peak_z)

        return None

    def _start_new_event(
        self,
        dt: datetime,
        ts_str: str,
        temp: float,
        hum: float,
        peak_z: float,
    ) -> None:
        # Step 1: Initialize new event record
        self.last_flag_time = dt
        self.active_event = {
            "start_dt": dt,
            "end_dt": dt,
            "start_time": ts_str,
            "end_time": ts_str,
            "peak_temp": temp,
            "peak_hum": hum,
            "min_temp": temp,
            "min_hum": hum,
            "max_peak_z": peak_z,
            "row_count": 1,
        }

    def _update_event(
        self,
        dt: datetime,
        ts_str: str,
        temp: float,
        hum: float,
        peak_z: float,
    ) -> None:
        # Step 1: Extend active event boundaries and update peaks
        self.last_flag_time = dt
        ev = self.active_event
        ev["end_dt"] = dt
        ev["end_time"] = ts_str
        ev["peak_temp"] = max(ev["peak_temp"], temp)
        ev["peak_hum"] = max(ev["peak_hum"], hum)
        ev["min_temp"] = min(ev["min_temp"], temp)
        ev["min_hum"] = min(ev["min_hum"], hum)
        ev["max_peak_z"] = max(ev["max_peak_z"], peak_z)
        ev["row_count"] += 1

    def _finalize_event(self) -> Optional[Dict[str, Any]]:
        # Step 1: Compute duration and deltas
        if not self.active_event:
            return None
        ev = self.active_event
        self.active_event = None
        self.last_flag_time = None

        duration_sec = max(1.0, (ev["end_dt"] - ev["start_dt"]).total_seconds())
        delta_temp = round(ev["peak_temp"] - self.normal_temp_mean, 1)
        delta_hum = round(ev["peak_hum"] - self.normal_hum_mean, 1)

        # Step 2: Determine severity: Low < 4, Medium < 8, High >= 8
        pz = ev["max_peak_z"]
        if pz < 4.0:
            severity = "Low"
        elif pz < 8.0:
            severity = "Medium"
        else:
            severity = "High"

        # Step 3: Determine what changed description
        changes = []
        if abs(delta_temp) >= 0.5:
            direction = "rose" if delta_temp > 0 else "dropped"
            changes.append(f"temperature {direction} {abs(delta_temp):.1f} °C")
        if abs(delta_hum) >= 2.0:
            direction = "rose" if delta_hum > 0 else "dropped"
            changes.append(f"humidity {direction} {abs(delta_hum):.1f}% RH")
        what_changed = ", ".join(changes) if changes else "sensor telemetry shifted"

        # Step 4: Format human sentence using the word 'unusual'
        time_display = ev["start_time"][11:16] if len(ev["start_time"]) >= 16 else ev["start_time"]
        dur_str = f"{int(round(duration_sec))} seconds" if duration_sec < 90 else f"{round(duration_sec / 60.0, 1)} minutes"
        sentence = f"Unusual reading at {time_display}: {what_changed} for about {dur_str}."

        # Step 5: Persist to SQLite
        insert_event(
            start_time=ev["start_time"],
            end_time=ev["end_time"],
            duration_sec=duration_sec,
            peak_temp=ev["peak_temp"],
            peak_hum=ev["peak_hum"],
            delta_temp=delta_temp,
            what_changed=what_changed,
            severity=severity,
            sentence=sentence,
        )
        log_audit("EVENT_DETECTED", "EventsService", f"{severity} severity: {sentence}")

        return {
            "start_time": ev["start_time"],
            "end_time": ev["end_time"],
            "duration_sec": duration_sec,
            "peak_temp": ev["peak_temp"],
            "peak_hum": ev["peak_hum"],
            "delta_temp": delta_temp,
            "what_changed": what_changed,
            "severity": severity,
            "sentence": sentence,
        }


events_service = EventsService()
