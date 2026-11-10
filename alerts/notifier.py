"""
alerts/notifier.py
Non-blocking building-wide employee alert system with state-transition gating,
severity routing, cooldown suppression, recovery notifications, and audit logging.

Supported channels (configured cleanly via config.yaml + local .env):
  - ntfy.sh mobile/browser push notifications (zero-account / zero-key setup)
  - Slack / Discord / Microsoft Teams incoming webhooks
  - Email broadcasts via SMTP (standard library smtplib)
"""

from __future__ import annotations

from collections import deque
import csv
from dataclasses import dataclass, field
from datetime import datetime
from email.message import EmailMessage
import os
from pathlib import Path
import queue
import smtplib
import sys
import threading
from typing import Any, Deque, Dict, List, Optional

import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import config, load_dotenv

SEVERITY_RANK: Dict[str, int] = {"Low": 1, "Medium": 2, "High": 3}


def _to_naive_datetime(value: Any) -> datetime:
    """Convert timestamp-like values into naive Python datetime consistently."""
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return datetime.now().replace(microsecond=0)
    dt = ts.to_pydatetime()
    return dt.replace(tzinfo=None)


@dataclass
class AlertSettings:
    """Runtime alert configuration loaded from config.yaml + environment variables."""

    enabled: bool = False
    building_zone: str = "Building A - Floor 1"
    min_severity: str = "Medium"
    cooldown_sec: float = 180.0
    recovery_sec: float = 30.0
    sustained_sec: float = 15.0
    send_recovery: bool = True
    log_file: Path = field(default_factory=lambda: PROJECT_ROOT / "logs" / "alert_history.csv")

    ntfy_enabled: bool = True
    ntfy_server: str = "https://ntfy.sh"
    ntfy_topic: str = ""

    webhook_enabled: bool = False
    webhook_url: str = ""

    email_enabled: bool = False
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    email_from: str = ""
    email_password: str = ""
    email_to: List[str] = field(default_factory=list)

    comfort_enabled: bool = False
    comfort_temp_min: float = 18.0
    comfort_temp_max: float = 31.0
    comfort_hum_min: float = 25.0
    comfort_hum_max: float = 75.0

    def active_channels(self) -> List[str]:
        """Return names of currently configured and enabled broadcast channels."""
        channels: List[str] = []
        if self.ntfy_enabled and self.ntfy_topic.strip():
            channels.append("ntfy")
        if self.webhook_enabled and self.webhook_url.strip():
            channels.append("webhook")
        if self.email_enabled and self.email_from.strip() and self.email_to:
            channels.append("email")
        return channels


def load_alert_settings(
    override_topic: Optional[str] = None,
    override_zone: Optional[str] = None,
    override_enabled: Optional[bool] = None,
) -> AlertSettings:
    """Build AlertSettings combining config.yaml and local .env / environment variables."""
    load_dotenv()

    ntfy_topic = (
        override_topic
        if override_topic is not None
        else (os.environ.get("NTFY_TOPIC") or str(config.get("alerts.ntfy.topic", "")))
    ).strip()
    ntfy_server = (os.environ.get("NTFY_SERVER") or str(config.get("alerts.ntfy.server", "https://ntfy.sh"))).strip()
    webhook_url = (os.environ.get("ALERT_WEBHOOK_URL") or "").strip()

    email_from = (os.environ.get("ALERT_EMAIL_FROM") or "").strip()
    email_password = (os.environ.get("ALERT_EMAIL_PASSWORD") or "").strip()
    raw_recipients = (os.environ.get("ALERT_EMAIL_TO") or "").strip()
    email_to = [addr.strip() for addr in raw_recipients.split(",") if addr.strip()]
    smtp_host = (os.environ.get("ALERT_SMTP_HOST") or str(config.get("alerts.email.smtp_host", "smtp.gmail.com"))).strip()
    smtp_port_raw = os.environ.get("ALERT_SMTP_PORT") or config.get("alerts.email.smtp_port", 587)
    try:
        smtp_port = int(smtp_port_raw)
    except (TypeError, ValueError):
        smtp_port = 587

    min_sev = str(config.get("alerts.min_severity", "Medium")).strip().title()
    if min_sev not in SEVERITY_RANK:
        min_sev = "Medium"

    log_rel = str(config.get("alerts.log_file", "logs/alert_history.csv"))
    log_path = Path(log_rel) if Path(log_rel).is_absolute() else (PROJECT_ROOT / log_rel)

    cfg_enabled = bool(config.get("alerts.enabled", False))
    enabled = cfg_enabled if override_enabled is None else bool(override_enabled)

    return AlertSettings(
        enabled=enabled,
        building_zone=(override_zone if override_zone is not None else str(config.get("alerts.building_zone", "Building A - Floor 1"))).strip(),
        min_severity=min_sev,
        cooldown_sec=float(config.get("alerts.cooldown_sec", 180)),
        recovery_sec=float(config.get("alerts.recovery_sec", 30)),
        sustained_sec=float(config.get("alerts.sustained_sec", 15)),
        send_recovery=bool(config.get("alerts.send_recovery", True)),
        log_file=log_path,
        ntfy_enabled=bool(config.get("alerts.ntfy.enabled", True)),
        ntfy_server=ntfy_server,
        ntfy_topic=ntfy_topic,
        webhook_enabled=bool(config.get("alerts.webhook.enabled", False)) or bool(webhook_url),
        webhook_url=webhook_url,
        email_enabled=bool(config.get("alerts.email.enabled", False)) or (bool(email_from) and bool(email_to)),
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        email_from=email_from,
        email_password=email_password,
        email_to=email_to,
        comfort_enabled=bool(config.get("alerts.comfort_guardrails.enabled", False)),
        comfort_temp_min=float(config.get("alerts.comfort_guardrails.temp_min", 18.0)),
        comfort_temp_max=float(config.get("alerts.comfort_guardrails.temp_max", 31.0)),
        comfort_hum_min=float(config.get("alerts.comfort_guardrails.hum_min", 25.0)),
        comfort_hum_max=float(config.get("alerts.comfort_guardrails.hum_max", 75.0)),
    )


@dataclass
class AlertPayload:
    """Rendered notification message ready for multi-channel dispatch."""

    event_type: str  # "ALERT", "REMINDER", "RESOLVED", "TEST"
    severity: str    # "Low", "Medium", "High", "Info"
    title: str
    body: str
    summary: str
    timestamp: datetime
    zone: str
    temperature: float
    humidity: float
    ewma_z_score: float
    tags: str = "warning"
    priority: str = "high"


@dataclass
class ChannelResult:
    """Delivery result for one channel attempt."""

    channel: str
    ok: bool
    detail: str


@dataclass
class AlertState:
    """Tracks episode hysteresis, cooldowns, recovery windows, and last dispatch state."""

    episode_active: bool = False
    episode_start_ts: Optional[datetime] = None
    last_alert_ts: Optional[datetime] = None
    last_seen_ts: Optional[datetime] = None
    normal_since_ts: Optional[datetime] = None
    comfort_breach_streak: int = 0
    alert_sent_for_episode: bool = False
    highest_severity_sent: Optional[str] = None
    last_status_message: str = "Alert monitor ready"


def compute_severity(
    ewma_z_score: float,
    elapsed_sec: float = 0.0,
    sustained_sec: float = 15.0,
    comfort_breach: bool = False,
) -> str:
    """Classify anomaly severity consistently with dashboard severity rules."""
    z = abs(float(ewma_z_score))
    if comfort_breach or z >= 5.0:
        return "High"
    if z >= 3.0 or elapsed_sec >= sustained_sec:
        return "Medium"
    return "Low"


def _describe_condition(row: Dict[str, Any], comfort_breach_reasons: List[str]) -> tuple[str, str]:
    """Return plain-English `(condition_summary, suggested_action)` for employees."""
    t_res = float(row.get("temp_ewma_residual", 0.0))
    h_res = float(row.get("hum_ewma_residual", 0.0))
    notes: List[str] = []
    actions: List[str] = []

    if comfort_breach_reasons:
        notes.extend(comfort_breach_reasons)
        actions.append("Inspect HVAC / AC thermostat and room ventilation immediately")

    if abs(t_res) >= 0.8:
        direction = "rose" if t_res > 0 else "dropped"
        notes.append(f"Temperature {direction} {abs(t_res):.1f} C vs room baseline")
        if t_res > 0:
            actions.append("Check for heat sources, blocked AC airflow, or equipment overheating")
        else:
            actions.append("Check open doors/windows or direct cold AC draft")

    if abs(h_res) >= 3.0:
        direction = "spiked" if h_res > 0 else "dropped"
        notes.append(f"Humidity {direction} {abs(h_res):.1f}% RH vs room baseline")
        if h_res > 0:
            actions.append("Check for steam/water leak, crowding, or ventilation stall")
        else:
            actions.append("Check dry heat / dehumidifier exhaust")

    if not notes:
        notes.append("Rapid short-term sensor chatter or abrupt signal jump detected")
        actions.append("Check DHT11 GPIO 4 wiring and room conditions")

    # Preserve order while deduplicating action suggestions
    unique_actions = list(dict.fromkeys(actions))
    return "; ".join(notes), " | ".join(unique_actions)


def build_alert_payload(
    event_type: str,
    severity: str,
    row: Dict[str, Any],
    settings: AlertSettings,
    comfort_breach_reasons: Optional[List[str]] = None,
) -> AlertPayload:
    """Create an ASCII-safe header + clear employee message payload."""
    ts = _to_naive_datetime(row.get("timestamp"))
    temp = float(row.get("temperature", 0.0))
    hum = float(row.get("humidity", 0.0))
    ewma_z = float(row.get("ewma_z_score", 0.0))
    zone = settings.building_zone or "Building Zone"
    time_str = ts.strftime("%Y-%m-%d %H:%M:%S")

    if event_type == "RESOLVED":
        title = f"[RESOLVED] {zone}: Climate Returned to Normal"
        summary = f"Recovered to {temp:.1f} C / {hum:.1f}% RH"
        body = (
            f"All Clear in {zone}\n"
            f"Sensor telemetry returned within normal room baseline.\n"
            f"- Temperature: {temp:.1f} C\n"
            f"- Humidity: {hum:.1f}% RH\n"
            f"- Time: {time_str}"
        )
        return AlertPayload(
            event_type=event_type,
            severity="Info",
            title=title,
            body=body,
            summary=summary,
            timestamp=ts,
            zone=zone,
            temperature=temp,
            humidity=hum,
            ewma_z_score=ewma_z,
            tags="white_check_mark",
            priority="default",
        )

    if event_type == "TEST":
        title = f"[TEST ALERT] {zone}: Employee Alert System Ready"
        summary = "Manual test alert verified"
        body = (
            f"Test notification from IoT Climate Monitor ({zone}).\n"
            f"- Latest Reading: {temp:.1f} C | {hum:.1f}% RH\n"
            f"- Active Channels: {', '.join(settings.active_channels()) or 'local log only'}\n"
            f"- Time: {time_str}\n"
            f"No action needed — this confirms employee alerts are reaching you."
        )
        return AlertPayload(
            event_type=event_type,
            severity="Info",
            title=title,
            body=body,
            summary=summary,
            timestamp=ts,
            zone=zone,
            temperature=temp,
            humidity=hum,
            ewma_z_score=ewma_z,
            tags="bell",
            priority="default",
        )

    prefix = "STILL ACTIVE" if event_type == "REMINDER" else f"{severity.upper()} ALERT"
    cond_summary, action_text = _describe_condition(row, comfort_breach_reasons or [])
    title = f"[{prefix}] {zone}: Unusual Room Climate"
    body = (
        f"Anomaly detected in {zone} at {time_str}\n"
        f"- Severity: {severity}\n"
        f"- Temperature: {temp:.1f} C\n"
        f"- Humidity: {hum:.1f}% RH\n"
        f"- Condition: {cond_summary}\n"
        f"- Suggested Action: {action_text}"
    )
    priority = "urgent" if severity == "High" else "high"
    tags = "rotating_light,thermometer" if severity == "High" else "warning,thermometer"
    return AlertPayload(
        event_type=event_type,
        severity=severity,
        title=title,
        body=body,
        summary=cond_summary,
        timestamp=ts,
        zone=zone,
        temperature=temp,
        humidity=hum,
        ewma_z_score=ewma_z,
        tags=tags,
        priority=priority,
    )


def send_ntfy(payload: AlertPayload, server: str, topic: str, timeout: float = 8.0) -> ChannelResult:
    """Send push notification via ntfy HTTP POST using ASCII headers."""
    clean_topic = topic.strip().strip("/")
    if not clean_topic:
        return ChannelResult("ntfy", False, "No ntfy topic configured")
    url = f"{server.rstrip('/')}/{clean_topic}"
    safe_title = payload.title.encode("ascii", errors="ignore").decode("ascii")
    headers = {
        "Title": safe_title,
        "Priority": payload.priority,
        "Tags": payload.tags,
    }
    try:
        resp = requests.post(url, data=payload.body.encode("utf-8"), headers=headers, timeout=timeout)
        if 200 <= resp.status_code < 300:
            return ChannelResult("ntfy", True, f"Sent to {url}")
        return ChannelResult("ntfy", False, f"HTTP {resp.status_code}: {resp.text[:120]}")
    except Exception as exc:
        return ChannelResult("ntfy", False, str(exc))


def send_webhook(payload: AlertPayload, webhook_url: str, timeout: float = 8.0) -> ChannelResult:
    """Send alert payload to Slack, Discord, or Microsoft Teams webhook."""
    url = webhook_url.strip()
    if not url:
        return ChannelResult("webhook", False, "No webhook URL configured")
    lower = url.lower()
    if "discord.com/api/webhooks" in lower or "discordapp.com/api/webhooks" in lower:
        json_body: Dict[str, Any] = {"content": f"**{payload.title}**\n{payload.body}"}
    else:
        json_body = {"text": f"*{payload.title}*\n{payload.body}"}
    try:
        resp = requests.post(url, json=json_body, timeout=timeout)
        if 200 <= resp.status_code < 300:
            return ChannelResult("webhook", True, f"Webhook delivered (HTTP {resp.status_code})")
        return ChannelResult("webhook", False, f"HTTP {resp.status_code}: {resp.text[:120]}")
    except Exception as exc:
        return ChannelResult("webhook", False, str(exc))


def send_email(payload: AlertPayload, settings: AlertSettings, timeout: float = 10.0) -> ChannelResult:
    """Broadcast alert email to configured recipients using SMTP."""
    if not settings.email_from or not settings.email_to:
        return ChannelResult("email", False, "Missing ALERT_EMAIL_FROM or ALERT_EMAIL_TO")
    msg = EmailMessage()
    msg["Subject"] = payload.title
    msg["From"] = settings.email_from
    msg["To"] = ", ".join(settings.email_to)
    msg.set_content(payload.body, charset="utf-8")

    try:
        if settings.smtp_port == 465:
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=timeout) as server:
                if settings.email_password:
                    server.login(settings.email_from, settings.email_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=timeout) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                if settings.email_password:
                    server.login(settings.email_from, settings.email_password)
                server.send_message(msg)
        return ChannelResult("email", True, f"Sent to {len(settings.email_to)} recipient(s)")
    except Exception as exc:
        return ChannelResult("email", False, str(exc))


class AlertManager:
    """Thread-safe stateful alert evaluator and non-blocking dispatcher."""

    def __init__(self, settings: Optional[AlertSettings] = None) -> None:
        self.settings: AlertSettings = settings or load_alert_settings()
        self.state: AlertState = AlertState()
        self._queue: queue.Queue[AlertPayload] = queue.Queue(maxsize=50)
        self._worker: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._log_lock = threading.Lock()
        self.recent_events: Deque[Dict[str, Any]] = deque(maxlen=25)

    def update_settings(self, settings: AlertSettings) -> None:
        with self._lock:
            self.settings = settings

    def _ensure_worker(self) -> None:
        if self._worker is None or not self._worker.is_alive():
            self._worker = threading.Thread(target=self._worker_loop, daemon=True)
            self._worker.start()

    def _worker_loop(self) -> None:
        while True:
            payload = self._queue.get()
            try:
                self.deliver_sync(payload)
            finally:
                self._queue.task_done()

    def _append_log(self, payload: AlertPayload, results: List[ChannelResult]) -> None:
        log_path = self.settings.log_file
        with self._log_lock:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            write_header = not log_path.exists() or log_path.stat().st_size == 0
            channels_str = ", ".join(r.channel for r in results) if results else "local_only"
            if not results:
                status_str = "logged_local"
            elif all(r.ok for r in results):
                status_str = "delivered"
            elif any(r.ok for r in results):
                status_str = "partial"
            else:
                status_str = "failed"

            with log_path.open("a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if write_header:
                    writer.writerow([
                        "timestamp",
                        "event_type",
                        "severity",
                        "zone",
                        "temperature",
                        "humidity",
                        "ewma_z_score",
                        "summary",
                        "channels",
                        "status",
                    ])
                writer.writerow([
                    payload.timestamp.isoformat(timespec="seconds"),
                    payload.event_type,
                    payload.severity,
                    payload.zone,
                    f"{payload.temperature:.2f}",
                    f"{payload.humidity:.2f}",
                    f"{payload.ewma_z_score:.2f}",
                    payload.summary,
                    channels_str,
                    status_str,
                ])

        self.recent_events.appendleft({
            "timestamp": payload.timestamp.strftime("%H:%M:%S"),
            "event_type": payload.event_type,
            "severity": payload.severity,
            "summary": payload.summary,
            "channels": channels_str,
            "status": status_str,
        })

    def deliver_sync(self, payload: AlertPayload) -> List[ChannelResult]:
        """Synchronously send payload to all active channels and write audit log."""
        with self._lock:
            cfg = self.settings
        results: List[ChannelResult] = []
        if cfg.ntfy_enabled and cfg.ntfy_topic.strip():
            results.append(send_ntfy(payload, cfg.ntfy_server, cfg.ntfy_topic))
        if cfg.webhook_enabled and cfg.webhook_url.strip():
            results.append(send_webhook(payload, cfg.webhook_url))
        if cfg.email_enabled and cfg.email_from.strip() and cfg.email_to:
            results.append(send_email(payload, cfg))

        self._append_log(payload, results)
        if results:
            ok_names = [r.channel for r in results if r.ok]
            fail_msgs = [f"{r.channel}: {r.detail}" for r in results if not r.ok]
            msg = f"{payload.event_type} ({payload.severity})"
            if ok_names:
                msg += f" -> sent via {', '.join(ok_names)}"
            if fail_msgs:
                msg += f" | errors: {'; '.join(fail_msgs)}"
            self.state.last_status_message = msg
        else:
            self.state.last_status_message = f"{payload.event_type} logged locally (no broadcast topic/webhook set)"
        return results

    def dispatch_async(self, payload: AlertPayload) -> None:
        """Queue notification for non-blocking background delivery."""
        self._ensure_worker()
        try:
            self._queue.put_nowait(payload)
        except queue.Full:
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except queue.Empty:
                pass
            self._queue.put_nowait(payload)

    def send_test_alert(
        self,
        temperature: float = 26.0,
        humidity: float = 58.0,
    ) -> List[ChannelResult]:
        """Send an immediate synchronous test notification across configured channels."""
        payload = build_alert_payload(
            event_type="TEST",
            severity="Info",
            row={
                "timestamp": datetime.now().replace(microsecond=0),
                "temperature": temperature,
                "humidity": humidity,
                "ewma_z_score": 0.0,
            },
            settings=self.settings,
        )
        return self.deliver_sync(payload)

    def evaluate_latest_row(
        self,
        row: Dict[str, Any],
        live_mode: bool = True,
        sync: bool = False,
    ) -> Optional[AlertPayload]:
        """
        Evaluate latest scored sensor row against hysteresis/cooldown rules.
        Never broadcasts when `live_mode` is False (e.g. Demo / CSV replay).
        """
        if not live_mode or not self.settings.enabled:
            return None

        ts = _to_naive_datetime(row.get("timestamp"))
        if self.state.last_seen_ts is not None and ts <= self.state.last_seen_ts:
            return None
        self.state.last_seen_ts = ts

        temp = float(row.get("temperature", 0.0))
        hum = float(row.get("humidity", 0.0))
        ewma_z = float(row.get("ewma_z_score", 0.0))
        model_anomaly = bool(row.get("hybrid_anomaly", False))

        comfort_reasons: List[str] = []
        if self.settings.comfort_enabled:
            if temp > self.settings.comfort_temp_max:
                comfort_reasons.append(f"Temp {temp:.1f} C above comfort max {self.settings.comfort_temp_max:.1f} C")
            elif temp < self.settings.comfort_temp_min:
                comfort_reasons.append(f"Temp {temp:.1f} C below comfort min {self.settings.comfort_temp_min:.1f} C")
            if hum > self.settings.comfort_hum_max:
                comfort_reasons.append(f"Humidity {hum:.1f}% above comfort max {self.settings.comfort_hum_max:.1f}%")
            elif hum < self.settings.comfort_hum_min:
                comfort_reasons.append(f"Humidity {hum:.1f}% below comfort min {self.settings.comfort_hum_min:.1f}%")

        if comfort_reasons:
            self.state.comfort_breach_streak += 1
        else:
            self.state.comfort_breach_streak = 0
        comfort_breach = self.state.comfort_breach_streak >= 2

        is_anomalous = model_anomaly or comfort_breach
        payload: Optional[AlertPayload] = None

        if is_anomalous:
            self.state.normal_since_ts = None
            if not self.state.episode_active:
                self.state.episode_active = True
                self.state.episode_start_ts = ts
                self.state.alert_sent_for_episode = False
                self.state.highest_severity_sent = None

            elapsed = (ts - self.state.episode_start_ts).total_seconds() if self.state.episode_start_ts else 0.0
            severity = compute_severity(
                ewma_z,
                elapsed_sec=elapsed,
                sustained_sec=self.settings.sustained_sec,
                comfort_breach=comfort_breach,
            )

            min_rank = SEVERITY_RANK.get(self.settings.min_severity, 2)
            curr_rank = SEVERITY_RANK[severity]
            prev_rank = SEVERITY_RANK.get(self.state.highest_severity_sent or "", 0)

            should_send = False
            event_type = "ALERT"
            if curr_rank >= min_rank:
                if not self.state.alert_sent_for_episode:
                    should_send = True
                    event_type = "ALERT"
                elif curr_rank > prev_rank:
                    should_send = True
                    event_type = "ALERT"
                elif self.state.last_alert_ts is not None and self.settings.cooldown_sec > 0:
                    since_last = (ts - self.state.last_alert_ts).total_seconds()
                    if since_last >= self.settings.cooldown_sec:
                        should_send = True
                        event_type = "REMINDER"

            if should_send:
                payload = build_alert_payload(
                    event_type=event_type,
                    severity=severity,
                    row=row,
                    settings=self.settings,
                    comfort_breach_reasons=comfort_reasons if comfort_breach else None,
                )
                self.state.alert_sent_for_episode = True
                self.state.highest_severity_sent = severity
                self.state.last_alert_ts = ts
        else:
            if self.state.episode_active:
                if self.state.normal_since_ts is None:
                    self.state.normal_since_ts = ts
                recovered_for = (ts - self.state.normal_since_ts).total_seconds()
                if recovered_for >= self.settings.recovery_sec:
                    if self.state.alert_sent_for_episode and self.settings.send_recovery:
                        payload = build_alert_payload(
                            event_type="RESOLVED",
                            severity="Info",
                            row=row,
                            settings=self.settings,
                        )
                    self.state.episode_active = False
                    self.state.episode_start_ts = None
                    self.state.normal_since_ts = None
                    self.state.alert_sent_for_episode = False
                    self.state.highest_severity_sent = None

        if payload is not None:
            if sync:
                self.deliver_sync(payload)
            else:
                self.dispatch_async(payload)
        return payload

    def process_latest(
        self,
        feat_df: pd.DataFrame,
        live_mode: bool = True,
        sync: bool = False,
    ) -> Optional[AlertPayload]:
        """Convenience wrapper accepting a scored feature DataFrame."""
        if feat_df is None or len(feat_df) == 0:
            return None
        latest = feat_df.iloc[-1].to_dict()
        return self.evaluate_latest_row(latest, live_mode=live_mode, sync=sync)
