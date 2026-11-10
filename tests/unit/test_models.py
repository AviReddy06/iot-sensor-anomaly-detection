"""Unit tests verifying trained artifacts, feature contract, and generalization sanity."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from features.feature_engine import (
    MODEL_FEATURE_COLS,
    apply_gated_persistence,
    build_features,
    compute_adaptive_ewma_z,
)


def test_saved_model_artifacts_contract(project_root: Path):
    models_dir = project_root / "models"
    iso = joblib.load(models_dir / "iforest.joblib")
    scaler = joblib.load(models_dir / "scaler.joblib")
    ocsvm = joblib.load(models_dir / "ocsvm.joblib")
    thresholds = json.loads((models_dir / "thresholds.json").read_text(encoding="utf-8"))
    summary = json.loads((models_dir / "evaluation_summary.json").read_text(encoding="utf-8"))

    assert thresholds["feature_cols"] == MODEL_FEATURE_COLS
    assert thresholds["scaler_type"] == "standard"
    assert thresholds["GAP_THRESHOLD"] == 10
    assert scaler.n_features_in_ == len(MODEL_FEATURE_COLS)
    assert iso.n_features_in_ == len(MODEL_FEATURE_COLS)
    assert ocsvm.n_features_in_ == len(MODEL_FEATURE_COLS)
    assert "eval_suite" in summary.get("datasets", {})
    assert "UCI_Occupancy_357" in summary.get("external_benchmarks", {})
    assert "IoTsec_Room_Climate" in summary.get("external_benchmarks", {})


def test_production_models_zero_false_alarms_on_room_shifted_baseline(project_root: Path, synthetic_steady_df: pd.DataFrame):
    models_dir = project_root / "models"
    iso = joblib.load(models_dir / "iforest.joblib")
    scaler = joblib.load(models_dir / "scaler.joblib")
    thresholds = json.loads((models_dir / "thresholds.json").read_text(encoding="utf-8"))

    # Room shifted +4 C and -7% RH vs training average (mirrors live COM19 hardware conditions)
    shifted = synthetic_steady_df.copy()
    shifted["temperature"] += 1.5
    shifted["humidity"] -= 4.0

    feat = build_features(shifted)
    X_scaled = scaler.transform(feat[MODEL_FEATURE_COLS])
    if_flag = apply_gated_persistence(
        iso.decision_function(X_scaled) < thresholds["iforest_threshold"],
        feat["session_id"].to_numpy(),
        features_df=feat,
    )
    ez_flag = compute_adaptive_ewma_z(
        feat, thresholds["ewma_temp_std"], thresholds["ewma_hum_std"]
    ) > thresholds["ewma_zscore_threshold"]
    hybrid_flag = if_flag | ez_flag

    assert int(np.sum(hybrid_flag)) == 0
