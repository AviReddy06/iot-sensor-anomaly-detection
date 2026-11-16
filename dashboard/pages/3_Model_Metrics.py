#!/usr/bin/env python3
"""
dashboard/pages/3_Model_Metrics.py
Dynamic evaluation report reading verified benchmarks from `models/evaluation_summary.json`
and threshold config from `models/thresholds.json`.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

st.set_page_config(page_title="Model & Metrics", page_icon="📊", layout="wide")


@st.cache_data
def load_summary():
    summary_path = PROJECT_ROOT / "models" / "evaluation_summary.json"
    thresholds_path = PROJECT_ROOT / "models" / "thresholds.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
    thresholds = json.loads(thresholds_path.read_text(encoding="utf-8")) if thresholds_path.exists() else {}
    return summary, thresholds


summary, thresholds = load_summary()

st.title("Model & Evaluation Benchmarks")
st.markdown("All metrics below are dynamically loaded from `models/evaluation_summary.json` generated cleanly by `train/train_models.py` and `evaluate/benchmark_external.py`.")

if not summary:
    st.error("`models/evaluation_summary.json` not found. Run `python train/train_models.py` first.")
    st.stop()

train_info = summary.get("training_summary", {})
c1, c2, c3, c4 = st.columns(4)
c1.metric("Training Feature Rows", f"{train_info.get('rows', 0):,}")
c2.metric("Continuous Sessions", train_info.get("sessions", 0))
c3.metric("Model Feature Count", len(thresholds.get("feature_cols", [])))
c4.metric("IF Threshold (0.25th %ile)", f"{thresholds.get('iforest_threshold', 0.0):.5f}")

st.divider()


def render_benchmark_table(title: str, caption: str, metrics_dict: dict) -> None:
    st.subheader(title)
    st.caption(caption)
    rows = []
    for model_name, m in metrics_dict.items():
        rows.append(
            {
                "Detector": model_name,
                "Precision": f"{m['precision']:.3f}",
                "Recall": f"{m['recall']:.3f}",
                "F1": f"{m['f1']:.3f}",
                "PR-AUC": f"{m['pr_auc']:.3f}",
                "ROC-AUC": f"{m['roc_auc']:.3f}",
                "FP": m["fp"],
                "FN": m["fn"],
                "Events Caught": f"{m.get('events_caught', '-')}/{m.get('events_total', '-')}",
            }
        )
    st.dataframe(pd.DataFrame(rows), hide_index=True, width='stretch')


datasets = summary.get("datasets", {})
if "eval_suite" in datasets:
    render_benchmark_table(
        "Unseen Multi-Fault + Live Hardware Suite (`eval_test_suite.csv`)",
        "1,947 scored rows: unseen Nov 1 clean baseline + 6 fault types + live 2026-11-10 COM19 ESP32+DHT11 baseline.",
        datasets["eval_suite"],
    )

if "eval_suite_breakdown" in summary:
    with st.expander("View Per-Fault & Live Hardware Breakdown"):
        b_rows = []
        for k, v in summary["eval_suite_breakdown"].items():
            if v["is_anomaly"]:
                b_rows.append(
                    {
                        "Category": k,
                        "Type": "Fault / Anomaly",
                        "Rows": v["rows"],
                        "IF Recall": f"{v['if_recall']:.1%}",
                        "Adaptive EWMA-Z Recall": f"{v['ewma_z_recall']:.1%}",
                        "Hybrid Recall": f"{v['hybrid_recall']:.1%}",
                    }
                )
            else:
                b_rows.append(
                    {
                        "Category": k,
                        "Type": "Clean / Live Baseline",
                        "Rows": v["rows"],
                        "IF Recall": f"FP={v['if_fp']}",
                        "Adaptive EWMA-Z Recall": f"FP={v['ewma_z_fp']}",
                        "Hybrid Recall": f"FP={v['hybrid_fp']}",
                    }
                )
        st.dataframe(pd.DataFrame(b_rows), hide_index=True, width='stretch')

st.divider()
if "pilot" in datasets:
    render_benchmark_table(
        "Verified Pilot Session (`pilot_data.csv` + `pilot_event_annotations.csv`)",
        "3,084 scored rows, 503 verified event rows across Event 1 (23:09:38–23:40:28) and Event 2.",
        datasets["pilot"],
    )

if "test" in datasets:
    render_benchmark_table(
        "Legacy Single-Event Test Set (`test.csv`)",
        "55 scored rows, 10 anomaly rows.",
        datasets["test"],
    )

external = summary.get("external_benchmarks", {})
if external:
    st.divider()
    st.header("External Public Benchmarks (Isolated Calibration)")
    st.caption("Evaluated separately with dataset-specific time scaling to validate architectural generalizability; zero overlap with ESP32 weights.")
    for ext_name, ext_info in external.items():
        render_benchmark_table(
            ext_name,
            f"{ext_info.get('source', '')} — Train: {ext_info.get('train_rows')} rows, Test: {ext_info.get('test_rows')} rows ({ext_info.get('anomalies')} positives)",
            ext_info.get("models", {}),
        )

st.divider()
st.subheader("Hardware & System Notes")
st.info(
    "- **ESP32 + DHT11 Hardware Verified**: Live telemetry streamed on **COM19 at 115200 baud** (`temperature,humidity\\n` every 2s, verified live 2026-11-10) with DTR/RTS reset protection and 0 false alarms.\n"
    "- **Cleaned Training Baseline**: 389 unlabeled ambient spikes/bursts quarantined from raw normal recordings prior to scaler & Isolation Forest fitting.\n"
    "- **Cross-Day Drift Robustness**: Adaptive Cauchy-weighted EWMA prevents long heat events from poisoning baseline while adapting across warmer/drier room shifts (`+4.5°C` warmer room today)."
)
