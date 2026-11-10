#!/usr/bin/env python3
"""
dashboard/user_app.py
Client-facing live IoT Sensor Monitor for ESP32 + DHT11 over USB Serial.
Clean single-entrypoint implementation with safe DTR/RTS serial handling,
dynamic COM port auto-detection, and unified feature/persistence scoring.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime
import json
from pathlib import Path
import queue
import sys
import threading
import time

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import serial
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from alerts.streamlit_panel import load_recent_alert_log, render_alert_sidebar
from collect.serial_utils import detect_esp32_port, list_serial_ports, open_serial_port, parse_sensor_line
from config import config
from features.feature_engine import (
    MODEL_FEATURE_COLS,
    apply_gated_persistence,
    build_features,
    compute_adaptive_ewma_z,
)

st.set_page_config(
    page_title="IoT Sensor Monitor",
    page_icon="🌡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    div[data-testid="stMetricValue"] { font-size: 1.9rem; }
    .stAlert { border-radius: 8px; }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_resource
def _load_estimators():
    iso = joblib.load(PROJECT_ROOT / "models" / "iforest.joblib")
    scaler = joblib.load(PROJECT_ROOT / "models" / "scaler.joblib")
    return iso, scaler


def load_models():
    iso, scaler = _load_estimators()
    with open(PROJECT_ROOT / "models" / "thresholds.json", "r", encoding="utf-8") as f:
        thresholds = json.load(f)
    return iso, scaler, thresholds


def serial_reader(port: str, baud: int, q_out: queue.Queue, stop_event: threading.Event) -> None:
    """Read validated lines from ESP32 serial without resetting MCU."""
    ser = None
    last_ts = None
    try:
        ser = open_serial_port(port, baudrate=baud, timeout=1.0)
        while not stop_event.is_set():
            line_bytes = ser.readline()
            if not line_bytes:
                continue
            parsed = parse_sensor_line(line_bytes.decode("utf-8", errors="ignore"))
            if parsed is None:
                continue
            temp, hum = parsed
            ts = datetime.now().isoformat(timespec="seconds")
            if ts == last_ts:
                continue
            last_ts = ts
            item = {"timestamp": ts, "temperature": temp, "humidity": hum}
            try:
                q_out.put_nowait(item)
            except queue.Full:
                try:
                    q_out.get_nowait()
                except queue.Empty:
                    pass
                q_out.put_nowait(item)
    except serial.SerialException as exc:
        q_out.put(("error", str(exc)))
    except Exception as exc:
        q_out.put(("error", str(exc)))
    finally:
        if ser is not None and ser.is_open:
            ser.close()


def init_state() -> None:
    maxlen = int(config.get("dashboard.buffer_maxlen", 300))
    if "serial_queue" not in st.session_state:
        st.session_state.serial_queue = queue.Queue(maxsize=maxlen)
    if "data_buffer" not in st.session_state:
        st.session_state.data_buffer = deque(maxlen=maxlen)
    if "serial_thread" not in st.session_state:
        st.session_state.serial_thread = None
    if "is_collecting" not in st.session_state:
        st.session_state.is_collecting = False
    if "stop_event" not in st.session_state:
        st.session_state.stop_event = None
    if "serial_error" not in st.session_state:
        st.session_state.serial_error = None


def process_queue() -> None:
    while not st.session_state.serial_queue.empty():
        item = st.session_state.serial_queue.get_nowait()
        if isinstance(item, tuple) and item[0] == "error":
            st.session_state.serial_error = item[1]
            st.session_state.is_collecting = False
        else:
            st.session_state.data_buffer.append(item)


def main() -> None:
    init_state()
    iso, scaler, thresholds = load_models()
    feature_cols = thresholds.get("feature_cols", MODEL_FEATURE_COLS)
    if_th = float(thresholds["iforest_threshold"])
    ez_th = float(thresholds.get("ewma_zscore_threshold", 3.5))
    z_th = float(thresholds["zscore_threshold"])

    st.title("🌡️ IoT Sensor Monitor")
    st.caption("Live ESP32 + DHT11 Temperature & Humidity Monitoring")

    detected = list_serial_ports()
    port_list = [dev for dev, _ in detected] or [config.serial_port]
    default_port = detect_esp32_port(config.serial_port)
    default_idx = port_list.index(default_port) if default_port in port_list else 0

    with st.sidebar:
        st.header("🔌 Connection")
        port = st.selectbox("COM Port", port_list, index=default_idx)
        baud_options = [9600, 19200, 38400, 57600, 115200]
        baud = st.selectbox("Baud Rate", baud_options, index=baud_options.index(config.baudrate) if config.baudrate in baud_options else 4)
        st.divider()

        if st.session_state.is_collecting:
            if st.button("⏹ Stop Monitoring", type="primary", width='stretch'):
                st.session_state.is_collecting = False
                if st.session_state.stop_event is not None:
                    st.session_state.stop_event.set()
                if st.session_state.serial_thread is not None:
                    st.session_state.serial_thread.join(timeout=2)
                st.rerun()
        else:
            if st.button("▶ Start Monitoring", type="primary", width='stretch'):
                st.session_state.serial_error = None
                st.session_state.is_collecting = True
                st.session_state.stop_event = threading.Event()
                st.session_state.data_buffer.clear()
                while not st.session_state.serial_queue.empty():
                    try:
                        st.session_state.serial_queue.get_nowait()
                    except queue.Empty:
                        break
                st.session_state.serial_thread = threading.Thread(
                    target=serial_reader,
                    args=(port, int(baud), st.session_state.serial_queue, st.session_state.stop_event),
                    daemon=True,
                )
                st.session_state.serial_thread.start()
                st.rerun()

        if st.button("Load Sample Snapshot", width='stretch'):
            live_csvs = sorted((PROJECT_ROOT / "data" / "raw").glob("live_*.csv"))
            sample_path = live_csvs[-1] if live_csvs else (PROJECT_ROOT / "data" / "processed" / "test_data_with_labels.csv")
            if sample_path.exists():
                sdf = pd.read_csv(sample_path).tail(60)
                st.session_state.data_buffer.clear()
                for _, row in sdf.iterrows():
                    st.session_state.data_buffer.append(
                        {"timestamp": str(row["timestamp"]), "temperature": float(row["temperature"]), "humidity": float(row["humidity"])}
                    )
                st.rerun()

        if st.button("🗑️ Clear Data", width='stretch'):
            st.session_state.data_buffer.clear()
            st.rerun()

        st.divider()
        if st.session_state.is_collecting:
            st.success(f"🟢 Streaming ({port} @ {baud})")
        else:
            st.info("⚪ Disconnected")

    latest_buf = st.session_state.data_buffer[-1] if st.session_state.data_buffer else {}
    alert_mgr = render_alert_sidebar(
        "user_app",
        default_temp=float(latest_buf.get("temperature", 26.0)),
        default_hum=float(latest_buf.get("humidity", 58.0)),
    )

    if st.session_state.serial_error:
        st.error(f"Serial connection error: {st.session_state.serial_error}")

    process_queue()

    if len(st.session_state.data_buffer) == 0:
        st.info("👈 Connect ESP32 + DHT11 via USB and click **Start Monitoring** (or **Load Sample Snapshot** to inspect recorded telemetry).")
    else:
        df = pd.DataFrame(list(st.session_state.data_buffer))
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp", kind="stable").reset_index(drop=True)
        latest = df.iloc[-1]

        feat_df = pd.DataFrame()
        if_flag = np.array([], dtype=bool)
        ez_flag = np.array([], dtype=bool)
        z_flag = np.array([], dtype=bool)
        hybrid_flag = np.array([], dtype=bool)
        latest_hybrid = False
        latest_if = False
        latest_ez = False

        if len(df) >= 2:
            feat_df = build_features(
                df,
                gap_threshold=thresholds.get("GAP_THRESHOLD", config.gap_threshold_sec),
                roll_min=thresholds.get("ROLL_MIN", config.roll_min),
                short_window_sec=thresholds.get("short_window_sec", config.short_window_sec),
                long_window_sec=thresholds.get("long_window_sec", config.long_window_sec),
                ewma_halflife_sec=thresholds.get("ewma_halflife_sec", config.ewma_halflife_sec),
                ewma_macro_gap_sec=thresholds.get("ewma_macro_gap_sec", config.ewma_macro_gap_sec),
            )
            if len(feat_df) > 0:
                X_scaled = scaler.transform(feat_df[feature_cols])
                scores = iso.decision_function(X_scaled)
                if_flag = apply_gated_persistence(scores < if_th, feat_df["session_id"].to_numpy(), features_df=feat_df)
                ez = compute_adaptive_ewma_z(feat_df, thresholds.get("ewma_temp_std", 0.65), thresholds.get("ewma_hum_std", 3.0))
                ez_flag = ez > ez_th
                z_t = np.abs((feat_df["temperature"] - thresholds["normal_temp_mean"]) / thresholds["normal_temp_std"])
                z_h = np.abs((feat_df["humidity"] - thresholds["normal_hum_mean"]) / thresholds["normal_hum_std"])
                z_flag = ((z_t > z_th) | (z_h > z_th)).to_numpy()
                hybrid_flag = if_flag | ez_flag
                ewma_z_vals = ez
                feat_df["ewma_z_score"] = ewma_z_vals
                feat_df["hybrid_anomaly"] = hybrid_flag
                latest_hybrid = bool(hybrid_flag[-1])
                latest_if = bool(if_flag[-1])
                latest_ez = bool(ez_flag[-1])
                if st.session_state.is_collecting:
                    dispatched = alert_mgr.process_latest(feat_df, live_mode=True)
                    if dispatched is not None:
                        st.toast(f"🔔 Employee Alert: {dispatched.event_type} ({dispatched.severity})")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("🌡️ Temperature", f"{latest['temperature']:.1f} °C")
        with col2:
            st.metric("💧 Humidity", f"{latest['humidity']:.1f} %")
        with col3:
            st.metric("📊 Readings", len(df))
        with col4:
            status = "🔴 ANOMALY" if latest_hybrid else "🟢 Normal"
            st.metric("Status", status)

        if st.session_state.is_collecting:
            stale_sec = (datetime.now() - latest["timestamp"].to_pydatetime()).total_seconds()
            if stale_sec > max(15.0, float(thresholds.get("GAP_THRESHOLD", config.gap_threshold_sec))):
                st.warning(f"Sensor stream stale: no valid DHT11 reading received for {stale_sec:.0f}s (check wiring / USB).")

        a1, a2 = st.columns(2)
        with a1:
            if latest_if:
                st.error("🔴 **Dynamic Disturbance Detected** (Isolation Forest)")
            else:
                st.success("🟢 No sudden dynamic disturbances")
        with a2:
            if latest_ez:
                st.error("🔴 **Drift/Excursion Detected** (Adaptive EWMA-Z)")
            else:
                st.success("🟢 Within room-adapted baseline range")

        tab1, tab2 = st.tabs(["📈 Time Series", "📊 Scatter"])
        with tab1:
            fig, axes = plt.subplots(2, 1, figsize=(10, 5), sharex=True)
            axes[0].plot(df["timestamp"], df["temperature"], "b-", alpha=0.75, linewidth=1.2, label="Temperature")
            if len(feat_df) > 0 and hybrid_flag.any():
                axes[0].scatter(feat_df.loc[hybrid_flag, "timestamp"], feat_df.loc[hybrid_flag, "temperature"], color="red", s=30, zorder=5, label="Anomaly")
            axes[0].set_ylabel("Temperature (°C)")
            axes[0].legend(loc="upper right")
            axes[0].grid(True, alpha=0.3)

            axes[1].plot(df["timestamp"], df["humidity"], "g-", alpha=0.75, linewidth=1.2, label="Humidity")
            if len(feat_df) > 0 and hybrid_flag.any():
                axes[1].scatter(feat_df.loc[hybrid_flag, "timestamp"], feat_df.loc[hybrid_flag, "humidity"], color="red", s=30, zorder=5, label="Anomaly")
            axes[1].set_ylabel("Humidity (% RH)")
            axes[1].set_xlabel("Time")
            axes[1].legend(loc="upper right")
            axes[1].grid(True, alpha=0.3)
            plt.tight_layout()
            st.pyplot(fig)
            plt.close(fig)

        with tab2:
            fig2, ax2 = plt.subplots(figsize=(6, 4))
            ax2.scatter(df["temperature"], df["humidity"], c=range(len(df)), cmap="viridis", alpha=0.75, s=30)
            ax2.set_xlabel("Temperature (°C)")
            ax2.set_ylabel("Humidity (% RH)")
            ax2.set_title("Temperature vs Humidity Trajectory")
            ax2.grid(True, alpha=0.3)
            st.pyplot(fig2)
            plt.close(fig2)

        st.subheader("Recent Readings")
        recent = df.tail(15).sort_values("timestamp", ascending=False).reset_index(drop=True)
        recent["timestamp"] = recent["timestamp"].dt.strftime("%H:%M:%S")
        st.dataframe(recent[["timestamp", "temperature", "humidity"]], hide_index=True, width='stretch')

        st.download_button(
            "📥 Download Session CSV",
            df.to_csv(index=False),
            f"readings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "text/csv",
            width='stretch',
        )

    alert_hist = load_recent_alert_log(limit=15)
    if alert_hist is not None and len(alert_hist) > 0:
        with st.expander("🔔 Employee Alert History"):
            st.dataframe(alert_hist, hide_index=True, width='stretch')

    st.divider()
    st.caption("IoT Sensor Monitor | ESP32 + DHT11 | Dungu Avinash Reddy")

    if st.session_state.is_collecting:
        time.sleep(config.get("dashboard.refresh_interval_sec", 2))
        st.rerun()


if __name__ == "__main__":
    main()
