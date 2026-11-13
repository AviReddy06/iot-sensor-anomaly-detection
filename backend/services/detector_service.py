"""
backend/services/detector_service.py
Model inference service loading serialized artifacts and thresholds.
Asserts feature list equality at startup, otherwise refuses to start.
Provides Low/Medium/High sensitivity percentiles (0.5th, 1st, 5th percentiles).
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import joblib
import numpy as np
import pandas as pd
from backend.config import PROJECT_ROOT
from features.feature_engine import (
    MODEL_FEATURE_COLS,
    apply_gated_persistence,
    build_features,
    compute_adaptive_ewma_z,
)


class DetectorService:
    def __init__(self, models_dir: Optional[Path] = None):
        # Step 1: Resolve models directory
        self.models_dir = models_dir or (PROJECT_ROOT / "models")
        self.scaler = None
        self.iso_model = None
        self.thresholds: Dict[str, Any] = {}
        self.active_sensitivity = "Medium"
        self.active_threshold = -0.17680869490601944
        # Step 2: Define sensitivity thresholds (0.5th, 1st, 5th percentiles)
        self.sensitivity_map = {
            "Low": -0.20078272276571404,     # 0.5th percentile
            "Medium": -0.17680869490601944,  # 1.0th percentile
            "High": -0.11362667221756062,    # 5.0th percentile
        }
        self.load_models()

    def load_models(self) -> None:
        # Step 1: Load serialized scaler and Isolation Forest model
        scaler_path = self.models_dir / "scaler.joblib"
        iso_path = self.models_dir / "iforest.joblib"
        thresh_path = self.models_dir / "thresholds.json"

        if not (scaler_path.exists() and iso_path.exists() and thresh_path.exists()):
            raise FileNotFoundError(f"Missing model artifacts in {self.models_dir}")

        self.scaler = joblib.load(scaler_path)
        self.iso_model = joblib.load(iso_path)

        with open(thresh_path, "r", encoding="utf-8") as f:
            self.thresholds = json.load(f)

        # Step 2: Refuse to start if feature list does not equal thresholds.json
        expected_features = list(MODEL_FEATURE_COLS)
        config_features = self.thresholds.get("feature_cols", [])
        if list(expected_features) != list(config_features):
            raise RuntimeError(
                f"Feature list mismatch! Expected {expected_features}, got {config_features}. Refusing to start."
            )

        # Step 3: Set active threshold to Medium by default
        self.set_sensitivity("Medium")

    def set_sensitivity(self, level: str) -> None:
        # Step 1: Update active sensitivity level
        if level not in self.sensitivity_map:
            raise ValueError(f"Unknown sensitivity {level}. Choose from {list(self.sensitivity_map.keys())}")
        self.active_sensitivity = level
        self.active_threshold = self.sensitivity_map[level]

    def evaluate_dataframe(self, df_raw: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        # Step 1: Extract features using feature_engine
        df_feat = build_features(df_raw)
        X = self.scaler.transform(df_feat[MODEL_FEATURE_COLS])
        
        # Step 2: Compute Isolation Forest scores and flags
        if_scores = self.iso_model.decision_function(X)
        raw_flags = if_scores < self.active_threshold
        sess = df_feat["session_id"].to_numpy()
        pers_flags = apply_gated_persistence(raw_flags, sess, features_df=df_feat)

        # Step 3: Compute Adaptive EWMA-Z scores and flags
        temp_std = self.thresholds.get("ewma_temp_std", 0.665)
        hum_std = self.thresholds.get("ewma_hum_std", 3.056)
        ewma_z_thresh = self.thresholds.get("ewma_zscore_threshold", 3.5)
        ewma_z = compute_adaptive_ewma_z(df_feat, temp_std, hum_std)
        ewma_flags = ewma_z > ewma_z_thresh

        # Step 4: Hybrid combination
        hybrid_flags = pers_flags | ewma_flags
        df_feat["anomaly_flag"] = hybrid_flags
        df_feat["if_score"] = if_scores
        df_feat["ewma_z"] = ewma_z

        info = {
            "sensitivity": self.active_sensitivity,
            "threshold": self.active_threshold,
            "ewma_threshold": ewma_z_thresh,
            "total_rows": len(df_feat),
            "flagged_rows": int(hybrid_flags.sum()),
        }
        return df_feat, info

    def evaluate_streaming_sample(
        self,
        buffer_df: pd.DataFrame,
    ) -> Dict[str, Any]:
        # Step 1: If buffer too short (< 2 samples), return normal
        if len(buffer_df) < 2:
            return {
                "flag": False,
                "score": 0.0,
                "ewma_z": 0.0,
                "peak_z": 0.0,
            }

        # Step 2: Evaluate features on recent buffer
        feat_df = build_features(buffer_df)
        if len(feat_df) == 0:
            return {"flag": False, "score": 0.0, "ewma_z": 0.0, "peak_z": 0.0}

        latest_feat = feat_df.iloc[-1:]
        X = self.scaler.transform(latest_feat[MODEL_FEATURE_COLS])
        score = float(self.iso_model.decision_function(X)[0])
        raw_flag = score < self.active_threshold

        # Step 3: Check persistence / excursion
        sess = feat_df["session_id"].to_numpy()
        all_raw_flags = (self.iso_model.decision_function(self.scaler.transform(feat_df[MODEL_FEATURE_COLS])) < self.active_threshold)
        pers_flag = bool(apply_gated_persistence(all_raw_flags, sess, features_df=feat_df)[-1])

        # Step 4: EWMA-Z evaluation
        temp_std = self.thresholds.get("ewma_temp_std", 0.665)
        hum_std = self.thresholds.get("ewma_hum_std", 3.056)
        ewma_z_thresh = self.thresholds.get("ewma_zscore_threshold", 3.5)
        ez_series = compute_adaptive_ewma_z(feat_df, temp_std, hum_std)
        latest_ez = float(ez_series.iloc[-1])
        ewma_flag = latest_ez > ewma_z_thresh

        # Step 5: Peak z calculation relative to normal mean
        norm_t_mean = self.thresholds.get("normal_temp_mean", 25.67)
        norm_t_std = self.thresholds.get("normal_temp_std", 0.83)
        t_val = float(latest_feat["temperature"].iloc[-1])
        z_t = abs(t_val - norm_t_mean) / norm_t_std
        peak_z = max(z_t, latest_ez)

        return {
            "flag": bool(pers_flag or ewma_flag),
            "score": score,
            "ewma_z": latest_ez,
            "peak_z": peak_z,
        }


# Global detector singleton
detector_service = DetectorService()
