#!/usr/bin/env python3
"""
dashboard/pages/2_Results.py
Interactive Client View and Technical View with live updates and dynamic sensitivity control.
"""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import queue
import sys
import time

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from alerts.streamlit_panel import load_recent_alert_log, render_alert_sidebar
from config import config
from features.feature_engine import (
    MODEL_FEATURE_COLS,
    apply_gated_persistence,
    build_features,
    compute_adaptive_ewma_z,
)

st.set_page_config(page_title="Results", page_icon="📊", layout="wide")


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

sensitivity_map = thresholds.get(
    "sensitivity_thresholds",
    {
        "Low (0.1th %ile)": iforest_threshold - 0.02,
        "Medium (0.25th %ile)": iforest_threshold,
        "High (1.0th %ile)": iforest_threshold + 0.04,
    },
)


def refresh_live_buffer() -> None:
    """Drain queued serial messages and recompute live processed_df while collecting."""
    if not st.session_state.get("is_collecting", False):
        return
    q_in = st.session_state.get("serial_queue")
    buf = st.session_state.get("data_buffer")
    if q_in is None or buf is None:
        return
    while not q_in.empty():
        try:
            item = q_in.get_nowait()
        except queue.Empty:
            break
        if isinstance(item, tuple) and item[0] == "error":
            st.session_state.serial_error = item[1]
            st.session_state.is_collecting = False
        else:
            buf.append(item)

    if len(buf) >= 2:
        raw_df = pd.DataFrame(list(buf))
        feat = build_features(
            raw_df,
            gap_threshold=thresholds.get("GAP_THRESHOLD", config.gap_threshold_sec),
            roll_min=thresholds.get("ROLL_MIN", config.roll_min),
            short_window_sec=thresholds.get("short_window_sec", config.short_window_sec),
            long_window_sec=thresholds.get("long_window_sec", config.long_window_sec),
            ewma_halflife_sec=thresholds.get("ewma_halflife_sec", config.ewma_halflife_sec),
            ewma_macro_gap_sec=thresholds.get("ewma_macro_gap_sec", config.ewma_macro_gap_sec),
        )
        if len(feat) > 0:
            X_scaled = scaler.transform(feat[feature_cols])
            scores = iso.decision_function(X_scaled)
            if_raw = scores < iforest_threshold
            iforest_flg = apply_gated_persistence(if_raw, feat["session_id"].to_numpy(), features_df=feat)
            ewma_z_vals = compute_adaptive_ewma_z(feat, ewma_temp_std, ewma_hum_std)
            ewma_flg = ewma_z_vals > ewma_zscore_threshold
            zt = np.abs((feat["temperature"] - normal_temp_mean) / normal_temp_std)
            zh = np.abs((feat["humidity"] - normal_hum_mean) / normal_hum_std)
            feat["iforest_score"] = scores
            feat["iforest_raw_anomaly"] = if_raw
            feat["iforest_anomaly"] = iforest_flg
            feat["ewma_z_score"] = ewma_z_vals
            feat["ewma_z_anomaly"] = ewma_flg
            feat["zscore_anomaly"] = ((zt > zscore_threshold) | (zh > zscore_threshold)).to_numpy()
            feat["hybrid_anomaly"] = iforest_flg | ewma_flg
            feat["source"] = "live"
            st.session_state.processed_df = feat


refresh_live_buffer()

if "processed_df" not in st.session_state or st.session_state.processed_df is None:
    st.warning("No processed data found. Please run an analysis on the **Analyse** page first.")
    if st.button("Go to Analyse"):
        st.switch_page("pages/1_Analyse.py")
    st.stop()

df = st.session_state.processed_df.copy()
df["timestamp"] = pd.to_datetime(df["timestamp"])

# Sidebar Sensitivity Controls (dynamically updates all metrics and charts!)
with st.sidebar:
    st.header("Detector Controls")
    options = list(sensitivity_map.keys())
    default_idx = 1 if len(options) > 1 else 0
    sensitivity = st.selectbox("Isolation Forest Sensitivity", options, index=default_idx)
    selected_threshold = float(sensitivity_map[sensitivity])
    selected_ewma_z = st.slider("Adaptive EWMA-Z Threshold (σ)", 2.5, 6.0, float(ewma_zscore_threshold), 0.25)
    detector_mode = st.selectbox("Primary Alert Flag", ["Hybrid (IF + EWMA-Z)", "Isolation Forest", "Adaptive EWMA-Z", "Z-Score Baseline"], index=0)

    st.caption(f"IF Threshold ({sensitivity}): `{selected_threshold:.5f}`")
    st.caption(f"Default IF Threshold: `{iforest_threshold:.5f}`")
    st.divider()
    if st.session_state.get("is_collecting", False):
        if st.button("⏹ Stop Live Stream", type="primary", width='stretch'):
            st.session_state.is_collecting = False
            stop_ev = st.session_state.get("stop_event")
            if stop_ev is not None:
                stop_ev.set()
            th = st.session_state.get("serial_thread")
            if th is not None:
                th.join(timeout=2)
            st.rerun()
        st.divider()
    st.caption("Severity Rules:")
    st.caption("Low: |Z| < 3 | Medium: 3 <= |Z| < 5 | High: |Z| >= 5")

alert_mgr = render_alert_sidebar(
    "results",
    default_temp=float(df["temperature"].iloc[-1]) if len(df) else 26.0,
    default_hum=float(df["humidity"].iloc[-1]) if len(df) else 58.0,
)

# Dynamic predictions using chosen sensitivity & thresholds
iforest_scores = df["iforest_score"].to_numpy(dtype=float)
iforest_flag = apply_gated_persistence(
    iforest_scores < selected_threshold,
    df["session_id"].to_numpy(),
    features_df=df,
)
ewma_z = df["ewma_z_score"].to_numpy(dtype=float) if "ewma_z_score" in df.columns else compute_adaptive_ewma_z(df, ewma_temp_std, ewma_hum_std)
ewma_flag = ewma_z > selected_ewma_z

z_temp = np.abs((df["temperature"].to_numpy(dtype=float) - normal_temp_mean) / normal_temp_std)
z_hum = np.abs((df["humidity"].to_numpy(dtype=float) - normal_hum_mean) / normal_hum_std)
zscore_flag = (z_temp > zscore_threshold) | (z_hum > zscore_threshold)
hybrid_flag = iforest_flag | ewma_flag

if st.session_state.get("is_collecting", False) and len(df) > 0:
    latest_row = df.iloc[-1].to_dict()
    latest_row["iforest_anomaly"] = bool(iforest_flag[-1])
    latest_row["ewma_z_score"] = float(ewma_z[-1])
    latest_row["ewma_z_anomaly"] = bool(ewma_flag[-1])
    latest_row["hybrid_anomaly"] = bool(hybrid_flag[-1])
    dispatched = alert_mgr.evaluate_latest_row(latest_row, live_mode=True)
    if dispatched is not None:
        st.toast(f"🔔 Employee Alert: {dispatched.event_type} ({dispatched.severity})")

mode_flag_map = {
    "Hybrid (IF + EWMA-Z)": hybrid_flag,
    "Isolation Forest": iforest_flag,
    "Adaptive EWMA-Z": ewma_flag,
    "Z-Score Baseline": zscore_flag,
}
active_flag = mode_flag_map[detector_mode]

tab_client, tab_technical = st.tabs(["Client View", "Technical View"])

with tab_client:
    st.header("Client View")
    latest_window = active_flag[-min(15, len(active_flag)) :]
    if latest_window.any():
        st.error("🔴 **ALERT** — Unusual sensor behavior detected in the latest readings")
    elif active_flag.any():
        st.warning("🟠 **Notice** — Historical anomaly events found; latest readings are currently normal")
    else:
        st.success("🟢 **Normal** — Room climate telemetry is operating normally")

    st.divider()
    st.subheader("📋 Detected Events")

    events = []
    if active_flag.any():
        flagged_indices = np.where(active_flag)[0]
        event_start = flagged_indices[0]
        for i in range(1, len(flagged_indices)):
            if flagged_indices[i] - flagged_indices[i - 1] > 2:
                events.append((event_start, flagged_indices[i - 1]))
                event_start = flagged_indices[i]
        events.append((event_start, flagged_indices[-1]))

    if events:
        st.info(f"Detected {len(events)} anomaly event(s) using **{detector_mode}**")
        event_rows = []
        for idx, (s_i, e_i) in enumerate(events, start=1):
            ev = df.iloc[s_i : e_i + 1]
            t_start = ev["timestamp"].iloc[0]
            t_end = ev["timestamp"].iloc[-1]
            duration = (t_end - t_start).total_seconds()

            max_t_res = float(ev["temp_ewma_residual"].iloc[np.argmax(np.abs(ev["temp_ewma_residual"]))])
            max_h_res = float(ev["hum_ewma_residual"].iloc[np.argmax(np.abs(ev["hum_ewma_residual"]))])
            peak_z = float(np.max(ewma_z[s_i : e_i + 1]))

            if peak_z < 3.0:
                severity = "Low"
            elif peak_z < 5.0:
                severity = "Medium"
            else:
                severity = "High"

            parts = []
            if abs(max_t_res) >= 0.8:
                direction = "rose" if max_t_res > 0 else "dropped"
                parts.append(f"temperature {direction} ~{abs(max_t_res):.1f} °C vs baseline")
            if abs(max_h_res) >= 3.0:
                direction = "rose" if max_h_res > 0 else "dropped"
                parts.append(f"humidity {direction} ~{abs(max_h_res):.1f}% vs baseline")
            if not parts:
                parts.append("rapid short-term jitter / signal oscillation detected")

            msg = f"Event at {t_start.strftime('%H:%M:%S')}: " + ", ".join(parts) + f" (~{duration:.0f}s)"
            event_rows.append(
                {
                    "Event": idx,
                    "Start": t_start.strftime("%H:%M:%S"),
                    "End": t_end.strftime("%H:%M:%S"),
                    "Duration (s)": f"{duration:.0f}",
                    "Temp Range (°C)": f"{ev['temperature'].min():.1f} – {ev['temperature'].max():.1f}",
                    "Hum Range (%)": f"{ev['humidity'].min():.1f} – {ev['humidity'].max():.1f}",
                    "Severity": severity,
                    "Summary": msg,
                }
            )
        st.dataframe(pd.DataFrame(event_rows), hide_index=True, width='stretch')
    else:
        st.info("No anomaly events detected under the active settings.")

    st.divider()
    st.subheader("⏱️ Event Timeline")
    if events:
        fig, ax = plt.subplots(figsize=(10, max(2.5, 0.55 * len(events))))
        for i, (s_i, e_i) in enumerate(events):
            start_dt = df["timestamp"].iloc[s_i]
            end_dt = df["timestamp"].iloc[e_i]
            width_days = max((end_dt - start_dt).total_seconds(), 2.0) / 86400.0
            ax.barh(i, width_days, left=start_dt, height=0.5, color="#dc3545", alpha=0.8, edgecolor="black")
        ax.set_yticks(range(len(events)))
        ax.set_yticklabels([f"Event {i+1}" for i in range(len(events))])
        ax.set_xlabel("Time")
        ax.set_title("Anomaly Event Timeline")
        ax.grid(True, alpha=0.3, axis="x")
        plt.tight_layout()
        st.pyplot(fig)
        plt.close(fig)
    else:
        st.info("No events to plot.")


with tab_technical:
    st.header("🔧 Technical View")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rows Analysed", f"{len(df):,}")
    c2.metric("Hybrid Alerts", int(hybrid_flag.sum()))
    c3.metric("IF Anomalies", int(iforest_flag.sum()))
    c4.metric("Adaptive EWMA-Z Anomalies", int(ewma_flag.sum()))

    st.divider()
    st.subheader("📈 Telemetry & Detections")
    fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
    axes[0].plot(df["timestamp"], df["temperature"], "b-", alpha=0.75, linewidth=1.2, label="Temperature")
    if hybrid_flag.any():
        axes[0].scatter(df.loc[hybrid_flag, "timestamp"], df.loc[hybrid_flag, "temperature"], color="red", s=28, zorder=5, label="Hybrid Alert")
    axes[0].set_ylabel("Temperature (°C)")
    axes[0].legend(loc="upper right")
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(df["timestamp"], df["humidity"], "g-", alpha=0.75, linewidth=1.2, label="Humidity")
    if hybrid_flag.any():
        axes[1].scatter(df.loc[hybrid_flag, "timestamp"], df.loc[hybrid_flag, "humidity"], color="red", s=28, zorder=5, label="Hybrid Alert")
    axes[1].set_ylabel("Humidity (% RH)")
    axes[1].set_xlabel("Timestamp")
    axes[1].legend(loc="upper right")
    axes[1].grid(True, alpha=0.3)
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("📉 Isolation Forest Score")
        fig2, ax2 = plt.subplots(figsize=(6, 3))
        ax2.plot(df["timestamp"], iforest_scores, "b-", alpha=0.7)
        ax2.axhline(y=selected_threshold, color="red", linestyle="--", label=f"Threshold ({selected_threshold:.4f})")
        if iforest_flag.any():
            ax2.scatter(df.loc[iforest_flag, "timestamp"], iforest_scores[iforest_flag], color="red", s=22, zorder=5)
        ax2.set_ylabel("Decision Score")
        ax2.tick_params(axis="x", rotation=30)
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        fig2.tight_layout()
        st.pyplot(fig2)
        plt.close(fig2)

    with col_b:
        st.subheader("📊 Adaptive EWMA-Z Score")
        fig3, ax3 = plt.subplots(figsize=(6, 3))
        ax3.plot(df["timestamp"], ewma_z, "m-", alpha=0.7)
        ax3.axhline(y=selected_ewma_z, color="red", linestyle="--", label=f"Threshold ({selected_ewma_z:.2f}σ)")
        if ewma_flag.any():
            ax3.scatter(df.loc[ewma_flag, "timestamp"], ewma_z[ewma_flag], color="red", s=22, zorder=5)
        ax3.set_ylabel("Max |EWMA-Z|")
        ax3.tick_params(axis="x", rotation=30)
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        fig3.tight_layout()
        st.pyplot(fig3)
        plt.close(fig3)

    if "label" in df.columns:
        st.divider()
        st.subheader("📊 Quantitative Evaluation on Ground-Truth Labels")
        y_true = df["label"].to_numpy(dtype=int)
        rows_eval = []
        for mname, mpred in [
            ("Hybrid (IF + EWMA-Z)", hybrid_flag),
            ("Isolation Forest", iforest_flag),
            ("Adaptive EWMA-Z", ewma_flag),
            ("Z-Score Baseline", zscore_flag),
        ]:
            cm = confusion_matrix(y_true, mpred, labels=[0, 1])
            p, r, f1, _ = precision_recall_fscore_support(y_true, mpred, average="binary", zero_division=0)
            rows_eval.append(
                {
                    "Detector": mname,
                    "Precision": round(float(p), 3),
                    "Recall": round(float(r), 3),
                    "F1": round(float(f1), 3),
                    "TP": int(cm[1, 1]),
                    "FP": int(cm[0, 1]),
                    "FN": int(cm[1, 0]),
                    "TN": int(cm[0, 0]),
                }
            )
        st.dataframe(pd.DataFrame(rows_eval), hide_index=True, width='stretch')

    st.subheader("🚩 Flagged Rows Sample")
    flagged = df[active_flag].copy()
    if len(flagged) > 0:
        flagged["iforest_flag"] = iforest_flag[active_flag]
        flagged["ewma_z_flag"] = ewma_flag[active_flag]
        flagged["hybrid_flag"] = hybrid_flag[active_flag]
        cols_show = [c for c in ["timestamp", "temperature", "humidity", "ewma_z_score", "iforest_score", "hybrid_flag", "iforest_flag", "ewma_z_flag", "label"] if c in flagged.columns]
        st.dataframe(flagged[cols_show].tail(100), hide_index=True, width='stretch')
    else:
        st.info("No flagged rows under active detector.")

if st.session_state.get("is_collecting", False):
    time.sleep(config.get("dashboard.refresh_interval_sec", 2))
    st.rerun()
