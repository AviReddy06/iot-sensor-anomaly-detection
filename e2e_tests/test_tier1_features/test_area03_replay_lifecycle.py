"""
e2e_tests/test_tier1_features/test_area03_replay_lifecycle.py
Area 3: Deterministic Simulation Replay & Event Lifecycle (Feature 5)
Tier 1 Tests: Simulation replay, anomaly detection accuracy, SQLite persistence, settings roundtrip.
"""

from pathlib import Path
import csv
import pytest
from starlette.testclient import TestClient
from backend.services.events_service import EventsService
from backend.database import insert_reading, insert_event, get_recent_readings, get_recent_events


def test_a3_t1_01_deterministic_replay_start_time(test_csv_path: Path):
    """
    TEST-A3-T1-01: Deterministic Replay Event Start Timestamp Verification.
    Scores test_data_with_labels.csv through real detector_service and verifies
    first anomaly event begins at 2026-10-27 22:03:29 without using ground-truth label column.
    """
    import pandas as pd
    from backend.services.detector_service import detector_service

    assert test_csv_path.exists(), f"Test CSV missing at {test_csv_path}"
    df = pd.read_csv(test_csv_path)
    df_feat, _ = detector_service.evaluate_dataframe(df)

    events_svc = EventsService()
    anomalies_detected = []

    for _, row in df_feat.iterrows():
        ts = str(row["timestamp"])
        temp = float(row["temperature"])
        hum = float(row["humidity"])
        flag = bool(row["anomaly_flag"])
        norm_t_mean = 25.67
        norm_t_std = 0.83
        peak_z = max(abs(temp - norm_t_mean) / norm_t_std, float(row["ewma_z"]))
        closed = events_svc.process_sample(ts, temp, hum, flag, peak_z)
        if closed:
            anomalies_detected.append(closed)

    final_event = events_svc.flush()
    if final_event:
        anomalies_detected.append(final_event)

    assert len(anomalies_detected) >= 1, "Expected at least 1 event generated during replay"
    first_event = anomalies_detected[0]
    assert "2026-10-27 22:03:29" in first_event["start_time"] or "2026-10-27T22:03:29" in first_event["start_time"]


def test_a3_t1_02_deterministic_replay_severity_high(test_csv_path: Path):
    """
    TEST-A3-T1-02: Peak temperature excursion results in High severity event.
    Scored through real detector_service; peak temp 34.2 °C yields High severity.
    """
    import pandas as pd
    from backend.services.detector_service import detector_service

    assert test_csv_path.exists(), f"Test CSV missing at {test_csv_path}"
    df = pd.read_csv(test_csv_path)
    df_feat, _ = detector_service.evaluate_dataframe(df)

    events_svc = EventsService()
    finalized_events = []

    for _, row in df_feat.iterrows():
        ts = str(row["timestamp"])
        temp = float(row["temperature"])
        hum = float(row["humidity"])
        flag = bool(row["anomaly_flag"])
        norm_t_mean = 25.67
        norm_t_std = 0.83
        peak_z = max(abs(temp - norm_t_mean) / norm_t_std, float(row["ewma_z"]))
        closed = events_svc.process_sample(ts, temp, hum, flag, peak_z)
        if closed:
            finalized_events.append(closed)

    final_event = events_svc.flush()
    if final_event:
        finalized_events.append(final_event)

    assert len(finalized_events) == 1, f"Expected exactly 1 event, got {len(finalized_events)}"
    event = finalized_events[0]
    assert event["severity"] == "High"
    assert event["peak_temp"] >= 34.0
    assert 15.0 <= event["duration_sec"] <= 25.0


def test_a3_t1_03_sensor_readings_sqlite_roundtrip(client: TestClient):
    """
    TEST-A3-T1-03: Sensor Readings SQLite Round-Trip Persistence.
    Readings inserted persist to SQLite and are returned by /api/client/readings.
    """
    insert_reading("2026-11-15T12:00:00Z", 24.5, 58.2, is_simulated=True)
    insert_reading("2026-11-15T12:00:02Z", 24.6, 58.4, is_simulated=True)

    response = client.get("/api/client/readings?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2

    # Check most recent reading
    temps = [r["temperature"] for r in data]
    assert 24.5 in temps or 24.6 in temps


def test_a3_t1_04_events_sqlite_roundtrip(client: TestClient):
    """
    TEST-A3-T1-04: Events SQLite Round-Trip Persistence.
    Events inserted persist to SQLite and are returned by /api/client/events.
    """
    insert_event(
        start_time="2026-11-15T12:00:00Z",
        end_time="2026-11-15T12:00:20Z",
        duration_sec=20.0,
        peak_temp=33.5,
        peak_hum=75.0,
        delta_temp=8.0,
        what_changed="temperature rose 8.0 °C",
        severity="High",
        sentence="Unusual reading at 12:00: temperature rose 8.0 °C for about 20 seconds.",
    )

    response = client.get("/api/client/events?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    event = data[0]
    assert event["severity"] == "High"
    assert event["peak_temp"] == 33.5
    assert "unusual" in event["sentence"].lower()


def test_a3_t1_05_sensitivity_setting_and_audit_roundtrip(client: TestClient, admin_token: str):
    """
    TEST-A3-T1-05: Sensitivity Setting Lifecycle & Audit Trail Round-Trip.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Set sensitivity to Low
    resp = client.post("/api/admin/settings/sensitivity", json={"level": "Low"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json().get("sensitivity") == "Low"

    # Verify query returns Low
    get_resp = client.get("/api/admin/settings/sensitivity", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json().get("sensitivity") == "Low"

    # Verify audit log recorded the change
    audit_resp = client.get("/api/admin/audit?limit=5", headers=headers)
    assert audit_resp.status_code == 200
    audit_entries = audit_resp.json()
    assert isinstance(audit_entries, list)
    actions = [e.get("action") for e in audit_entries]
    assert any("SENSITIVITY" in a for a in actions), f"SENSITIVITY action not found in {actions}"
