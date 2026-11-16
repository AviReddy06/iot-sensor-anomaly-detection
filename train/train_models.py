#!/usr/bin/env python3
"""
train/train_models.py
Train anomaly detection models strictly on cleaned normal baseline features,
calibrate sensitivity thresholds, compare multi-model performance, and serialize artifacts.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    precision_recall_fscore_support,
    roc_auc_score,
)
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import RobustScaler, StandardScaler
from sklearn.svm import OneClassSVM

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import config
from features.feature_engine import (
    MODEL_FEATURE_COLS,
    apply_gated_persistence,
    compute_adaptive_ewma_z,
)


def extract_true_events(y_true: np.ndarray) -> List[Tuple[int, int]]:
    """Return contiguous inclusive index intervals (start, end) where y_true == 1."""
    events: List[Tuple[int, int]] = []
    in_event = False
    start = 0
    for i, val in enumerate(y_true):
        if val == 1 and not in_event:
            in_event = True
            start = i
        elif val == 0 and in_event:
            in_event = False
            events.append((start, i - 1))
    if in_event:
        events.append((start, len(y_true) - 1))
    return events


def compute_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    continuous_score: np.ndarray,
) -> Dict[str, Any]:
    """Compute row-level and event-level classification metrics."""
    y_true_arr = np.asarray(y_true, dtype=int)
    y_pred_arr = np.asarray(y_pred, dtype=int)
    cm = confusion_matrix(y_true_arr, y_pred_arr, labels=[0, 1])
    tn, fp, fn, tp = (int(cm[0, 0]), int(cm[0, 1]), int(cm[1, 0]), int(cm[1, 1]))
    prec, rec, f1, _ = precision_recall_fscore_support(
        y_true_arr, y_pred_arr, average="binary", zero_division=0
    )

    try:
        pr_auc = float(average_precision_score(y_true_arr, continuous_score))
        roc_auc = float(roc_auc_score(y_true_arr, continuous_score))
    except ValueError:
        pr_auc = 0.0
        roc_auc = 0.0

    # Event-level evaluation
    true_events = extract_true_events(y_true_arr)
    events_caught = sum(1 for s, e in true_events if y_pred_arr[s : e + 1].any())

    # Count false-alarm episodes in y_true == 0 regions (merging gaps <= 5 rows)
    fa_episodes = 0
    in_fa = False
    gap_count = 0
    for yt, yp in zip(y_true_arr, y_pred_arr):
        if yt == 0 and yp == 1:
            if not in_fa:
                fa_episodes += 1
                in_fa = True
            gap_count = 0
        else:
            if in_fa:
                gap_count += 1
                if gap_count > 5 or yt == 1:
                    in_fa = False

    return {
        "rows": int(len(y_true_arr)),
        "positives": int((y_true_arr == 1).sum()),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": round(float(prec), 4),
        "recall": round(float(rec), 4),
        "f1": round(float(f1), 4),
        "pr_auc": round(pr_auc, 4),
        "roc_auc": round(roc_auc, 4),
        "events_total": int(len(true_events)),
        "events_caught": int(events_caught),
        "event_recall": round(float(events_caught / len(true_events)), 4) if true_events else 1.0,
        "false_alarm_episodes": int(fa_episodes),
    }


def evaluate_all_models_on_df(
    df: pd.DataFrame,
    y_true: np.ndarray,
    scaler: Any,
    iso: IsolationForest,
    ocsvm: OneClassSVM,
    lof: LocalOutlierFactor,
    thresholds: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """Run standardized comparison across all unsupervised detectors."""
    X_scaled = scaler.transform(df[MODEL_FEATURE_COLS])
    sess = df["session_id"].to_numpy()

    # 1. Raw Z-Score Baseline
    z_temp = np.abs((df["temperature"] - thresholds["normal_temp_mean"]) / thresholds["normal_temp_std"])
    z_hum = np.abs((df["humidity"] - thresholds["normal_hum_mean"]) / thresholds["normal_hum_std"])
    z_score_val = np.maximum(z_temp.to_numpy(dtype=float), z_hum.to_numpy(dtype=float))
    z_flag = z_score_val > thresholds["zscore_threshold"]

    # 2. Adaptive Gated EWMA-Z
    ewma_z = compute_adaptive_ewma_z(df, thresholds["ewma_temp_std"], thresholds["ewma_hum_std"])
    ewma_flag = ewma_z > thresholds["ewma_zscore_threshold"]

    # 3. Isolation Forest (raw & gated persistence)
    if_scores = iso.decision_function(X_scaled)
    if_raw_flag = if_scores < thresholds["iforest_threshold"]
    if_pers_flag = apply_gated_persistence(if_raw_flag, sess, features_df=df)

    # 4. Hybrid Ensemble (IF with Persistence OR Adaptive EWMA-Z)
    hybrid_flag = if_pers_flag | ewma_flag
    hybrid_cont = np.maximum(
        np.clip((-if_scores + thresholds["iforest_threshold"]) * 15.0 + 3.5, 0.0, 20.0),
        ewma_z,
    )

    # 5. One-Class SVM
    svm_scores = ocsvm.decision_function(X_scaled)
    svm_flag = svm_scores < thresholds["ocsvm_threshold"]

    # 6. Local Outlier Factor (novelty=True)
    lof_scores = lof.decision_function(X_scaled)
    lof_flag = lof_scores < thresholds["lof_threshold"]

    return {
        "Z-Score Baseline": compute_metrics(y_true, z_flag, z_score_val),
        "Adaptive EWMA-Z": compute_metrics(y_true, ewma_flag, ewma_z),
        "Isolation Forest (Raw)": compute_metrics(y_true, if_raw_flag, -if_scores),
        "Isolation Forest": compute_metrics(y_true, if_pers_flag, -if_scores),
        "Hybrid (IF + EWMA-Z)": compute_metrics(y_true, hybrid_flag, hybrid_cont),
        "One-Class SVM": compute_metrics(y_true, svm_flag, -svm_scores),
        "LOF (Novelty)": compute_metrics(y_true, lof_flag, -lof_scores),
    }


def train_and_evaluate() -> Dict[str, Any]:
    """Train production models on clean normal data and save artifacts + benchmarks."""
    feat_dir = config.features_dir
    proc_dir = config.processed_dir
    models_dir = config.model_dir
    models_dir.mkdir(parents=True, exist_ok=True)

    normal_full = pd.read_csv(feat_dir / "normal_features_full.csv")
    normal_full["timestamp"] = pd.to_datetime(normal_full["timestamp"])
    X_normal = normal_full[MODEL_FEATURE_COLS].copy()

    scaler_type = str(config.get("features.scaler_type", "standard")).lower()
    scaler = RobustScaler() if scaler_type == "robust" else StandardScaler()
    X_normal_scaled = scaler.fit_transform(X_normal)

    n_estimators = int(config.get("model.n_estimators", 200))
    max_samples = config.get("model.max_samples", "auto")
    contamination = config.contamination
    random_state = int(config.get("model.random_state", 42))
    n_jobs = int(config.get("model.n_jobs", -1))

    print(f"Training IsolationForest on {len(X_normal)} clean normal rows x {len(MODEL_FEATURE_COLS)} features (scaler={scaler_type})...")
    iso = IsolationForest(
        n_estimators=n_estimators,
        max_samples=max_samples,
        contamination=contamination,
        random_state=random_state,
        n_jobs=n_jobs,
    )
    iso.fit(X_normal_scaled)
    normal_scores = iso.decision_function(X_normal_scaled)

    # Calibrate sensitivity thresholds strictly on normal training score percentiles
    default_pct = float(config.get("model.threshold_percentile", 0.25))
    iforest_threshold = float(np.percentile(normal_scores, default_pct))
    sensitivity_thresholds = {
        "Low (0.1th %ile)": float(np.percentile(normal_scores, 0.1)),
        "Medium (0.25th %ile)": float(np.percentile(normal_scores, 0.25)),
        "High (1.0th %ile)": float(np.percentile(normal_scores, 1.0)),
    }

    # Fit comparison detectors cleanly on evenly strided subsample (<= 6000 rows)
    sub_idx = np.linspace(0, len(X_normal_scaled) - 1, min(6000, len(X_normal_scaled)), dtype=int)
    ocsvm = OneClassSVM(kernel="rbf", nu=0.005, gamma="scale").fit(X_normal_scaled[sub_idx])
    ocsvm_scores_norm = ocsvm.decision_function(X_normal_scaled)
    ocsvm_threshold = float(np.percentile(ocsvm_scores_norm, 0.5))

    lof = LocalOutlierFactor(n_neighbors=20, novelty=True, n_jobs=n_jobs).fit(X_normal_scaled[sub_idx])
    lof_scores_norm = lof.decision_function(X_normal_scaled)
    lof_threshold = float(np.percentile(lof_scores_norm, 0.5))

    thresholds: Dict[str, Any] = {
        "model_type": "isolation_forest",
        "scaler_type": scaler_type,
        "feature_cols": list(MODEL_FEATURE_COLS),
        "iforest_threshold": iforest_threshold,
        "threshold_percentile": default_pct,
        "sensitivity_thresholds": sensitivity_thresholds,
        "zscore_threshold": float(config.get("detection.zscore_threshold", 3.0)),
        "ewma_zscore_threshold": float(config.get("detection.ewma_zscore_threshold", 3.5)),
        "ocsvm_threshold": ocsvm_threshold,
        "lof_threshold": lof_threshold,
        "normal_temp_mean": float(normal_full["temperature"].mean()),
        "normal_temp_std": float(normal_full["temperature"].std()),
        "normal_hum_mean": float(normal_full["humidity"].mean()),
        "normal_hum_std": float(normal_full["humidity"].std()),
        "ewma_temp_std": float(normal_full["temp_ewma_residual"].std()),
        "ewma_hum_std": float(normal_full["hum_ewma_residual"].std()),
        "GAP_THRESHOLD": int(config.gap_threshold_sec),
        "ROLL_MIN": int(config.roll_min),
        "short_window_sec": int(config.short_window_sec),
        "long_window_sec": int(config.long_window_sec),
        "ewma_halflife_sec": int(config.ewma_halflife_sec),
        "ewma_macro_gap_sec": int(config.ewma_macro_gap_sec),
        "persistence_window": int(config.get("detection.persistence_window", 5)),
        "persistence_min_hits": int(config.get("detection.persistence_min_hits", 3)),
        "alert_cooldown_sec": int(config.get("detection.alert_cooldown_sec", 30)),
        "training_rows": int(len(normal_full)),
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

    # Save primary artifacts
    joblib.dump(iso, models_dir / "iforest.joblib")
    joblib.dump(scaler, models_dir / "scaler.joblib")
    joblib.dump(ocsvm, models_dir / "ocsvm.joblib")
    with open(models_dir / "thresholds.json", "w", encoding="utf-8") as f:
        json.dump(thresholds, f, indent=2)

    # Evaluate across datasets
    eval_summary: Dict[str, Any] = {
        "generated_at": thresholds["trained_at"],
        "training_summary": {
            "rows": int(len(normal_full)),
            "sessions": int(normal_full["session_id"].nunique()),
            "temp_mean": round(thresholds["normal_temp_mean"], 2),
            "temp_std": round(thresholds["normal_temp_std"], 3),
            "hum_mean": round(thresholds["normal_hum_mean"], 2),
            "hum_std": round(thresholds["normal_hum_std"], 3),
            "ewma_temp_std": round(thresholds["ewma_temp_std"], 3),
            "ewma_hum_std": round(thresholds["ewma_hum_std"], 3),
        },
        "datasets": {},
    }

    # 1. Legacy test.csv
    test_path = feat_dir / "test_features_full.csv"
    if test_path.exists():
        test_df = pd.read_csv(test_path)
        eval_summary["datasets"]["test"] = evaluate_all_models_on_df(
            test_df, test_df["label"].to_numpy(dtype=int), scaler, iso, ocsvm, lof, thresholds
        )

    # 2. Pilot dataset with verified event annotations
    pilot_path = feat_dir / "pilot_features_full.csv"
    ann_path = proc_dir / "pilot_event_annotations.csv"
    if pilot_path.exists() and ann_path.exists():
        pilot_df = pd.read_csv(pilot_path)
        pilot_df["timestamp"] = pd.to_datetime(pilot_df["timestamp"])
        ann = pd.read_csv(ann_path)
        y_pilot = np.zeros(len(pilot_df), dtype=int)
        for _, row in ann.iterrows():
            s_t = pd.to_datetime(row["start_time"])
            e_t = pd.to_datetime(row["end_time"])
            y_pilot[(pilot_df["timestamp"] >= s_t) & (pilot_df["timestamp"] <= e_t)] = 1
        eval_summary["datasets"]["pilot"] = evaluate_all_models_on_df(
            pilot_df, y_pilot, scaler, iso, ocsvm, lof, thresholds
        )

    # 3. Unseen multi-fault + live hardware evaluation suite
    suite_path = feat_dir / "eval_suite_features_full.csv"
    if suite_path.exists():
        suite_df = pd.read_csv(suite_path)
        suite_res = evaluate_all_models_on_df(
            suite_df, suite_df["label"].to_numpy(dtype=int), scaler, iso, ocsvm, lof, thresholds
        )
        # Add per-fault & live normal breakdown for Isolation Forest & Hybrid
        X_s = scaler.transform(suite_df[MODEL_FEATURE_COLS])
        if_raw = iso.decision_function(X_s) < thresholds["iforest_threshold"]
        if_p = apply_gated_persistence(if_raw, suite_df["session_id"].to_numpy(), features_df=suite_df)
        ez_p = compute_adaptive_ewma_z(suite_df, thresholds["ewma_temp_std"], thresholds["ewma_hum_std"]) > thresholds["ewma_zscore_threshold"]
        hyb_p = if_p | ez_p
        breakdown: Dict[str, Dict[str, Any]] = {}
        if "fault_type" in suite_df.columns:
            for ft, grp in suite_df.groupby("fault_type"):
                idx = grp.index.to_numpy()
                is_anom = int(grp["label"].iloc[0]) == 1
                breakdown[str(ft)] = {
                    "rows": int(len(idx)),
                    "is_anomaly": bool(is_anom),
                    "if_recall" if is_anom else "if_fp": round(float(if_p[idx].mean()), 4) if is_anom else int(if_p[idx].sum()),
                    "ewma_z_recall" if is_anom else "ewma_z_fp": round(float(ez_p[idx].mean()), 4) if is_anom else int(ez_p[idx].sum()),
                    "hybrid_recall" if is_anom else "hybrid_fp": round(float(hyb_p[idx].mean()), 4) if is_anom else int(hyb_p[idx].sum()),
                }
        eval_summary["datasets"]["eval_suite"] = suite_res
        eval_summary["eval_suite_breakdown"] = breakdown

    # Preserve existing external benchmark section if already present
    summary_path = models_dir / "evaluation_summary.json"
    if summary_path.exists():
        try:
            existing = json.loads(summary_path.read_text(encoding="utf-8"))
            if "external_benchmarks" in existing:
                eval_summary["external_benchmarks"] = existing["external_benchmarks"]
        except Exception:
            pass

    summary_path.write_text(json.dumps(eval_summary, indent=2), encoding="utf-8")

    # Print clean summary table
    for ds_name, ds_metrics in eval_summary["datasets"].items():
        print(f"\n=== {ds_name.upper()} BENCHMARK ===")
        for model_name, m in ds_metrics.items():
            print(
                f"  {model_name:24s} | P={m['precision']:.3f} R={m['recall']:.3f} F1={m['f1']:.3f} "
                f"| PR={m['pr_auc']:.3f} ROC={m['roc_auc']:.3f} | FP={m['fp']:3d} FN={m['fn']:3d} "
                f"| Ev={m['events_caught']}/{m['events_total']}"
            )
    if "eval_suite_breakdown" in eval_summary:
        print("\n=== EVAL SUITE CATEGORY BREAKDOWN ===")
        for ft, info in eval_summary["eval_suite_breakdown"].items():
            print(f"  {ft:22s}: {info}")

    print(f"\nSaved artifacts cleanly to {models_dir}/")
    return eval_summary


if __name__ == "__main__":
    train_and_evaluate()
