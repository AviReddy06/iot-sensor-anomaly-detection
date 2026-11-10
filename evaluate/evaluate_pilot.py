#!/usr/bin/env python3
"""
evaluate/evaluate_pilot.py
Evaluate saved production models on the pilot dataset with verified event annotations.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Dict

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, confusion_matrix, precision_recall_fscore_support, roc_auc_score

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import config
from features.feature_engine import (
    MODEL_FEATURE_COLS,
    apply_gated_persistence,
    compute_adaptive_ewma_z,
)


def evaluate_pilot() -> Dict[str, dict]:
    """Run standardized evaluation on pilot_features_full.csv + pilot_event_annotations.csv."""
    pilot = pd.read_csv(config.features_dir / "pilot_features_full.csv")
    pilot["timestamp"] = pd.to_datetime(pilot["timestamp"])
    pilot = pilot.sort_values("timestamp", kind="stable").reset_index(drop=True)

    annotations = pd.read_csv(config.processed_dir / "pilot_event_annotations.csv")
    annotations["start_time"] = pd.to_datetime(annotations["start_time"])
    annotations["end_time"] = pd.to_datetime(annotations["end_time"])

    iso = joblib.load(config.model_dir / "iforest.joblib")
    scaler = joblib.load(config.model_dir / "scaler.joblib")
    with open(config.model_dir / "thresholds.json", "r", encoding="utf-8") as f:
        thresholds = json.load(f)

    feature_cols = thresholds.get("feature_cols", MODEL_FEATURE_COLS)
    labels = np.zeros(len(pilot), dtype=int)
    for _, row in annotations.iterrows():
        mask = (pilot["timestamp"] >= row["start_time"]) & (pilot["timestamp"] <= row["end_time"])
        labels[mask] = 1

    print(f"Loaded pilot: {len(pilot)} rows | Positives: {int(labels.sum())} | Events: {len(annotations)}")

    X_scaled = scaler.transform(pilot[feature_cols])
    if_scores = iso.decision_function(X_scaled)
    if_raw = if_scores < thresholds["iforest_threshold"]
    if_flag = apply_gated_persistence(if_raw, pilot["session_id"].to_numpy(), features_df=pilot)

    ewma_z = compute_adaptive_ewma_z(pilot, thresholds["ewma_temp_std"], thresholds["ewma_hum_std"])
    ewma_flag = ewma_z > thresholds["ewma_zscore_threshold"]

    z_t = np.abs((pilot["temperature"] - thresholds["normal_temp_mean"]) / thresholds["normal_temp_std"])
    z_h = np.abs((pilot["humidity"] - thresholds["normal_hum_mean"]) / thresholds["normal_hum_std"])
    z_score_val = np.maximum(z_t.to_numpy(dtype=float), z_h.to_numpy(dtype=float))
    z_flag = z_score_val > thresholds["zscore_threshold"]

    hybrid_flag = if_flag | ewma_flag

    results: Dict[str, dict] = {}
    print("\n=== PILOT EVALUATION RESULTS ===")
    for name, pred, cont in [
        ("Z-Score Baseline", z_flag, z_score_val),
        ("Adaptive EWMA-Z", ewma_flag, ewma_z),
        ("Isolation Forest", if_flag, -if_scores),
        ("Hybrid (IF + EWMA-Z)", hybrid_flag, np.maximum(ewma_z, np.clip((-if_scores + thresholds["iforest_threshold"]) * 15.0 + 3.5, 0, 20))),
    ]:
        cm = confusion_matrix(labels, pred, labels=[0, 1])
        p, r, f1, _ = precision_recall_fscore_support(labels, pred, average="binary", zero_division=0)
        pr = average_precision_score(labels, cont)
        roc = roc_auc_score(labels, cont)
        print(
            f"  {name:22s} | TN={cm[0,0]:4d} FP={cm[0,1]:3d} FN={cm[1,0]:3d} TP={cm[1,1]:3d} "
            f"| P={p:.3f} R={r:.3f} F1={f1:.3f} PR-AUC={pr:.3f} ROC-AUC={roc:.3f}"
        )
        results[name] = {"precision": float(p), "recall": float(r), "f1": float(f1), "fp": int(cm[0, 1]), "fn": int(cm[1, 0])}

    print("\n=== PER-EVENT RECALL ===")
    for _, row in annotations.iterrows():
        mask = (pilot["timestamp"] >= row["start_time"]) & (pilot["timestamp"] <= row["end_time"])
        idx = np.where(mask)[0]
        if len(idx) > 0:
            print(
                f"  Event {int(row['event_id'])} ({row['start_time']} -> {row['end_time']}, {len(idx)} rows): "
                f"Z={int(z_flag[idx].sum())}/{len(idx)} | IF={int(if_flag[idx].sum())}/{len(idx)} "
                f"| EWMA-Z={int(ewma_flag[idx].sum())}/{len(idx)} | Hybrid={int(hybrid_flag[idx].sum())}/{len(idx)}"
            )

    return results


if __name__ == "__main__":
    evaluate_pilot()
