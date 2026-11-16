"""Unit tests for building-wide employee alert gating, escalation, cooldowns, and delivery."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd

from alerts.notifier import (
    AlertManager,
    AlertSettings,
    build_alert_payload,
    compute_severity,
    send_email,
    send_ntfy,
    send_webhook,
)


def _make_settings(tmp_path: Path, **overrides) -> AlertSettings:
    defaults = dict(
        enabled=True,
        building_zone="Building A - Lab 2",
        min_severity="Medium",
        cooldown_sec=180.0,
        recovery_sec=30.0,
        sustained_sec=15.0,
        send_recovery=True,
        log_file=tmp_path / "alert_history.csv",
        ntfy_enabled=True,
        ntfy_server="https://ntfy.sh",
        ntfy_topic="test-office-topic",
        webhook_enabled=False,
        webhook_url="",
        email_enabled=False,
    )
    defaults.update(overrides)
    return AlertSettings(**defaults)


def test_demo_mode_never_broadcasts_alerts(tmp_path: Path, monkeypatch):
    mock_post = MagicMock()
    monkeypatch.setattr("alerts.notifier.requests.post", mock_post)

    mgr = AlertManager(_make_settings(tmp_path))
    row = {
        "timestamp": "2026-11-10T18:00:00",
        "temperature": 38.0,
        "humidity": 90.0,
        "temp_ewma_residual": 10.0,
        "hum_ewma_residual": 30.0,
        "ewma_z_score": 12.0,
        "hybrid_anomaly": True,
    }
    res = mgr.evaluate_latest_row(row, live_mode=False, sync=True)
    assert res is None
    assert mock_post.call_count == 0


def test_low_severity_filtered_until_sustained_escalation(tmp_path: Path, monkeypatch):
    mock_post = MagicMock()
    mock_post.return_value = MagicMock(status_code=200, text="ok")
    monkeypatch.setattr("alerts.notifier.requests.post", mock_post)

    mgr = AlertManager(_make_settings(tmp_path, min_severity="Medium", sustained_sec=15.0))
    t0 = datetime(2026, 11, 10, 18, 0, 0)

    # Initial Low jitter (< 3.0 sigma) -> suppressed
    r1 = mgr.evaluate_latest_row(
        {
            "timestamp": t0,
            "temperature": 26.2,
            "humidity": 59.0,
            "temp_ewma_residual": 0.4,
            "hum_ewma_residual": 1.0,
            "ewma_z_score": 1.4,
            "hybrid_anomaly": True,
        },
        live_mode=True,
        sync=True,
    )
    assert r1 is None
    assert mock_post.call_count == 0

    # Still Low at +6s -> suppressed
    r2 = mgr.evaluate_latest_row(
        {
            "timestamp": t0 + timedelta(seconds=6),
            "temperature": 26.3,
            "humidity": 59.5,
            "temp_ewma_residual": 0.5,
            "hum_ewma_residual": 1.2,
            "ewma_z_score": 1.6,
            "hybrid_anomaly": True,
        },
        live_mode=True,
        sync=True,
    )
    assert r2 is None

    # Continuous anomaly crosses 15s -> escalates to Medium and fires once
    r3 = mgr.evaluate_latest_row(
        {
            "timestamp": t0 + timedelta(seconds=16),
            "temperature": 26.4,
            "humidity": 60.0,
            "temp_ewma_residual": 0.6,
            "hum_ewma_residual": 1.5,
            "ewma_z_score": 1.8,
            "hybrid_anomaly": True,
        },
        live_mode=True,
        sync=True,
    )
    assert r3 is not None
    assert r3.event_type == "ALERT"
    assert r3.severity == "Medium"
    assert mock_post.call_count == 1


def test_cooldown_reminder_and_recovery_hysteresis(tmp_path: Path, monkeypatch):
    mock_post = MagicMock()
    mock_post.return_value = MagicMock(status_code=200, text="ok")
    monkeypatch.setattr("alerts.notifier.requests.post", mock_post)

    mgr = AlertManager(_make_settings(tmp_path, cooldown_sec=180.0, recovery_sec=30.0))
    t0 = datetime(2026, 11, 10, 18, 10, 0)

    def make_row(sec: int, z: float, anom: bool):
        return {
            "timestamp": t0 + timedelta(seconds=sec),
            "temperature": 33.5 if anom else 26.0,
            "humidity": 50.0,
            "temp_ewma_residual": 5.5 if anom else 0.1,
            "hum_ewma_residual": -2.0,
            "ewma_z_score": z,
            "hybrid_anomaly": anom,
        }

    # Start of High event -> 1 ALERT
    assert mgr.evaluate_latest_row(make_row(0, 6.2, True), live_mode=True, sync=True).event_type == "ALERT"
    # Duplicate timestamp poll ignored
    assert mgr.evaluate_latest_row(make_row(0, 6.2, True), live_mode=True, sync=True) is None
    # Inside cooldown window -> silent
    assert mgr.evaluate_latest_row(make_row(60, 6.5, True), live_mode=True, sync=True) is None
    assert mgr.evaluate_latest_row(make_row(150, 6.1, True), live_mode=True, sync=True) is None
    # Past 180s cooldown -> 1 REMINDER
    rem = mgr.evaluate_latest_row(make_row(185, 6.0, True), live_mode=True, sync=True)
    assert rem is not None and rem.event_type == "REMINDER"

    # Brief normal dip for 10s (< recovery_sec=30s) then back to anomaly -> no recovery spam
    assert mgr.evaluate_latest_row(make_row(190, 0.4, False), live_mode=True, sync=True) is None
    assert mgr.evaluate_latest_row(make_row(200, 0.4, False), live_mode=True, sync=True) is None
    assert mgr.evaluate_latest_row(make_row(205, 5.2, True), live_mode=True, sync=True) is None

    # Clean recovery sustained >= 30s -> 1 RESOLVED notice
    assert mgr.evaluate_latest_row(make_row(210, 0.3, False), live_mode=True, sync=True) is None
    assert mgr.evaluate_latest_row(make_row(225, 0.2, False), live_mode=True, sync=True) is None
    rec = mgr.evaluate_latest_row(make_row(242, 0.1, False), live_mode=True, sync=True)
    assert rec is not None and rec.event_type == "RESOLVED"
    assert mock_post.call_count == 3  # ALERT + REMINDER + RESOLVED

    # Audit CSV written cleanly
    log_df = pd.read_csv(tmp_path / "alert_history.csv")
    assert list(log_df["event_type"]) == ["ALERT", "REMINDER", "RESOLVED"]


def test_comfort_guardrails_catch_slow_hvac_failure(tmp_path: Path, monkeypatch):
    mock_post = MagicMock()
    mock_post.return_value = MagicMock(status_code=200, text="ok")
    monkeypatch.setattr("alerts.notifier.requests.post", mock_post)

    mgr = AlertManager(_make_settings(tmp_path, comfort_enabled=True, comfort_temp_max=31.0))
    t0 = datetime(2026, 11, 10, 18, 20, 0)

    # Model sees hybrid_anomaly=False (slow drift), 1st hot row starts streak without firing yet
    r1 = mgr.evaluate_latest_row(
        {
            "timestamp": t0,
            "temperature": 31.8,
            "humidity": 55.0,
            "temp_ewma_residual": 0.4,
            "hum_ewma_residual": 0.2,
            "ewma_z_score": 0.6,
            "hybrid_anomaly": False,
        },
        live_mode=True,
        sync=True,
    )
    assert r1 is None

    # 2nd consecutive hot row confirms comfort breach -> High alert
    r2 = mgr.evaluate_latest_row(
        {
            "timestamp": t0 + timedelta(seconds=2),
            "temperature": 32.0,
            "humidity": 55.0,
            "temp_ewma_residual": 0.5,
            "hum_ewma_residual": 0.2,
            "ewma_z_score": 0.7,
            "hybrid_anomaly": False,
        },
        live_mode=True,
        sync=True,
    )
    assert r2 is not None
    assert r2.severity == "High"
    assert "above comfort max" in r2.summary


def test_channel_senders_format_and_smtp_mocked(tmp_path: Path, monkeypatch):
    post_calls = []

    def fake_post(url, data=None, json=None, headers=None, timeout=8.0):
        post_calls.append({"url": url, "data": data, "json": json, "headers": headers})
        return MagicMock(status_code=200, text="ok")

    monkeypatch.setattr("alerts.notifier.requests.post", fake_post)

    smtp_instance = MagicMock()
    smtp_ctx = MagicMock()
    smtp_ctx.__enter__.return_value = smtp_instance
    smtp_ctx.__exit__.return_value = False
    monkeypatch.setattr("alerts.notifier.smtplib.SMTP", MagicMock(return_value=smtp_ctx))

    cfg = _make_settings(
        tmp_path,
        webhook_enabled=True,
        webhook_url="https://discord.com/api/webhooks/123/abc",
        email_enabled=True,
        email_from="monitor@example.com",
        email_password="app-password",
        email_to=["staff@example.com"],
    )
    payload = build_alert_payload(
        "ALERT",
        "High",
        {
            "timestamp": "2026-11-10T18:30:00",
            "temperature": 34.2,
            "humidity": 82.0,
            "temp_ewma_residual": 6.1,
            "hum_ewma_residual": 21.0,
            "ewma_z_score": 7.4,
        },
        cfg,
    )

    ntfy_res = send_ntfy(payload, cfg.ntfy_server, cfg.ntfy_topic)
    hook_res = send_webhook(payload, cfg.webhook_url)
    mail_res = send_email(payload, cfg)

    assert ntfy_res.ok and hook_res.ok and mail_res.ok
    assert post_calls[0]["headers"]["Title"].isascii()
    assert "content" in post_calls[1]["json"]
    smtp_instance.starttls.assert_called_once()
    smtp_instance.login.assert_called_once_with("monitor@example.com", "app-password")
    smtp_instance.send_message.assert_called_once()
    assert compute_severity(5.1) == "High"
    assert compute_severity(3.2) == "Medium"
    assert compute_severity(1.2) == "Low"


def test_user_app_test_alert_button_safe_no_remote_crash(project_root: Path, tmp_path: Path, monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.delenv("NTFY_TOPIC", raising=False)
    monkeypatch.delenv("ALERT_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("ALERT_EMAIL_FROM", raising=False)
    monkeypatch.delenv("ALERT_EMAIL_TO", raising=False)

    at = AppTest.from_file(str(project_root / "dashboard" / "user_app.py"), default_timeout=25).run()
    assert not at.exception
    mgr = at.session_state["alert_manager"]
    mgr.settings.log_file = tmp_path / "ui_alert_history.csv"
    mgr.settings.ntfy_topic = ""
    mgr.settings.webhook_enabled = False
    mgr.settings.email_enabled = False

    # Click "📢 Send Test Alert" in sidebar
    test_btn = [b for b in at.sidebar.button if "Send Test Alert" in b.label][0]
    test_btn.click().run()
    assert not at.exception
    assert not at.error
    assert (tmp_path / "ui_alert_history.csv").exists()

