#!/usr/bin/env python3
"""
dashboard/admin_app.py
Admin dashboard: system overview, threshold management, feature analytics,
model evaluation (internal + external), data export, and executable pipeline triggers.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.metrics import auc, confusion_matrix, precision_recall_fscore_support, roc_curve
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import config
from preprocess.clean_datasets import load_raw_normal
from features.feature_engine import (
    MODEL_FEATURE_COLS,
    apply_gated_persistence,
    compute_adaptive_ewma_z,
)

st.set_page_config(page_title="Admin - IoT Anomaly Detection", page_icon="⚙️", layout="wide")

st.markdown(
    """
<style>
    .admin-header { background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%); color: white; padding: 1rem; border-radius: 8px; }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_resource
def load_models():
    iso = joblib.load(PROJECT_ROOT / "models" / "iforest.joblib")
    scaler = joblib.load(PROJECT_ROOT / "models" / "scaler.joblib")
    with open(PROJECT_ROOT / "models" / "thresholds.json", "r", encoding="utf-8") as f:
        thresholds = json.load(f)
    summary_path = PROJECT_ROOT / "models" / "evaluation_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
    return iso, scaler, thresholds, summary


@st.cache_data
def load_reference_data():
    datasets = {}
    feat_dir = config.features_dir
    proc_dir = config.processed_dir
    try:
        for key, fname in [
            ("normal", feat_dir / "normal_features_full.csv"),
            ("pilot", feat_dir / "pilot_features_full.csv"),
            ("test", feat_dir / "test_features_full.csv"),
            ("eval_suite", feat_dir / "eval_suite_features_full.csv"),
        ]:
            if fname.exists():
                df = pd.read_csv(fname)
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                datasets[key] = df
        ann_path = proc_dir / "pilot_event_annotations.csv"
        if ann_path.exists():
            ann = pd.read_csv(ann_path)
            ann["start_time"] = pd.to_datetime(ann["start_time"])
            ann["end_time"] = pd.to_datetime(ann["end_time"])
            datasets["annotations"] = ann
    except Exception as exc:
        st.error(f"Error loading reference data: {exc}")
    return datasets


iso, scaler, thresholds, eval_summary = load_models()
ref_data = load_reference_data()

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
GAP_THRESHOLD = int(thresholds.get("GAP_THRESHOLD", config.gap_threshold_sec))
ROLL_MIN = int(thresholds.get("ROLL_MIN", config.roll_min))

st.markdown('<div class="admin-header"><h1>Admin Dashboard — IoT Anomaly Detection</h1></div>', unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    ["Overview", "Model Config", "Analytics", "Evaluation", "Data Manager", "Settings"]
)

with tab1:
    st.header("System Overview")
    normal_df = ref_data.get("normal")
    n_train = len(normal_df) if normal_df is not None else thresholds.get("training_rows", 0)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Primary Detector", "Hybrid (IF + EWMA-Z)")
    c2.metric("Model Features", len(feature_cols))
    c3.metric("Clean Training Rows", f"{n_train:,}")
    c4.metric("IF Threshold (0.25th %ile)", f"{iforest_threshold:.5f}")

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Active Thresholds")
        thresh_df = pd.DataFrame(
            {
                "Parameter": ["IF Threshold", "Adaptive EWMA-Z", "Fixed Z-Score", "Gap Threshold", "Rolling Min Periods"],
                "Value": [f"{iforest_threshold:.5f}", f"{ewma_zscore_threshold}σ", f"{zscore_threshold}σ", f"{GAP_THRESHOLD}s", f"{ROLL_MIN}"],
                "Notes": [
                    "0.25th percentile of clean normal IF scores",
                    "Cauchy-gated EWMA residual z-score cutoff",
                    "Fixed normal mean/std baseline cutoff",
                    "Gap seconds defining a new session_id",
                    "Minimum observations per rolling window",
                ],
            }
        )
        st.dataframe(thresh_df, hide_index=True, width='stretch')

    with c2:
        st.subheader("Training Baseline Statistics")
        if normal_df is not None:
            stats_df = pd.DataFrame(
                {
                    "Channel": ["Temperature (°C)", "Humidity (% RH)"],
                    "Mean": [f"{normal_df['temperature'].mean():.2f}", f"{normal_df['humidity'].mean():.2f}"],
                    "Std": [f"{normal_df['temperature'].std():.2f}", f"{normal_df['humidity'].std():.2f}"],
                    "EWMA Resid Std": [f"{ewma_temp_std:.3f}", f"{ewma_hum_std:.3f}"],
                    "Min": [f"{normal_df['temperature'].min():.2f}", f"{normal_df['humidity'].min():.2f}"],
                    "Max": [f"{normal_df['temperature'].max():.2f}", f"{normal_df['humidity'].max():.2f}"],
                }
            )
            st.dataframe(stats_df, hide_index=True, width='stretch')

    st.divider()
    st.subheader("Dataset Summary")
    summary_rows = []
    for name, df in ref_data.items():
        if isinstance(df, pd.DataFrame) and "timestamp" in df.columns:
            summary_rows.append(
                {
                    "Dataset": name,
                    "Rows": f"{len(df):,}",
                    "Columns": len(df.columns),
                    "Time Range": f"{df['timestamp'].min()} → {df['timestamp'].max()}",
                    "Sessions": int(df["session_id"].nunique()) if "session_id" in df.columns else "N/A",
                }
            )
    st.dataframe(pd.DataFrame(summary_rows), hide_index=True, width='stretch')


with tab2:
    st.header("Model Configuration")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Isolation Forest & Sensitivity")
        st.json(
            {
                "n_estimators": config.get("model.n_estimators", 200),
                "scaler_type": thresholds.get("scaler_type", "standard"),
                "threshold_percentile": thresholds.get("threshold_percentile", 0.25),
                "iforest_threshold": iforest_threshold,
                "sensitivity_thresholds": thresholds.get("sensitivity_thresholds", {}),
                "persistence_window": thresholds.get("persistence_window", 5),
                "persistence_min_hits": thresholds.get("persistence_min_hits", 3),
            }
        )
    with c2:
        st.subheader("EWMA & Z-Score Baselines")
        st.json(
            {
                "ewma_halflife_sec": thresholds.get("ewma_halflife_sec", 2400),
                "ewma_macro_gap_sec": thresholds.get("ewma_macro_gap_sec", 1800),
                "ewma_zscore_threshold": ewma_zscore_threshold,
                "ewma_temp_std": ewma_temp_std,
                "ewma_hum_std": ewma_hum_std,
                "zscore_threshold": zscore_threshold,
            }
        )

    st.divider()
    st.subheader("Modify Saved Thresholds")
    col1, col2 = st.columns(2)
    with col1:
        new_if = st.number_input("IF Threshold", value=iforest_threshold, format="%.5f", step=0.005)
        new_ewma_z = st.number_input("Adaptive EWMA-Z Threshold", value=ewma_zscore_threshold, format="%.2f", step=0.25)
    with col2:
        new_z = st.number_input("Fixed Z-Score Threshold", value=zscore_threshold, format="%.1f", step=0.5)
        new_gap = st.number_input("GAP_THRESHOLD (s)", value=GAP_THRESHOLD, step=1)
        new_roll = st.number_input("ROLL_MIN", value=ROLL_MIN, step=1)

    if st.button("Save Thresholds", type="primary"):
        thresholds["iforest_threshold"] = float(new_if)
        thresholds["ewma_zscore_threshold"] = float(new_ewma_z)
        thresholds["zscore_threshold"] = float(new_z)
        thresholds["GAP_THRESHOLD"] = int(new_gap)
        thresholds["ROLL_MIN"] = int(new_roll)
        with open(PROJECT_ROOT / "models" / "thresholds.json", "w", encoding="utf-8") as f:
            json.dump(thresholds, f, indent=2)
        st.cache_resource.clear()
        st.success("Thresholds saved cleanly to `models/thresholds.json`.")
        st.rerun()


with tab3:
    st.header("Feature Analytics")
    normal_df = ref_data.get("normal")
    if normal_df is not None:
        st.subheader("Engineered Feature Distributions (Normal Training Baseline)")
        available = [c for c in feature_cols if c in normal_df.columns]
        n_cols = 3
        n_rows = int(np.ceil(len(available) / n_cols))
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(14, 3.2 * n_rows))
        axes = np.atleast_1d(axes).flatten()
        for i, col in enumerate(available):
            axes[i].hist(normal_df[col].dropna(), bins=40, alpha=0.75, edgecolor="black")
            axes[i].set_title(col, fontsize=10)
            axes[i].grid(True, alpha=0.25)
        for j in range(len(available), len(axes)):
            axes[j].axis("off")
        plt.tight_layout()
        st.pyplot(fig)
        plt.close(fig)

        st.divider()
        st.subheader("Feature Correlation Matrix")
        corr = normal_df[available].corr()
        fig_c, ax_c = plt.subplots(figsize=(10, 8))
        sns.heatmap(corr, annot=True, cmap="RdBu_r", center=0, fmt=".2f", square=True, ax=ax_c)
        ax_c.set_title("Model Feature Correlations (Clean Normal Data)")
        st.pyplot(fig_c)
        plt.close(fig_c)
    else:
        st.info("Local `data/processed/features_v2/normal_features_full.csv` not built yet. Run **1. Run Cleaning** and **2. Build Features** in **Data Manager** (or `python features/build_features_v2.py`) to view full feature distributions.")


with tab4:
    st.header("Model Evaluation (Internal & External)")
    eval_suite = ref_data.get("eval_suite")
    test_df = ref_data.get("test")
    pilot_df = ref_data.get("pilot")
    annotations = ref_data.get("annotations")

    if eval_suite is not None and "label" in eval_suite.columns:
        st.subheader("Unseen Multi-Fault + Live Hardware Eval Suite")
        es_clean = eval_suite.dropna(subset=feature_cols).copy()
        y_es = es_clean["label"].to_numpy(dtype=int)
        if_sc_es = iso.decision_function(scaler.transform(es_clean[feature_cols]))
        if_pr_es = apply_gated_persistence(if_sc_es < iforest_threshold, es_clean["session_id"].to_numpy(), features_df=es_clean).astype(int)
        ez_es = compute_adaptive_ewma_z(es_clean, ewma_temp_std, ewma_hum_std)
        ez_pr_es = (ez_es > ewma_zscore_threshold).astype(int)
        hyb_pr_es = (if_pr_es | ez_pr_es).astype(int)
        z_es = np.maximum(
            np.abs((es_clean["temperature"] - normal_temp_mean) / normal_temp_std),
            np.abs((es_clean["humidity"] - normal_hum_mean) / normal_hum_std),
        ).to_numpy()
        z_pr_es = (z_es > zscore_threshold).astype(int)

        eval_rows = []
        for name, pr in [("Hybrid (IF + EWMA-Z)", hyb_pr_es), ("Isolation Forest", if_pr_es), ("Adaptive EWMA-Z", ez_pr_es), ("Z-Score Baseline", z_pr_es)]:
            cm = confusion_matrix(y_es, pr, labels=[0, 1])
            p, r, f1, _ = precision_recall_fscore_support(y_es, pr, average="binary", zero_division=0)
            eval_rows.append({"Detector": name, "Precision": f"{p:.3f}", "Recall": f"{r:.3f}", "F1": f"{f1:.3f}", "FP": int(cm[0, 1]), "FN": int(cm[1, 0])})
        st.dataframe(pd.DataFrame(eval_rows), hide_index=True, width='stretch')

        # Aligned ROC curve on es_clean (zero length mismatch!)
        fpr_if, tpr_if, _ = roc_curve(y_es, -if_sc_es)
        fpr_ez, tpr_ez, _ = roc_curve(y_es, ez_es)
        fpr_z, tpr_z, _ = roc_curve(y_es, z_es)
        fig_r, ax_r = plt.subplots(figsize=(8, 4.5))
        ax_r.plot(fpr_ez, tpr_ez, label=f"Adaptive EWMA-Z (AUC={auc(fpr_ez, tpr_ez):.3f})", linewidth=2)
        ax_r.plot(fpr_if, tpr_if, label=f"Isolation Forest (AUC={auc(fpr_if, tpr_if):.3f})", linewidth=2)
        ax_r.plot(fpr_z, tpr_z, label=f"Z-Score (AUC={auc(fpr_z, tpr_z):.3f})", linewidth=2)
        ax_r.plot([0, 1], [0, 1], "k--", alpha=0.4)
        ax_r.set_xlabel("False Positive Rate")
        ax_r.set_ylabel("True Positive Rate")
        ax_r.set_title("ROC Curves — Unseen Multi-Fault Eval Suite")
        ax_r.legend()
        ax_r.grid(True, alpha=0.3)
        st.pyplot(fig_r)
        plt.close(fig_r)
    elif eval_summary.get("datasets", {}).get("eval_suite"):
        st.subheader("Unseen Multi-Fault + Live Hardware Eval Suite (Summary)")
        st.dataframe(pd.DataFrame.from_dict(eval_summary["datasets"]["eval_suite"], orient="index").reset_index().rename(columns={"index": "Detector"}), hide_index=True, width='stretch')

    if pilot_df is not None and annotations is not None:
        st.divider()
        st.subheader("Verified Pilot Evaluation")
        p_clean = pilot_df.dropna(subset=feature_cols).copy()
        p_clean["label"] = 0
        for _, ann in annotations.iterrows():
            m = (p_clean["timestamp"] >= ann["start_time"]) & (p_clean["timestamp"] <= ann["end_time"])
            p_clean.loc[m, "label"] = 1
        y_p = p_clean["label"].to_numpy(dtype=int)
        if_sc_p = iso.decision_function(scaler.transform(p_clean[feature_cols]))
        if_p = apply_gated_persistence(if_sc_p < iforest_threshold, p_clean["session_id"].to_numpy(), features_df=p_clean).astype(int)
        ez_p = (compute_adaptive_ewma_z(p_clean, ewma_temp_std, ewma_hum_std) > ewma_zscore_threshold).astype(int)
        hyb_p = (if_p | ez_p).astype(int)

        prows = []
        for name, pr in [("Hybrid (IF + EWMA-Z)", hyb_p), ("Adaptive EWMA-Z", ez_p), ("Isolation Forest", if_p)]:
            cm = confusion_matrix(y_p, pr, labels=[0, 1])
            p, r, f1, _ = precision_recall_fscore_support(y_p, pr, average="binary", zero_division=0)
            prows.append({"Detector": name, "Precision": f"{p:.3f}", "Recall": f"{r:.3f}", "F1": f"{f1:.3f}", "FP": int(cm[0, 1]), "FN": int(cm[1, 0])})
        st.dataframe(pd.DataFrame(prows), hide_index=True, width='stretch')
    elif eval_summary.get("datasets", {}).get("pilot"):
        st.divider()
        st.subheader("Verified Pilot Evaluation (Summary)")
        st.dataframe(pd.DataFrame.from_dict(eval_summary["datasets"]["pilot"], orient="index").reset_index().rename(columns={"index": "Detector"}), hide_index=True, width='stretch')

    if eval_summary.get("external_benchmarks"):
        st.divider()
        st.subheader("External Public Benchmarks (Strictly Isolated Calibration)")
        for bname, binfo in eval_summary["external_benchmarks"].items():
            st.markdown(f"**{bname}** — {binfo.get('source', '')}")
            st.dataframe(pd.DataFrame.from_dict(binfo["models"], orient="index").reset_index().rename(columns={"index": "Detector"}), hide_index=True, width='stretch')


with tab5:
    st.header("Data Manager & Pipeline Actions")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Raw CSVs (`data/raw/`)")
        for f in sorted((PROJECT_ROOT / "data" / "raw").glob("*.csv")):
            df_f = load_raw_normal(f) if f.name == "normal_data.csv" else pd.read_csv(f)
            st.write(f"**{f.name}** — {len(df_f):,} rows")
    with c2:
        st.subheader("Processed CSVs (`data/processed/`)")
        for f in sorted((PROJECT_ROOT / "data" / "processed").glob("*.csv")):
            df_f = pd.read_csv(f)
            st.write(f"**{f.name}** — {len(df_f):,} rows")

    st.divider()
    st.subheader("Export Feature Matrices")
    d1, d2, d3 = st.columns(3)
    with d1:
        if ref_data.get("normal") is not None:
            st.download_button("Download Normal Features", ref_data["normal"].to_csv(index=False), "normal_features_full.csv", "text/csv", width='stretch')
    with d2:
        if ref_data.get("pilot") is not None:
            st.download_button("Download Pilot Features", ref_data["pilot"].to_csv(index=False), "pilot_features_full.csv", "text/csv", width='stretch')
    with d3:
        if ref_data.get("eval_suite") is not None:
            st.download_button("Download Eval Suite", ref_data["eval_suite"].to_csv(index=False), "eval_suite_features_full.csv", "text/csv", width='stretch')

    st.divider()
    st.subheader("Execute Pipeline Steps")
    b1, b2, b3, b4 = st.columns(4)

    def run_step(label: str, script_rel: str) -> None:
        with st.spinner(f"Running {script_rel}..."):
            res = subprocess.run([sys.executable, str(PROJECT_ROOT / script_rel)], cwd=str(PROJECT_ROOT), capture_output=True, text=True)
        if res.returncode == 0:
            st.cache_data.clear()
            st.cache_resource.clear()
            st.success(f"{label} succeeded!")
            if res.stdout:
                st.code(res.stdout[-1500:], language="text")
        else:
            st.error(f"{label} failed (exit {res.returncode}): {res.stderr}")

    with b1:
        if st.button("1. Run Cleaning", width='stretch'):
            run_step("Preprocessing", "preprocess/clean_datasets.py")
    with b2:
        if st.button("2. Build Features", width='stretch'):
            run_step("Feature Build", "features/build_features_v2.py")
    with b3:
        if st.button("3. Retrain Models", width='stretch'):
            run_step("Model Training", "train/train_models.py")
    with b4:
        if st.button("4. Regenerate Plots", width='stretch'):
            run_step("EDA Plots", "eda/generate_plots_v2.py")


with tab6:
    st.header("System & Hardware Settings")
    st.subheader("ESP32 + DHT11 Hardware Status")
    st.success("Firmware `firmware/esp32_dht11/esp32_dht11.ino` verified live on **COM19 @ 115200 baud** (`temperature,humidity` every 2000ms).")
    st.json(
        {
            "sensor": "DHT11",
            "mcu": "ESP32 DevKit",
            "gpio": 4,
            "default_port": config.serial_port,
            "baudrate": config.baudrate,
            "sampling_interval_ms": config.sampling_interval_ms,
        }
    )
    st.subheader("Active `thresholds.json`")
    st.json(thresholds)

st.divider()
st.caption("Admin Dashboard | IoT Anomaly Detection System")
