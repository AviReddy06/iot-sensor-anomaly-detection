#!/usr/bin/env python3
"""
dashboard/Home.py
Entry point for the multi-page IoT Sensor Anomaly Detection Streamlit dashboard.
Run via: python -m streamlit run dashboard/Home.py --server.port 8501 --server.address localhost
"""

from pathlib import Path
import json
import sys

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

st.set_page_config(
    page_title="AI-Based IoT Sensor Anomaly Detection",
    page_icon="🌡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("AI-Based IoT Sensor Anomaly Detection")

st.markdown("""
End-to-end anomaly detection and health monitoring system for **ESP32 + DHT11** temperature and humidity telemetry over USB serial.

### Core Pipeline & Detectors
1. **Z-Score Baseline** — Fixed mean/std threshold (`3.0 sigma`) trained on normal ambient readings.
2. **Adaptive Gated EWMA-Z** — Causal Cauchy-weighted EWMA baseline that adapts to gradual room/weather drift while freezing during sustained excursions (`3.5 sigma`).
3. **Isolation Forest + Gated Persistence** — Unsupervised detector trained on `12` time-aware, session-aware features (`ewma residuals`, `rates`, `10s std`, `reversal jitter`, `joint norms`) with persistence filtering to eliminate post-event echoes.
4. **Hybrid Ensemble (IF | Adaptive EWMA-Z)** — Combines dynamic disturbance sensitivity (spikes/chatter/drops) with drift-aware plateau sensitivity (`offset_fault` / sustained heating).
""")

summary_path = PROJECT_ROOT / "models" / "evaluation_summary.json"
if summary_path.exists():
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        eval_m = summary.get("datasets", {}).get("eval_suite", {}).get("Hybrid (IF + EWMA-Z)", {})
        pilot_m = summary.get("datasets", {}).get("pilot", {}).get("Hybrid (IF + EWMA-Z)", {})
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Clean Training Rows", f"{summary.get('training_summary', {}).get('rows', 0):,}")
        with col2:
            st.metric("Pilot F1 (Hybrid)", f"{pilot_m.get('f1', 0.0):.3f}", f"FP: {pilot_m.get('fp', 0)}")
        with col3:
            st.metric("Eval Suite F1 (Hybrid)", f"{eval_m.get('f1', 0.0):.3f}", f"Ev: {eval_m.get('events_caught', 0)}/{eval_m.get('events_total', 0)}")
        with col4:
            live_fp = summary.get("eval_suite_breakdown", {}).get("live_dht11_normal", {}).get("hybrid_fp", "N/A")
            st.metric("Live Hardware FP (COM19)", f"{live_fp}")
    except Exception:
        pass

st.divider()

if st.button("Start Analysis", type="primary", width='stretch'):
    st.switch_page("pages/1_Analyse.py")

st.divider()
st.caption("Dungu Avinash Reddy | Roll RK3P25KZA09 | Reg. 12509090 | ESP32 + DHT11 Verified on COM19")

with st.sidebar:
    st.header("Navigation")
    st.markdown("""
    **Multi-Page App:**
    1. **Home** — System architecture & summary
    2. **Analyse** — Load Eval Suite / Pilot / Test / Upload CSV / Live ESP32 stream
    3. **Results** — Client View & Technical View with dynamic sensitivity tuning
    4. **Model & Metrics** — Live metrics from `models/evaluation_summary.json`

    **Standalone Interfaces:**
    - `streamlit run dashboard/user_app.py` (Client Live Monitor)
    - `streamlit run dashboard/admin_app.py` (Admin & Model Manager)
    """)
    st.divider()
    st.caption("AI-Based IoT Sensor Anomaly Detection")
