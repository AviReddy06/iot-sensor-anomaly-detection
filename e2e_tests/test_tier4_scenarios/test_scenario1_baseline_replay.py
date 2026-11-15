"""
e2e_tests/test_tier4_scenarios/test_scenario1_baseline_replay.py
Tier 4 Scenario 1: Deterministic Baseline Replay & Anomaly Alert Lifecycle
Replays historical frozen hold-out dataset through the genuine ML detector and validates
exactly 1 High event without false alarms.
"""

from pathlib import Path
import pandas as pd
import pytest
from starlette.testclient import TestClient
from backend.services.detector_service import detector_service
from backend.services.events_service import events_service
from backend.database import insert_reading


def test_scenario_01_baseline_replay_alert_lifecycle(test_csv_path: Path, client: TestClient):
    """
    Scenario 1:
    1. Load test_data_with_labels.csv.
    2. Evaluate telemetry through genuine detector_service (Isolation Forest + Adaptive EWMA-Z).
    3. Confirm rows prior to 22:03:29 trigger zero anomaly flags.
    4. Confirm at 22:03:29, first anomaly triggers with peak temp >= 34.0 °C and High severity.
    5. Query /api/client/events and confirm exactly 1 incident produced across entire dataset.
    """
    assert test_csv_path.exists()
    df = pd.read_csv(test_csv_path)

    # 1. Run real detector inference (strictly NO CSV ground-truth shortcut)
    df_scored, info = detector_service.evaluate_dataframe(df)

    # 2. Confirm zero false alarms prior to incident onset
    pre_incident = df_scored[df_scored["timestamp"] < "2026-10-27 22:03:29"]
    assert pre_incident["anomaly_flag"].sum() == 0, (
        f"Detected {pre_incident['anomaly_flag'].sum()} false alarms prior to 22:03:29"
    )

    # 3. Process scored telemetry through events service and persist to SQLite
    events_service.reset()
    for _, row in df_scored.iterrows():
        ts = str(row["timestamp"])
        temp = float(row["temperature"])
        hum = float(row["humidity"])
        is_flagged = bool(row["anomaly_flag"])
        peak_z = float(abs(row["ewma_z"])) if "ewma_z" in row else 0.0

        insert_reading(ts, temp, hum, is_simulated=True)
        events_service.process_sample(ts, temp, hum, is_flagged, peak_z)

    # 4. Flush active event via public method
    events_service.flush()

    # 5. Assertions via client REST API
    resp = client.get("/api/client/events")
    assert resp.status_code == 200
    events = resp.json()
    assert len(events) == 1, f"Expected exactly 1 incident, found {len(events)}: {events}"

    event = events[0]
    assert "2026-10-27" in event["start_time"]
    assert "22:03:29" in event["start_time"]
    assert event["severity"] == "High"
    assert event["peak_temp"] >= 34.0
    assert "unusual" in event["sentence"].lower()

    # 6. Verify client status endpoint reflects current state
    status_resp = client.get("/api/client/status")
    assert status_resp.status_code == 200
