"""
tests/test_webapp_backend.py
Comprehensive automated test suite for Phase 4:
Serial parser, detector safety assert, client-safe response scrubbing,
admin authentication, rate limiting, and event detection.
"""

from __future__ import annotations
import json
import os
import pytest
from fastapi.testclient import TestClient
import pandas as pd
from backend.app import app
from backend.services.detector_service import DetectorService, detector_service
from backend.services.events_service import EventsService
from backend.services.serial_parser import parse_serial_line


@pytest.fixture
def client():
    # Step 1: Create fresh TestClient instance
    return TestClient(app)


def test_serial_parser_strictness():
    # Step 1: Verify correct extraction of temperature from parts[0] and humidity from parts[1]
    res = parse_serial_line("26.4,58.2\r\n")
    assert res is not None
    temp, hum = res
    assert temp == 26.4
    assert hum == 58.2

    # Step 2: Verify headers and diagnostics are skipped
    assert parse_serial_line("temperature,humidity\n") is None
    assert parse_serial_line("DHT11 sensor ready\n") is None
    assert parse_serial_line("ESP32 booting...\n") is None

    # Step 3: Verify malformed and partial lines are skipped
    assert parse_serial_line("25.0\n") is None
    assert parse_serial_line("invalid,data\n") is None
    assert parse_serial_line("") is None

    # Step 4: Verify NaNs and infinites are skipped
    assert parse_serial_line("NaN,55.0\n") is None
    assert parse_serial_line("24.0,nan\n") is None
    assert parse_serial_line("inf,60.0\n") is None


def test_detector_refuses_mismatched_feature_list(tmp_path):
    # Step 1: Create a mock models directory with mismatched feature list
    mock_thresh = tmp_path / "thresholds.json"
    mock_scaler = tmp_path / "scaler.joblib"
    mock_iforest = tmp_path / "iforest.joblib"

    # Copy real joblib files
    import shutil
    shutil.copy("models/scaler.joblib", mock_scaler)
    shutil.copy("models/iforest.joblib", mock_iforest)

    # Write mismatched feature list
    with open(mock_thresh, "w") as f:
        json.dump({"feature_cols": ["only_one_feature"]}, f)

    # Step 2: Assert detector refuses to start
    with pytest.raises(RuntimeError) as exc_info:
        DetectorService(models_dir=tmp_path)
    assert "Feature list mismatch" in str(exc_info.value)
    assert "Refusing to start" in str(exc_info.value)


def test_client_routes_strictly_client_safe(client):
    # Step 1: Query all public client routes
    routes = ["/api/client/status", "/api/client/readings", "/api/client/events"]
    forbidden = [
        "isolation", "forest", "score", "threshold", "z-score",
        "precision", "recall", "f1", "confusion", "ewma", "model"
    ]

    for r in routes:
        resp = client.get(r)
        assert resp.status_code == 200
        content = resp.text.lower()
        # Step 2: Assert none of the forbidden terms appear anywhere in payload
        for word in forbidden:
            assert word not in content, f"Forbidden term '{word}' found in client route {r}: {content}"


def test_auth_and_rate_limiting(monkeypatch, client):
    # Step 1: Test 503 when ADMIN_PASSWORD is unset
    import backend.config as bcfg
    import backend.auth as bauth
    monkeypatch.setattr(bcfg, "ADMIN_PASSWORD", None)

    resp_503 = client.get("/api/admin/model/details")
    assert resp_503.status_code == 503
    assert "ADMIN_PASSWORD environment variable is not set" in resp_503.json()["detail"]

    # Step 2: Configure valid ADMIN_PASSWORD
    test_pwd = "safe_test_admin_pass"
    monkeypatch.setattr(bcfg, "ADMIN_PASSWORD", test_pwd)

    # Step 3: Test 401 without token
    resp_no_token = client.get("/api/admin/model/details")
    assert resp_no_token.status_code == 401

    # Step 4: Test 401 with wrong password
    resp_wrong = client.post("/api/auth/login", json={"password": "wrong_password"})
    assert resp_wrong.status_code == 401

    # Step 5: Test successful login with correct password
    resp_login = client.post("/api/auth/login", json={"password": test_pwd})
    assert resp_login.status_code == 200
    token = resp_login.json()["token"]
    assert token is not None

    # Step 6: Access admin route with token
    resp_admin = client.get("/api/admin/model/details", headers={"Authorization": f"Bearer {token}"})
    assert resp_admin.status_code == 200

    # Step 7: Rate limiting - 5 failed attempts allowed, 6th rejected with 429
    bauth._LOGIN_ATTEMPTS.clear()
    for _ in range(5):
        r = client.post("/api/auth/login", json={"password": "bad"})
        assert r.status_code == 401
    r_sixth = client.post("/api/auth/login", json={"password": "bad"})
    assert r_sixth.status_code == 429


def test_events_service_on_test_data():
    # Step 1: Load test data with labels
    df_raw = pd.read_csv("data/processed/test_data_with_labels.csv")
    detector_service.set_sensitivity("Medium")
    df_feat, info = detector_service.evaluate_dataframe(df_raw)

    # Step 2: Instantiate events service
    ev_svc = EventsService(normal_temp_mean=25.67, normal_hum_mean=61.42)
    closed_events = []

    for _, row in df_feat.iterrows():
        ts = str(row["timestamp"])
        t = float(row["temperature"])
        h = float(row["humidity"])
        flag = bool(row["anomaly_flag"])
        peak_z = float(abs(t - 25.67) / 0.83)
        ev = ev_svc.process_sample(ts, t, h, flag, peak_z)
        if ev:
            closed_events.append(ev)

    # Finalize remaining event
    final_ev = ev_svc._finalize_event()
    if final_ev:
        closed_events.append(final_ev)

    # Step 3: Verify the 10 true rows form one event beginning 2026-10-27 22:03:29 with High severity
    assert len(closed_events) >= 1
    target_event = [e for e in closed_events if "22:03:29" in e["start_time"]][0]
    assert target_event is not None
    assert target_event["severity"] == "High"
    assert "unusual" in target_event["sentence"].lower()

    # Step 4: Count false alarm rows
    false_alarm_rows = int(((df_feat["label"] == 0) & df_feat["anomaly_flag"]).sum())
    print(f"Verified Event: {target_event['sentence']} | False alarm rows: {false_alarm_rows}")
    assert false_alarm_rows == 3


def test_websocket_admin_rejects_missing_token(client):
    # Step 1: Connect to /ws/admin without token
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/admin") as ws:
            ws.receive_text()
