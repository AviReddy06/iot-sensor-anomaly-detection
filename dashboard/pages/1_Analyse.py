#!/usr/bin/env python3
"""
dashboard/pages/1_Analyse.py
Data loading, unified time-aware feature computation, and multi-detector anomaly scoring.
Supports Demo Datasets (Eval Suite / Pilot / Legacy Test), Upload CSV, and Live ESP32 Serial.
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
import numpy as np
import pandas as pd
import serial
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from collect.serial_utils import detect_esp32_port, list_serial_ports, open_serial_port, parse_sensor_line
from config import config
from features.feature_engine import (
    MODEL_FEATURE_COLS,
    apply_gated_persistence,
    build_features,
    compute_adaptive_ewma_z,
)

st.set_page_config(page_title="Analyse", page_icon="🔬", layout="wide")


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


iso, scaler, thresholds = load_models()

feature_cols = thresholds.get("feature_cols", MODEL_FEATURE_COLS)
iforest_threshold = float(thresholds["iforest_threshold"])
zscore_threshold = float(thresholds["zscore_threshold"])
ewma_zscore_threshold = float(thresholds.get("ewma_zscore_threshold", 3.5))
normal_temp_mean = float(thresholds["normal_temp_mean"])
normal_temp_std = float(thresholds["normal_temp_std"])
normal_hum_mean = float(thresholds["normal_hum_mean"])
normal_hum_std = float(thresholds["normal_hum_std"])
ewma_temp_std = float(thresholds.get("ewma_temp_std", 0.65))
ewma_hum_std = float(thresholds.get("ewma_hum_std", 3.0))
GAP_THRESHOLD = float(thresholds.get("GAP_THRESHOLD", config.gap_threshold_sec))
ROLL_MIN = int(thresholds.get("ROLL_MIN", config.roll_min))


# ============================================================
# SESSION STATE INIT
# ============================================================
if "processed_df" not in st.session_state:
    st.session_state.processed_df = None
if "serial_queue" not in st.session_state:
    st.session_state.serial_queue = queue.Queue(maxsize=config.get("dashboard.buffer_maxlen", 500))
if "data_buffer" not in st.session_state:
    st.session_state.data_buffer = deque(maxlen=config.get("dashboard.buffer_maxlen", 500))
if "serial_thread" not in st.session_state:
    st.session_state.serial_thread = None
if "is_collecting" not in st.session_state:
    st.session_state.is_collecting = False
if "stop_event" not in st.session_state:
    st.session_state.stop_event = None
if "serial_error" not in st.session_state:
    st.session_state.serial_error = None


def load_demo_dataset(choice: str) -> pd.DataFrame | None:
    """Load selected local evaluation/pilot/test dataset."""
    file_map = {
        "Unseen Multi-Fault + Live Suite (1,950 rows)": PROJECT_ROOT / "data" / "processed" / "eval_test_suite.csv",
        "Pilot Session Annotated (3,087 rows)": PROJECT_ROOT / "data" / "processed" / "pilot_data_prepared.csv",
        "Legacy Test Set (56 rows)": PROJECT_ROOT / "data" / "processed" / "test_data_with_labels.csv",
    }
    path = file_map[choice]
    if not path.exists():
        st.error(f"Dataset not found: {path}")
        return None
    df = pd.read_csv(path)
    if "Pilot" in choice and (PROJECT_ROOT / "data" / "processed" / "pilot_event_annotations.csv").exists():
        ann = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "pilot_event_annotations.csv")
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df["label"] = 0
        for _, r in ann.iterrows():
            m = (df["timestamp"] >= pd.to_datetime(r["start_time"])) & (df["timestamp"] <= pd.to_datetime(r["end_time"]))
            df.loc[m, "label"] = 1
    st.success(f"Loaded {choice}: {len(df)} rows")
    return df


def load_uploaded_file(uploaded_file) -> pd.DataFrame | None:
    """Load and validate an uploaded CSV with timestamp, temperature, humidity."""
    if uploaded_file is None:
        return None
    if uploaded_file.size == 0:
        st.error("Uploaded file is empty.")
        return None
    try:
        df = pd.read_csv(uploaded_file)
    except Exception as exc:
        st.error(f"Could not parse CSV: {exc}")
        return None

    if len(df.columns) >= 3 and set(["timestamp", "temperature", "humidity"]).issubset(df.columns):
        return df

    if len(df.columns) == 3:
        col_vals = [str(c).strip() for c in df.columns]
        looks_headerless = any(":" in c or "T" in c for c in col_vals) or all(
            c.lstrip("+-").replace(".", "", 1).isdigit() for c in col_vals[1:]
        )
        if looks_headerless:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, header=None, names=["timestamp", "temperature", "humidity"])
            st.success(f"Loaded headerless CSV: {len(df)} rows")
            return df

    st.error(f"Expected columns ['timestamp', 'temperature', 'humidity']. Found: {list(df.columns)}")
    return None


def process_data(data: pd.DataFrame, source_name: str) -> pd.DataFrame | None:
    """Build unified features and compute Z-Score, Adaptive EWMA-Z, IF, and Hybrid flags."""
    df = data.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp", "temperature", "humidity"]).sort_values("timestamp", kind="stable").reset_index(drop=True)

    features_df = build_features(
        df,
        gap_threshold=GAP_THRESHOLD,
        roll_min=ROLL_MIN,
        short_window_sec=thresholds.get("short_window_sec", config.short_window_sec),
        long_window_sec=thresholds.get("long_window_sec", config.long_window_sec),
        ewma_halflife_sec=thresholds.get("ewma_halflife_sec", config.ewma_halflife_sec),
        ewma_macro_gap_sec=thresholds.get("ewma_macro_gap_sec", config.ewma_macro_gap_sec),
    )

    if len(features_df) == 0:
        st.warning("Waiting for at least 2 valid readings inside a session to compute dynamic features.")
        return None

    X_scaled = scaler.transform(features_df[feature_cols])
    scores = iso.decision_function(X_scaled)
    if_raw = scores < iforest_threshold
    iforest_flag = apply_gated_persistence(if_raw, features_df["session_id"].to_numpy(), features_df=features_df)

    ewma_z = compute_adaptive_ewma_z(features_df, ewma_temp_std, ewma_hum_std)
    ewma_flag = ewma_z > ewma_zscore_threshold

    z_temp = np.abs((features_df["temperature"] - normal_temp_mean) / normal_temp_std)
    z_hum = np.abs((features_df["humidity"] - normal_hum_mean) / normal_hum_std)
    zscore_flag = (z_temp > zscore_threshold) | (z_hum > zscore_threshold)

    features_df["iforest_score"] = scores
    features_df["iforest_raw_anomaly"] = if_raw
    features_df["iforest_anomaly"] = iforest_flag
    features_df["ewma_z_score"] = ewma_z
    features_df["ewma_z_anomaly"] = ewma_flag
    features_df["zscore_anomaly"] = zscore_flag.to_numpy()
    features_df["hybrid_anomaly"] = iforest_flag | ewma_flag
    features_df["source"] = source_name
    return features_df


def serial_reader(port: str, baud: int, q_out: queue.Queue, stop_event: threading.Event) -> None:
    """Background thread reading validated ESP32 + DHT11 lines without resetting the board."""
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
            record = {"timestamp": ts, "temperature": temp, "humidity": hum}
            try:
                q_out.put_nowait(record)
            except queue.Full:
                try:
                    q_out.get_nowait()
                except queue.Empty:
                    pass
                q_out.put_nowait(record)
    except serial.SerialException as exc:
        q_out.put(("error", str(exc)))
    except Exception as exc:
        q_out.put(("error", str(exc)))
    finally:
        if ser is not None and ser.is_open:
            ser.close()


def drain_serial_queue() -> None:
    """Drain items and errors from serial queue into session buffer."""
    while not st.session_state.serial_queue.empty():
        item = st.session_state.serial_queue.get_nowait()
        if isinstance(item, tuple) and item[0] == "error":
            st.session_state.serial_error = item[1]
            st.session_state.is_collecting = False
        else:
            st.session_state.data_buffer.append(item)


# ============================================================
# PAGE UI
# ============================================================
st.title("Analyse Sensor Telemetry")
st.markdown("Load recorded datasets, upload custom CSV files, or stream live **ESP32 + DHT11** telemetry over USB serial.")

source_option = st.radio(
    "Choose data source:",
    ["Demo data", "Upload CSV", "Live from ESP32 (serial)"],
    horizontal=True,
)

df_input: pd.DataFrame | None = None
source_name = ""

if source_option == "Demo data":
    demo_choice = st.selectbox(
        "Select benchmark dataset:",
        [
            "Unseen Multi-Fault + Live Suite (1,950 rows)",
            "Pilot Session Annotated (3,087 rows)",
            "Legacy Test Set (56 rows)",
        ],
    )
    if st.button("Load & Score Demo Data", type="primary"):
        df_input = load_demo_dataset(demo_choice)
        source_name = "demo"

elif source_option == "Upload CSV":
    uploaded = st.file_uploader("Upload CSV file (`timestamp,temperature,humidity`)", type=["csv"])
    if uploaded is not None:
        df_input = load_uploaded_file(uploaded)
        source_name = "upload"

elif source_option == "Live from ESP32 (serial)":
    detected_ports = list_serial_ports()
    port_options = [dev for dev, _ in detected_ports] or [config.serial_port]
    default_port = detect_esp32_port(config.serial_port)
    default_idx = port_options.index(default_port) if default_port in port_options else 0

    with st.sidebar:
        st.header("Serial Settings")
        port = st.selectbox("COM Port", port_options, index=default_idx)
        baud_choices = [9600, 19200, 38400, 57600, 115200]
        baud = st.selectbox("Baud Rate", baud_choices, index=baud_choices.index(config.baudrate) if config.baudrate in baud_choices else 4)

        if not st.session_state.is_collecting:
            if st.button("▶ Start Serial Stream", type="primary", width='stretch'):
                st.session_state.serial_error = None
                st.session_state.processed_df = None
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
        else:
            if st.button("⏹ Stop Stream", type="primary", width='stretch'):
                st.session_state.is_collecting = False
                if st.session_state.stop_event is not None:
                    st.session_state.stop_event.set()
                if st.session_state.serial_thread is not None:
                    st.session_state.serial_thread.join(timeout=2)
                st.rerun()

if st.session_state.get("serial_error"):
    st.error(f"Serial Error: {st.session_state.serial_error}")

if df_input is not None:
    with st.spinner("Computing session-aware features and scoring..."):
        processed = process_data(df_input, source_name)
    if processed is not None:
        st.session_state.processed_df = processed
        st.success(f"Scored {len(processed):,} rows with {len(feature_cols)} features.")

if st.session_state.is_collecting:
    drain_serial_queue()
    if len(st.session_state.data_buffer) >= 2:
        live_df = pd.DataFrame(list(st.session_state.data_buffer))
        latest_ts = pd.to_datetime(live_df["timestamp"].iloc[-1], errors="coerce")
        if pd.notna(latest_ts):
            stale_sec = (datetime.now() - latest_ts.to_pydatetime()).total_seconds()
            if stale_sec > max(15.0, float(GAP_THRESHOLD)):
                st.warning(f"Sensor stream stale: no valid DHT11 reading received for {stale_sec:.0f}s (check wiring / USB).")
        processed = process_data(live_df, "live")
        if processed is not None:
            st.session_state.processed_df = processed
    else:
        st.info(f"Streaming from ESP32... collected {len(st.session_state.data_buffer)} reading(s) so far.")

if st.session_state.processed_df is not None:
    res = st.session_state.processed_df
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rows Processed", f"{len(res):,}")
    c2.metric("Hybrid Alerts (IF | EWMA-Z)", int(res["hybrid_anomaly"].sum()))
    c3.metric("IF (Persistence) Flags", int(res["iforest_anomaly"].sum()))
    c4.metric("Adaptive EWMA-Z Flags", int(res["ewma_z_anomaly"].sum()))

    st.subheader("Latest Telemetry Preview")
    preview_cols = [c for c in ["timestamp", "temperature", "humidity", "ewma_z_score", "iforest_score", "hybrid_anomaly", "iforest_anomaly", "zscore_anomaly", "label"] if c in res.columns]
    st.dataframe(res.tail(15)[preview_cols], hide_index=True, width='stretch')
    st.caption("Navigate to the **Results** page for interactive Client & Technical views.")

if st.session_state.is_collecting:
    time.sleep(config.get("dashboard.refresh_interval_sec", 2))
    st.rerun()
