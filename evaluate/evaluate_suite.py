#!/usr/bin/env python3
"""
evaluate/evaluate_suite.py
Evaluate saved production models on the unseen multi-fault + live ESP32/DHT11 evaluation suite.
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


def evaluate_suite() -> Dict[str, dict]:
    """Evaluate all detectors on eval_suite_features_full.csv across fault categories and live hardware."""
    suite = pd.read_csv(config.features_dir / "eval_suite_features_full.csv")
    suite["timestamp"] = pd.to_datetime(suite["timestamp"])
    suite = suite.sort_values("timestamp", kind="stable").reset_index(drop=True)

    iso = joblib.load(config.model_dir / "iforest.joblib")
    scaler = joblib.load(config.model_dir / "scaler.joblib")
    with open(config.model_dir / "thresholds.json", "r", encoding="utf-8") as f:
        thresholds = json.load(f)

    feature_cols = thresholds.get("feature_cols", MODEL_FEATURE_COLS)
    y_true = suite["label"].to_numpy(dtype=int)

    X_scaled = scaler.transform(suite[feature_cols])
    if_scores = iso.decision_function(X_scaled)
    if_flag = apply_gated_persistence(
        if_scores < thresholds["iforest_threshold"],
        suite["session_id"].to_numpy(),
        features_df=suite,
    )

    ewma_z = compute_adaptive_ewma_z(suite, thresholds["ewma_temp_std"], thresholds["ewma_hum_std"])
    ewma_flag = ewma_z > thresholds["ewma_zscore_threshold"]

    z_t = np.abs((suite["temperature"] - thresholds["normal_temp_mean"]) / thresholds["normal_temp_std"])
    z_h = np.abs((suite["humidity"] - thresholds["normal_hum_mean"]) / thresholds["normal_hum_std"])
    z_val = np.maximum(z_t.to_numpy(dtype=float), z_h.to_numpy(dtype=float))
    z_flag = z_val > thresholds["zscore_threshold"]

    hybrid_flag = if_flag | ewma_flag

    print(f"Loaded Eval Suite: {len(suite)} rows | Anomalies: {int(y_true.sum())} | Normal/Live: {int((y_true == 0).sum())}")
    results: Dict[str, dict] = {}
    for name, pred, cont in [
        ("Z-Score Baseline", z_flag, z_val),
        ("Adaptive EWMA-Z", ewma_flag, ewma_z),
        ("Isolation Forest", if_flag, -if_scores),
        ("Hybrid (IF + EWMA-Z)", hybrid_flag, np.maximum(ewma_z, np.clip((-if_scores + thresholds["iforest_threshold"]) * 15.0 + 3.5, 0, 20))),
    ]:
        cm = confusion_matrix(y_true, pred, labels=[0, 1])
        p, r, f1, _ = precision_recall_fscore_support(y_true, pred, average="binary", zero_division=0)
        pr = average_precision_score(y_true, cont)
        roc = roc_auc_score(y_true, cont)
        print(
            f"  {name:22s} | TN={cm[0,0]:4d} FP={cm[0,1]:3d} FN={cm[1,0]:3d} TP={cm[1,1]:3d} "
            f"| P={p:.3f} R={r:.3f} F1={f1:.3f} PR-AUC={pr:.3f} ROC-AUC={roc:.3f}"
        )
        results[name] = {"precision": float(p), "recall": float(r), "f1": float(f1), "fp": int(cm[0, 1]), "fn": int(cm[1, 0])}

    if "fault_type" in suite.columns:
        print("\n=== CATEGORY BREAKDOWN (Recall on Faults / False Positives on Normal) ===")
        for ft, grp in suite.groupby("fault_type"):
            idx = grp.index.to_numpy()
            if int(grp["label"].iloc[0]) == 1:
                print(
                    f"  [FAULT] {ft:20s} ({len(idx):2d} rows) -> "
                    f"Z={z_flag[idx].mean():.2f} | EWMA-Z={ewma_flag[idx].mean():.2f} "
                    f"| IF={if_flag[idx].mean():.2f} | Hybrid={hybrid_flag[idx].mean():.2f}"
                )
            else:
                print(
                    f"  [CLEAN] {ft:20s} ({len(idx):4d} rows) -> "
                    f"FP: Z={int(z_flag[idx].sum())} | EWMA-Z={int(ewma_flag[idx].sum())} "
                    f"| IF={int(if_flag[idx].sum())} | Hybrid={int(hybrid_flag[idx].sum())}"
                )

    return results


if __name__ == "__main__":
    evaluate_suite()
