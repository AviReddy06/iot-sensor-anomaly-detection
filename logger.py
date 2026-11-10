"""
logger.py - Continuous serial logger for ESP32 + DHT11 temperature & humidity.

Usage:
    python logger.py [--port COM19] [--baud 115200] [--output data/raw/live_log.csv] [--alert] [--ntfy-topic my-topic]
"""

from __future__ import annotations

import argparse
from collections import deque
from datetime import datetime
import json
from pathlib import Path
import sys

from config import config
from collect.serial_utils import detect_esp32_port, open_serial_port, parse_sensor_line


def _load_live_detector():
    """Load trained artifacts and thresholds for optional headless --alert mode."""
    import joblib
    from features.feature_engine import MODEL_FEATURE_COLS

    iso = joblib.load(config.model_dir / "iforest.joblib")
    scaler = joblib.load(config.model_dir / "scaler.joblib")
    with open(config.model_dir / "thresholds.json", "r", encoding="utf-8") as f:
        thresholds = json.load(f)
    feature_cols = thresholds.get("feature_cols", MODEL_FEATURE_COLS)
    return iso, scaler, thresholds, feature_cols


def run_logger(
    port: str,
    baud: int,
    output_file: Path,
    enable_alerts: bool = False,
    ntfy_topic: str | None = None,
    zone: str | None = None,
) -> None:
    """Append validated ESP32 readings with CSV headers into output_file (and optionally broadcast alerts)."""
    if port.lower() == "auto":
        port = detect_esp32_port(config.serial_port)

    alert_mgr = None
    detector = None
    buffer = deque(maxlen=int(config.get("dashboard.buffer_maxlen", 500)))
    if enable_alerts:
        import pandas as pd
        from alerts.notifier import AlertManager, load_alert_settings
        from features.feature_engine import apply_gated_persistence, build_features, compute_adaptive_ewma_z

        settings = load_alert_settings(
            override_topic=ntfy_topic,
            override_zone=zone,
            override_enabled=True,
        )
        alert_mgr = AlertManager(settings)
        iso, scaler, thresholds, feature_cols = _load_live_detector()
        detector = (pd, iso, scaler, thresholds, feature_cols, build_features, apply_gated_persistence, compute_adaptive_ewma_z)
        print(f"Live employee alerts ACTIVE | zone='{settings.building_zone}' | channels={settings.active_channels() or ['local_log']}")

    output_file.parent.mkdir(parents=True, exist_ok=True)
    write_header = not output_file.exists() or output_file.stat().st_size == 0

    try:
        ser = open_serial_port(port, baudrate=baud, timeout=config.serial_timeout)
        print(f"Connected to {port} at {baud} baud")
        print(f"Logging to {output_file}")
        print("Press Ctrl+C to stop\n")
    except Exception as exc:
        print(f"ERROR: Could not open serial port {port}: {exc}")
        print("\nChecklist:")
        print("  1. ESP32 connected via USB")
        print("  2. Correct COM port (check Device Manager)")
        print("  3. Arduino Serial Monitor CLOSED")
        sys.exit(1)

    last_ts: str | None = None
    with output_file.open("a", newline="", encoding="utf-8") as f:
        if write_header:
            f.write("timestamp,temperature,humidity\n")
            f.flush()

        try:
            while True:
                line_bytes = ser.readline()
                if not line_bytes:
                    continue

                raw_line = line_bytes.decode("utf-8", errors="ignore")
                parsed = parse_sensor_line(raw_line)
                if parsed is None:
                    continue

                temperature, humidity = parsed
                timestamp = datetime.now().isoformat(timespec="seconds")
                if timestamp == last_ts:
                    continue
                last_ts = timestamp

                row = f"{timestamp},{temperature:.2f},{humidity:.2f}\n"
                f.write(row)
                f.flush()
                print(f"Saved: {row.strip()}")

                if alert_mgr is not None and detector is not None:
                    pd, iso, scaler, thresholds, feature_cols, build_features, apply_gated_persistence, compute_adaptive_ewma_z = detector
                    buffer.append({"timestamp": timestamp, "temperature": temperature, "humidity": humidity})
                    if len(buffer) >= 2:
                        feat_df = build_features(
                            pd.DataFrame(list(buffer)),
                            gap_threshold=thresholds.get("GAP_THRESHOLD", config.gap_threshold_sec),
                            roll_min=thresholds.get("ROLL_MIN", config.roll_min),
                            short_window_sec=thresholds.get("short_window_sec", config.short_window_sec),
                            long_window_sec=thresholds.get("long_window_sec", config.long_window_sec),
                            ewma_halflife_sec=thresholds.get("ewma_halflife_sec", config.ewma_halflife_sec),
                            ewma_macro_gap_sec=thresholds.get("ewma_macro_gap_sec", config.ewma_macro_gap_sec),
                        )
                        if len(feat_df) > 0:
                            scores = iso.decision_function(scaler.transform(feat_df[feature_cols]))
                            if_flag = apply_gated_persistence(
                                scores < float(thresholds["iforest_threshold"]),
                                feat_df["session_id"].to_numpy(),
                                features_df=feat_df,
                            )
                            ez = compute_adaptive_ewma_z(
                                feat_df,
                                float(thresholds.get("ewma_temp_std", 0.65)),
                                float(thresholds.get("ewma_hum_std", 3.0)),
                            )
                            ez_flag = ez > float(thresholds.get("ewma_zscore_threshold", 3.5))
                            feat_df["ewma_z_score"] = ez
                            feat_df["iforest_anomaly"] = if_flag
                            feat_df["ewma_z_anomaly"] = ez_flag
                            feat_df["hybrid_anomaly"] = if_flag | ez_flag
                            dispatched = alert_mgr.process_latest(feat_df, live_mode=True)
                            if dispatched is not None:
                                print(f"  [NOTIFY] {dispatched.title} -> {dispatched.summary}")
        except KeyboardInterrupt:
            print("\nStopped by user (Ctrl+C)")
        finally:
            ser.close()
            print("Serial port closed")


def main() -> None:
    parser = argparse.ArgumentParser(description="Continuous ESP32 + DHT11 CSV logger with optional live alerts.")
    parser.add_argument("--port", default="auto", help="COM port or 'auto'")
    parser.add_argument("--baud", type=int, default=config.baudrate, help="Serial baudrate")
    parser.add_argument(
        "--output",
        type=Path,
        default=config.raw_dir / "live_session_log.csv",
        help="Destination CSV path (default: data/raw/live_session_log.csv)",
    )
    parser.add_argument("--alert", action="store_true", help="Enable headless anomaly alerting while logging")
    parser.add_argument("--ntfy-topic", default=None, help="Optional ntfy.sh topic override for push alerts")
    parser.add_argument("--zone", default=None, help="Optional building/room zone label override")
    args = parser.parse_args()
    run_logger(
        args.port,
        args.baud,
        args.output,
        enable_alerts=args.alert,
        ntfy_topic=args.ntfy_topic,
        zone=args.zone,
    )


if __name__ == "__main__":
    main()
