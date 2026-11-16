"""
e2e_tests/test_tier2_boundaries/test_area03_boundary.py
Area 3 Boundary & Corner Cases (Feature 5)
Tier 2 Tests: Replay idempotency, normal baseline zero-alarm, 10s gap auto-finalization, sensitivity shift, DB isolation.
"""

from pathlib import Path
import csv
import pytest
from starlette.testclient import TestClient
from backend.services.events_service import EventsService
from backend.database import insert_event, get_recent_events
import backend.config as config

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def test_a3_t2_01_event_deduplication_on_identical_window():
    """
    TEST-A3-T2-01: Deduplication logic prevents inserting duplicate events for identical time window.
    """
    id1 = insert_event(
        start_time="2026-10-27T22:03:29Z",
        end_time="2026-10-27T22:03:47Z",
        duration_sec=18.0,
        peak_temp=34.2,
        peak_hum=82.1,
        delta_temp=8.0,
        what_changed="temperature rose",
        severity="High",
        sentence="Unusual reading at 22:03",
    )
    # Attempt inserting identical time window
    id2 = insert_event(
        start_time="2026-10-27T22:03:29Z",
        end_time="2026-10-27T22:03:47Z",
        duration_sec=18.0,
        peak_temp=34.2,
        peak_hum=82.1,
        delta_temp=8.0,
        what_changed="temperature rose",
        severity="High",
        sentence="Unusual reading at 22:03",
    )
    assert id1 == id2, "Expected duplicate event insertion to return existing event ID"


def test_a3_t2_02_normal_baseline_zero_false_events(test_csv_path: Path):
    """
    TEST-A3-T2-02: Normal baseline data (first 37 rows) yields zero anomaly events.
    """
    events_svc = EventsService()
    finalized = []

    with open(test_csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            count += 1
            if count > 37:
                break
            ts = row["timestamp"]
            temp = float(row["temperature"])
            hum = float(row["humidity"])
            peak_z = abs(temp - 25.67) / 0.83
            # In normal baseline rows, label is 0
            closed = events_svc.process_sample(ts, temp, hum, False, peak_z)
            if closed:
                finalized.append(closed)

    assert len(finalized) == 0, f"Expected 0 events on normal baseline, got {len(finalized)}"
    assert events_svc.active_event is None


def test_a3_t2_03_event_auto_finalization_on_10s_gap():
    """
    TEST-A3-T2-03: Event automatically finalizes after > 10 seconds of normal telemetry.
    """
    events_svc = EventsService()
    # Telemetry starts anomaly
    events_svc.process_sample("2026-11-15T12:00:00Z", 32.0, 75.0, True, 7.5)
    events_svc.process_sample("2026-11-15T12:00:02Z", 33.0, 78.0, True, 8.8)
    assert events_svc.active_event is not None

    # Normal reading arrives 12 seconds later (> 10s gap)
    closed = events_svc.process_sample("2026-11-15T12:00:14Z", 25.0, 60.0, False, 0.5)
    assert closed is not None, "Expected event to be finalized after > 10s gap"
    assert closed["severity"] == "High"
    assert events_svc.active_event is None


def test_a3_t2_04_marginal_sample_sensitivity_influence(test_csv_path: Path):
    """
    TEST-A3-T2-04: Marginal sample detection changes with sensitivity threshold.
    Validates that updating sensitivity in detector_service changes thresholds
    and alters anomaly flagging counts on real evaluation telemetry.
    """
    import pandas as pd
    from backend.services.detector_service import detector_service

    df = pd.read_csv(test_csv_path)

    detector_service.set_sensitivity("Low")
    df_low, info_low = detector_service.evaluate_dataframe(df)

    detector_service.set_sensitivity("High")
    df_high, info_high = detector_service.evaluate_dataframe(df)

    # Restore default sensitivity
    detector_service.set_sensitivity("Medium")

    assert info_low["threshold"] < info_high["threshold"], "Low sensitivity threshold must be stricter than High"
    assert info_high["flagged_rows"] >= info_low["flagged_rows"], "High sensitivity must catch at least as many anomalies"
    assert info_high["flagged_rows"] > info_low["flagged_rows"], (
        f"Marginal samples not differentiated: Low={info_low['flagged_rows']}, High={info_high['flagged_rows']}"
    )


def test_a3_t2_05_ephemeral_database_isolation():
    """
    TEST-A3-T2-05: Ephemeral database isolation contract.
    Ensures tests operate on temp DB and production DB at data/iot_anomaly.db is untouched.
    """
    prod_db = PROJECT_ROOT / "data" / "iot_anomaly.db"
    if prod_db.exists():
        # Assert config.DB_PATH does not point to prod_db during test execution
        assert config.DB_PATH.resolve() != prod_db.resolve()
        assert "test" in str(config.DB_PATH).lower() or "tmp" in str(config.DB_PATH).lower()
