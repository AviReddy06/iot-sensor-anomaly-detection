
#!/usr/bin/env python3
"""
dashboard/pages/1_Analyse.py
Data loading, unified time-aware feature computation, and multi-detector anomaly scoring.
Supports Demo Datasets, CSV Upload, Local ESP32 Serial, and Render Cloud Telemetry.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime
import json
import os
from pathlib import Path
import queue
import sys
import threading
import time
import urllib.error
import urllib.request

import joblib
import numpy as np
import pandas as pd
import serial
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from alerts.streamlit_panel import render_alert_sidebar
from collect.serial_utils import (
    detect_esp32_port,
    list_serial_ports,
    open_serial_port,
    parse_sensor_line,
    register_active_serial_port,
    release_active_serial_port,
    unregister_active_serial_port,
)
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
# SESSION STATE
# ============================================================

if "processed_df" not in st.session_state:
    st.session_state.processed_df = None
if "serial_queue" not in st.session_state:
    st.session_state.serial_queue = queue.Queue(
        maxsize=config.get("dashboard.buffer_maxlen", 500)
    )
if "data_buffer" not in st.session_state:
    st.session_state.data_buffer = deque(
        maxlen=config.get("dashboard.buffer_maxlen", 500)
    )
if "serial_thread" not in st.session_state:
    st.session_state.serial_thread = None
if "is_collecting" not in st.session_state:
    st.session_state.is_collecting = False
if "stop_event" not in st.session_state:
    st.session_state.stop_event = None
if "serial_error" not in st.session_state:
    st.session_state.serial_error = None
if "is_cloud_collecting" not in st.session_state:
    st.session_state.is_cloud_collecting = False
if "cloud_error" not in st.session_state:
    st.session_state.cloud_error = None
if "cloud_last_id" not in st.session_state:
    st.session_state.cloud_last_id = 0


# ============================================================
# DATA LOADING
# ============================================================

def load_demo_dataset(choice: str) -> pd.DataFrame | None:
    """Load selected local evaluation/pilot/test dataset."""
    pilot_prepared = PROJECT_ROOT / "data" / "processed" / "pilot_data_prepared.csv"
    pilot_path = (
        pilot_prepared
        if pilot_prepared.exists()
        else PROJECT_ROOT / "data" / "raw" / "pilot_data.csv"
    )

    file_map = {
        "Unseen Multi-Fault + Live Suite (1,950 rows)": (
            PROJECT_ROOT / "data" / "processed" / "eval_test_suite.csv"
        ),
        "Pilot Session Annotated (3,087 rows)": pilot_path,
        "Legacy Test Set (56 rows)": (
            PROJECT_ROOT / "data" / "processed" / "test_data_with_labels.csv"
        ),
    }

    path = file_map[choice]

    if not path.exists():
        st.error(f"Dataset not found: {path}")
        return None

    df = pd.read_csv(path)

    annotation_path = (
        PROJECT_ROOT / "data" / "processed" / "pilot_event_annotations.csv"
    )

    if "Pilot" in choice and annotation_path.exists():
        ann = pd.read_csv(annotation_path)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df["label"] = 0

        for _, row in ann.iterrows():
            mask = (
                (df["timestamp"] >= pd.to_datetime(row["start_time"]))
                & (df["timestamp"] <= pd.to_datetime(row["end_time"]))
            )
            df.loc[mask, "label"] = 1

    st.success(f"Loaded {choice}: {len(df)} rows")
    return df


def load_uploaded_file(uploaded_file) -> pd.DataFrame | None:
    """Load and validate uploaded CSV data."""
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

    required = {"timestamp", "temperature", "humidity"}

    if required.issubset(df.columns):
        return df

    if len(df.columns) == 3:
        col_vals = [str(col).strip() for col in df.columns]
        looks_headerless = (
            any(":" in col or "T" in col for col in col_vals)
            or all(
                col.lstrip("+-").replace(".", "", 1).isdigit()
                for col in col_vals[1:]
            )
        )

        if looks_headerless:
            uploaded_file.seek(0)
            df = pd.read_csv(
                uploaded_file,
                header=None,
                names=["timestamp", "temperature", "humidity"],
            )
            st.success(f"Loaded headerless CSV: {len(df)} rows")
            return df

    st.error(
        "Expected columns ['timestamp', 'temperature', 'humidity']. "
        f"Found: {list(df.columns)}"
    )
    return None


# ============================================================
# ML PROCESSING
# ============================================================

def process_data(data: pd.DataFrame, source_name: str) -> pd.DataFrame | None:
    """Compute features and all anomaly detector outputs."""
    df = data.copy()

    df["timestamp"] = pd.to_datetime(
        df["timestamp"], errors="coerce"
    )
    df["temperature"] = pd.to_numeric(
        df["temperature"], errors="coerce"
    )
    df["humidity"] = pd.to_numeric(
        df["humidity"], errors="coerce"
    )

    df = (
        df.dropna(
            subset=["timestamp", "temperature", "humidity"]
        )
        .sort_values("timestamp", kind="stable")
        .reset_index(drop=True)
    )

    features_df = build_features(
        df,
        gap_threshold=GAP_THRESHOLD,
        roll_min=ROLL_MIN,
        short_window_sec=thresholds.get(
            "short_window_sec", config.short_window_sec
        ),
        long_window_sec=thresholds.get(
            "long_window_sec", config.long_window_sec
        ),
        ewma_halflife_sec=thresholds.get(
            "ewma_halflife_sec", config.ewma_halflife_sec
        ),
        ewma_macro_gap_sec=thresholds.get(
            "ewma_macro_gap_sec", config.ewma_macro_gap_sec
        ),
    )

    if len(features_df) == 0:
        st.warning(
            "Waiting for at least 2 valid readings inside a session "
            "to compute dynamic features."
        )
        return None

    X_scaled = scaler.transform(features_df[feature_cols])
    scores = iso.decision_function(X_scaled)

    if_raw = scores < iforest_threshold

    iforest_flag = apply_gated_persistence(
        if_raw,
        features_df["session_id"].to_numpy(),
        features_df=features_df,
    )

    ewma_z = compute_adaptive_ewma_z(
        features_df,
        ewma_temp_std,
        ewma_hum_std,
    )

    ewma_flag = ewma_z > ewma_zscore_threshold

    z_temp = np.abs(
        (features_df["temperature"] - normal_temp_mean)
        / normal_temp_std
    )
    z_hum = np.abs(
        (features_df["humidity"] - normal_hum_mean)
        / normal_hum_std
    )

    zscore_flag = (
        (z_temp > zscore_threshold)
        | (z_hum > zscore_threshold)
    )

    features_df["iforest_score"] = scores
    features_df["iforest_raw_anomaly"] = if_raw
    features_df["iforest_anomaly"] = iforest_flag
    features_df["ewma_z_score"] = ewma_z
    features_df["ewma_z_anomaly"] = ewma_flag
    features_df["zscore_anomaly"] = zscore_flag.to_numpy()
    features_df["hybrid_anomaly"] = iforest_flag | ewma_flag
    features_df["source"] = source_name

    return features_df


# ============================================================
# LOCAL SERIAL STREAM
# ============================================================

def serial_reader(
    port: str,
    baud: int,
    q_out: queue.Queue,
    stop_event: threading.Event,
) -> None:
    """Read validated ESP32 sensor lines in a background thread."""
    ser = None
    last_ts = None
    curr_thread = threading.current_thread()

    try:
        release_active_serial_port(port)
        ser = open_serial_port(port, baudrate=baud, timeout=1.0)

        register_active_serial_port(
            port, stop_event, curr_thread, ser
        )

        while not stop_event.is_set():
            line_bytes = ser.readline()

            if not line_bytes:
                continue

            parsed = parse_sensor_line(
                line_bytes.decode("utf-8", errors="ignore")
            )

            if parsed is None:
                continue

            temp, hum = parsed
            ts = datetime.now().isoformat(timespec="seconds")

            if ts == last_ts:
                continue

            last_ts = ts

            record = {
                "timestamp": ts,
                "temperature": temp,
                "humidity": hum,
            }

            try:
                q_out.put_nowait(record)
            except queue.Full:
                try:
                    q_out.get_nowait()
                except queue.Empty:
                    pass

                q_out.put_nowait(record)

    except serial.SerialException as exc:
        if not stop_event.is_set():
            q_out.put(("error", str(exc)))

    except Exception as exc:
        if not stop_event.is_set():
            q_out.put(("error", str(exc)))

    finally:
        unregister_active_serial_port(port, curr_thread)

        if ser is not None and ser.is_open:
            try:
                ser.close()
            except Exception:
                pass


def drain_serial_queue() -> None:
    """Move serial queue items into the session buffer."""
    while not st.session_state.serial_queue.empty():
        item = st.session_state.serial_queue.get_nowait()

        if isinstance(item, tuple) and item[0] == "error":
            st.session_state.serial_error = item[1]
            st.session_state.is_collecting = False
        else:
            st.session_state.data_buffer.append(item)


# ============================================================
# RENDER CLOUD API
# ============================================================

def get_backend_url() -> str:
    """Get backend URL from Streamlit Secrets or environment."""
    try:
        value = st.secrets.get(
            "BACKEND_URL",
            os.environ.get("BACKEND_URL", ""),
        )
    except Exception:
        value = os.environ.get("BACKEND_URL", "")

    return str(value).strip().rstrip("/")


def fetch_cloud_readings(limit: int = 500) -> int:
    """Fetch new readings from Render without duplicating database IDs."""
    backend_url = get_backend_url()

    if not backend_url:
        raise RuntimeError(
            "BACKEND_URL is missing. Add it to Streamlit Cloud Secrets."
        )

    url = f"{backend_url}/api/client/readings?limit={limit}"

    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json"},
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        records = json.loads(
            response.read().decode("utf-8")
        )

    if not isinstance(records, list):
        raise ValueError(
            "Backend returned an unexpected readings response."
        )

    new_records = [
        record
        for record in records
        if isinstance(record, dict)
        and int(record.get("id", 0))
        > st.session_state.cloud_last_id
    ]

    new_records.sort(
        key=lambda record: int(record["id"])
    )

    for record in new_records:
        st.session_state.data_buffer.append({
            "id": int(record["id"]),
            "timestamp": record["timestamp"],
            "temperature": float(record["temperature"]),
            "humidity": float(record["humidity"]),
        })

        st.session_state.cloud_last_id = max(
            st.session_state.cloud_last_id,
            int(record["id"]),
        )

    st.session_state.cloud_error = None

    return len(new_records)


# ============================================================
# PAGE UI
# ============================================================

st.title("Analyse Sensor Telemetry")

st.markdown(
    "Load recorded datasets, upload custom CSV files, or monitor "
    "live **ESP32 + DHT11** telemetry locally or through the cloud."
)

source_option = st.radio(
    "Choose data source:",
    [
        "Demo data",
        "Upload CSV",
        "Live from ESP32 (serial)",
        "Live from Render (Cloud)",
    ],
    horizontal=True,
)

df_input: pd.DataFrame | None = None
source_name = ""


# ============================================================
# DEMO DATA
# ============================================================

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


# ============================================================
# CSV UPLOAD
# ============================================================

elif source_option == "Upload CSV":
    uploaded = st.file_uploader(
        "Upload CSV file (`timestamp,temperature,humidity`)",
        type=["csv"],
    )

    if uploaded is not None:
        df_input = load_uploaded_file(uploaded)
        source_name = "upload"


# ============================================================
# LOCAL ESP32 SERIAL
# ============================================================

elif source_option == "Live from ESP32 (serial)":
    detected_ports = list_serial_ports()
    port_options = (
        [dev for dev, _ in detected_ports]
        or [config.serial_port]
    )

    default_port = detect_esp32_port(config.serial_port)
    default_idx = (
        port_options.index(default_port)
        if default_port in port_options
        else 0
    )

    with st.sidebar:
        st.header("Serial Settings")

        port = st.selectbox(
            "COM Port",
            port_options,
            index=default_idx,
        )

        baud_choices = [9600, 19200, 38400, 57600, 115200]

        baud = st.selectbox(
            "Baud Rate",
            baud_choices,
            index=(
                baud_choices.index(config.baudrate)
                if config.baudrate in baud_choices
                else 4
            ),
        )

        if not st.session_state.is_collecting:
            if st.button(
                "▶ Start Serial Stream",
                type="primary",
                width="stretch",
            ):
                st.session_state.serial_error = None
                st.session_state.cloud_error = None
                st.session_state.processed_df = None
                st.session_state.is_cloud_collecting = False
                st.session_state.is_collecting = True
                st.session_state.active_serial_port = port
                st.session_state.stop_event = threading.Event()
                st.session_state.data_buffer.clear()

                while not st.session_state.serial_queue.empty():
                    try:
                        st.session_state.serial_queue.get_nowait()
                    except queue.Empty:
                        break

                st.session_state.serial_thread = threading.Thread(
                    target=serial_reader,
                    args=(
                        port,
                        int(baud),
                        st.session_state.serial_queue,
                        st.session_state.stop_event,
                    ),
                    daemon=True,
                )

                st.session_state.serial_thread.start()
                st.rerun()

        else:
            if st.button(
                "⏹ Stop Stream",
                type="primary",
                width="stretch",
            ):
                st.session_state.is_collecting = False

                if st.session_state.stop_event is not None:
                    st.session_state.stop_event.set()

                release_active_serial_port(port)

                if st.session_state.serial_thread is not None:
                    st.session_state.serial_thread.join(timeout=2)

                st.rerun()



# ============================================================
# REAL-TIME SENSOR MONITORING
# ============================================================

if (
    st.session_state.is_collecting
    or st.session_state.is_cloud_collecting
):
    if len(st.session_state.data_buffer) > 0:
        chart_df = pd.DataFrame(
            list(st.session_state.data_buffer)
        )

        chart_df["timestamp"] = pd.to_datetime(
            chart_df["timestamp"],
            errors="coerce",
        )

        chart_df["temperature"] = pd.to_numeric(
            chart_df["temperature"],
            errors="coerce",
        )

        chart_df["humidity"] = pd.to_numeric(
            chart_df["humidity"],
            errors="coerce",
        )

        chart_df = (
            chart_df.dropna(
                subset=["timestamp", "temperature", "humidity"]
            )
            .sort_values("timestamp")
            .tail(120)
        )

        if not chart_df.empty:
            st.divider()
            st.header("📡 Real-Time Sensor Monitoring")

            latest = chart_df.iloc[-1]

            metric1, metric2, metric3 = st.columns(3)

            metric1.metric(
                "🌡️ Current Temperature",
                f"{latest['temperature']:.2f} °C",
            )

            metric2.metric(
                "💧 Current Humidity",
                f"{latest['humidity']:.2f} %",
            )

            metric3.metric(
                "📊 Total Readings",
                len(st.session_state.data_buffer),
            )

            st.subheader("Temperature Monitoring")

            st.line_chart(
                chart_df,
                x="timestamp",
                y="temperature",
                height=300,
                color="#FF4B4B",
            )

            st.subheader("Humidity Monitoring")

            st.line_chart(
                chart_df,
                x="timestamp",
                y="humidity",
                height=300,
                color="#2196F3",
            )

            st.caption(
                "Showing the latest 120 sensor readings. "
                "Graphs update automatically as new telemetry arrives."
            )

# ============================================================
# RENDER CLOUD MODE
# ============================================================

elif source_option == "Live from Render (Cloud)":
    with st.sidebar:
        st.header("☁️ Cloud Settings")

        st.caption(
            "Reads ESP32 telemetry stored by your Render FastAPI backend."
        )

        if not st.session_state.is_cloud_collecting:
            if st.button(
                "▶ Start Cloud Stream",
                type="primary",
                width="stretch",
            ):
                st.session_state.serial_error = None
                st.session_state.cloud_error = None
                st.session_state.processed_df = None

                st.session_state.is_collecting = False
                st.session_state.is_cloud_collecting = True

                st.session_state.cloud_last_id = 0
                st.session_state.data_buffer.clear()

                st.rerun()

        else:
            if st.button(
                "⏹ Stop Cloud Stream",
                type="primary",
                width="stretch",
            ):
                st.session_state.is_cloud_collecting = False
                st.rerun()


# ============================================================
# ERRORS AND ALERT SETTINGS
# ============================================================

if st.session_state.get("serial_error"):
    st.error(
        f"Serial Error: {st.session_state.serial_error}"
    )

if st.session_state.get("cloud_error"):
    st.warning(
        f"Cloud connection issue: {st.session_state.cloud_error}"
    )

latest_buf = (
    st.session_state.data_buffer[-1]
    if st.session_state.data_buffer
    else {}
)

alert_mgr = render_alert_sidebar(
    "analyse",
    default_temp=float(
        latest_buf.get("temperature", 26.0)
    ),
    default_hum=float(
        latest_buf.get("humidity", 58.0)
    ),
)


# ============================================================
# DEMO / CSV PROCESSING
# ============================================================

if df_input is not None:
    with st.spinner(
        "Computing session-aware features and scoring..."
    ):
        processed = process_data(df_input, source_name)

    if processed is not None:
        st.session_state.processed_df = processed

        st.success(
            f"Scored {len(processed):,} rows "
            f"with {len(feature_cols)} features."
        )


# ============================================================
# CLOUD DATA FETCHING
# ============================================================

if st.session_state.is_cloud_collecting:
    try:
        added = fetch_cloud_readings()

        if added:
            st.caption(
                f"☁️ Received {added} new cloud reading(s)."
            )

    except urllib.error.HTTPError as exc:
        st.session_state.cloud_error = (
            f"HTTP {exc.code}: {exc.reason}"
        )

    except urllib.error.URLError as exc:
        st.session_state.cloud_error = (
            f"Could not reach Render backend: {exc.reason}"
        )

    except (TimeoutError, ValueError, RuntimeError) as exc:
        st.session_state.cloud_error = str(exc)

    except Exception as exc:
        st.session_state.cloud_error = (
            f"{type(exc).__name__}: {exc}"
        )


# ============================================================
# LIVE STREAM PROCESSING
# ============================================================

if (
    st.session_state.is_collecting
    or st.session_state.is_cloud_collecting
):
    if st.session_state.is_collecting:
        drain_serial_queue()

    if len(st.session_state.data_buffer) >= 2:
        live_df = pd.DataFrame(
            list(st.session_state.data_buffer)
        )

        live_df["timestamp"] = pd.to_datetime(
            live_df["timestamp"],
            errors="coerce",
        )

        latest_ts = live_df["timestamp"].iloc[-1]

        if pd.notna(latest_ts):
            now_ts = (
                pd.Timestamp.now(tz=latest_ts.tz)
                if latest_ts.tz is not None
                else pd.Timestamp.now()
            )

            stale_sec = (
                now_ts - latest_ts
            ).total_seconds()

            if stale_sec > max(15.0, GAP_THRESHOLD):
                source_label = (
                    "cloud backend"
                    if st.session_state.is_cloud_collecting
                    else "USB sensor"
                )

                st.warning(
                    f"Sensor stream stale: no valid DHT11 reading "
                    f"received for {stale_sec:.0f}s "
                    f"(check {source_label})."
                )

        source_label = (
            "cloud"
            if st.session_state.is_cloud_collecting
            else "live"
        )

        processed = process_data(
            live_df,
            source_label,
        )

        if processed is not None:
            st.session_state.processed_df = processed

            dispatched = alert_mgr.process_latest(
                processed,
                live_mode=True,
            )

            if dispatched is not None:
                st.toast(
                    f"🔔 Employee Alert: "
                    f"{dispatched.event_type} "
                    f"({dispatched.severity})"
                )

    else:
        stream_label = (
            "Render cloud"
            if st.session_state.is_cloud_collecting
            else "ESP32"
        )

        st.info(
            f"Streaming from {stream_label}... "
            f"collected {len(st.session_state.data_buffer)} "
            f"reading(s) so far."
        )


# ============================================================
# RESULTS
# ============================================================

if st.session_state.processed_df is not None:
    res = st.session_state.processed_df

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Rows Processed",
        f"{len(res):,}",
    )

    c2.metric(
        "Hybrid Alerts (IF | EWMA-Z)",
        int(res["hybrid_anomaly"].sum()),
    )

    c3.metric(
        "IF (Persistence) Flags",
        int(res["iforest_anomaly"].sum()),
    )

    c4.metric(
        "Adaptive EWMA-Z Flags",
        int(res["ewma_z_anomaly"].sum()),
    )

    st.subheader("Latest Telemetry Preview")

    preview_cols = [
        col
        for col in [
            "timestamp",
            "temperature",
            "humidity",
            "ewma_z_score",
            "iforest_score",
            "hybrid_anomaly",
            "iforest_anomaly",
            "zscore_anomaly",
            "label",
        ]
        if col in res.columns
    ]

    st.dataframe(
        res.tail(15)[preview_cols],
        hide_index=True,
        width="stretch",
    )

    st.caption(
        "Navigate to the **Results** page "
        "for interactive Client & Technical views."
    )


# ============================================================
# AUTO REFRESH
# ============================================================

if (
    st.session_state.is_collecting
    or st.session_state.is_cloud_collecting
):
    time.sleep(
        config.get("dashboard.refresh_interval_sec", 2)
    )
    st.rerun()
