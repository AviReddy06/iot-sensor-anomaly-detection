"""
backend/services/inference_service.py
Inference service for unsupervised IoT anomaly detection.
Loads trained models and provides batch and streaming inference using the exact
shared features/feature_engine.py logic to ensure zero training-serving skew.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import config
from features.feature_engine import (
    MODEL_FEATURE_COLS,
    apply_gated_persistence,
    build_features,
    compute_adaptive_ewma_z,
)


class InferenceService:
    def __init__(self, model_dir: Optional[Path] = None):
        self.model_dir = model_dir or (PROJECT_ROOT / "models")
        self.iso = None
        self.scaler = None
        self.thresholds: Dict[str, Any] = {}
        self.evaluation_summary: Dict[str, Any] = {}
        self.active_if_threshold: float = -0.21657
        self.active_ewma_threshold: float = 3.5
        self.active_zscore_threshold: float = 3.0
        self.active_sensitivity: str = "Medium (0.25th %ile)"
        self.is_degraded: bool = False
        self.degraded_reason: Optional[str] = None
        self.model_status: str = "healthy"
        self.load_models()

    def load_models(self) -> None:
        """Load trained models and configuration with graceful degradation."""
        try:
            iso_path = self.model_dir / "iforest.joblib"
            scaler_path = self.model_dir / "scaler.joblib"
            thresholds_path = self.model_dir / "thresholds.json"

            if not (iso_path.exists() and scaler_path.exists()):
                missing = [p.name for p in [iso_path, scaler_path] if not p.exists()]
                self.is_degraded = True
                self.model_status = "degraded"
                self.degraded_reason = f"Missing model artifacts in {self.model_dir}: {', '.join(missing)}"
                return

            self.iso = joblib.load(iso_path)
            self.scaler = joblib.load(scaler_path)

            if thresholds_path.exists():
                with open(thresholds_path, "r", encoding="utf-8") as f:
                    self.thresholds = json.load(f)
                self.active_if_threshold = float(self.thresholds.get("iforest_threshold", -0.21657))
                self.active_ewma_threshold = float(self.thresholds.get("ewma_zscore_threshold", 3.5))
                self.active_zscore_threshold = float(self.thresholds.get("zscore_threshold", 3.0))

            summary_path = self.model_dir / "evaluation_summary.json"
            if summary_path.exists():
                with open(summary_path, "r", encoding="utf-8") as f:
                    self.evaluation_summary = json.load(f)

            self.is_degraded = False
            self.model_status = "healthy"
            self.degraded_reason = None
        except Exception as exc:
            self.is_degraded = True
            self.model_status = "degraded"
            self.degraded_reason = f"Model artifact missing or corrupt in {self.model_dir}: {exc}"

    def get_model_info(self) -> Dict[str, Any]:
        """Return model metadata, thresholds, and configuration."""
        return {
            "model_type": "Isolation Forest (200 trees) + Adaptive Cauchy EWMA-Z (Hybrid)",
            "scaler_type": self.thresholds.get("scaler_type", "StandardScaler"),
            "feature_cols": MODEL_FEATURE_COLS,
            "feature_count": len(MODEL_FEATURE_COLS),
            "training_rows": self.thresholds.get("training_rows", 34374),
            "thresholds": {
                "iforest_threshold": self.active_if_threshold,
                "ewma_zscore_threshold": self.active_ewma_threshold,
                "zscore_threshold": self.active_zscore_threshold,
                "active_sensitivity": self.active_sensitivity,
                "sensitivity_presets": self.thresholds.get("sensitivity_thresholds", {
                    "Low (0.1th %ile)": -0.22858,
                    "Medium (0.25th %ile)": -0.21657,
                    "High (1.0th %ile)": -0.17681,
                }),
                "ewma_temp_std": self.thresholds.get("ewma_temp_std", 0.665),
                "ewma_hum_std": self.thresholds.get("ewma_hum_std", 3.056),
                "normal_temp_mean": self.thresholds.get("normal_temp_mean", 25.67),
                "normal_temp_std": self.thresholds.get("normal_temp_std", 0.83),
                "normal_hum_mean": self.thresholds.get("normal_hum_mean", 61.42),
                "normal_hum_std": self.thresholds.get("normal_hum_std", 4.40),
            },
        }

    def set_thresholds(
        self,
        if_threshold: Optional[float] = None,
        ewma_threshold: Optional[float] = None,
        zscore_threshold: Optional[float] = None,
        sensitivity_label: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update runtime detection thresholds."""
        if if_threshold is not None:
            self.active_if_threshold = float(if_threshold)
        if ewma_threshold is not None:
            self.active_ewma_threshold = float(ewma_threshold)
        if zscore_threshold is not None:
            self.active_zscore_threshold = float(zscore_threshold)
        if sensitivity_label is not None:
            self.active_sensitivity = sensitivity_label

        return {
            "iforest_threshold": self.active_if_threshold,
            "ewma_zscore_threshold": self.active_ewma_threshold,
            "zscore_threshold": self.active_zscore_threshold,
            "active_sensitivity": self.active_sensitivity,
        }

    def process_dataframe(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Process a DataFrame through feature engineering and all 4 detectors:
        Z-Score, Adaptive EWMA-Z, Gated Isolation Forest, and Hybrid.
        """
        if self.is_degraded or self.scaler is None or self.iso is None:
            df_res = df.copy()
            df_res["is_anomaly"] = False
            df_res["if_anomaly"] = False
            df_res["ewma_anomaly"] = False
            df_res["zscore_anomaly"] = False
            df_res["hybrid_score"] = 0.0
            df_res["status"] = "Detector unavailable"
            return df_res, {"degraded": True, "degraded_reason": self.degraded_reason}

        raw_df = df.copy()
        raw_df["timestamp"] = pd.to_datetime(raw_df["timestamp"])
        raw_df = raw_df.sort_values("timestamp", kind="stable").reset_index(drop=True)

        features = build_features(
            raw_df,
            gap_threshold=self.thresholds.get("GAP_THRESHOLD", config.gap_threshold_sec),
            roll_min=self.thresholds.get("ROLL_MIN", config.roll_min),
            short_window_sec=self.thresholds.get("short_window_sec", config.short_window_sec),
            long_window_sec=self.thresholds.get("long_window_sec", config.long_window_sec),
            ewma_halflife_sec=self.thresholds.get("ewma_halflife_sec", config.ewma_halflife_sec),
            ewma_macro_gap_sec=self.thresholds.get("ewma_macro_gap_sec", config.ewma_macro_gap_sec),
        )

        if len(features) == 0:
            return pd.DataFrame(), {}

        feature_cols = self.thresholds.get("feature_cols", MODEL_FEATURE_COLS)
        X_scaled = self.scaler.transform(features[feature_cols])

        # 1. Isolation Forest
        if_scores = self.iso.decision_function(X_scaled)
        if_raw = if_scores < self.active_if_threshold
        if_gated = apply_gated_persistence(
            if_raw,
            features["session_id"].to_numpy(),
            features_df=features,
            window=self.thresholds.get("persistence_window", 5),
            min_hits=self.thresholds.get("persistence_min_hits", 3),
        )

        # 2. Adaptive EWMA-Z
        ewma_temp_std = float(self.thresholds.get("ewma_temp_std", 0.665))
        ewma_hum_std = float(self.thresholds.get("ewma_hum_std", 3.056))
        ewma_z = compute_adaptive_ewma_z(features, ewma_temp_std, ewma_hum_std)
        ewma_flag = ewma_z > self.active_ewma_threshold

        # 3. Z-Score Baseline
        norm_t_mean = float(self.thresholds.get("normal_temp_mean", 25.67))
        norm_t_std = float(self.thresholds.get("normal_temp_std", 0.83))
        norm_h_mean = float(self.thresholds.get("normal_hum_mean", 61.42))
        norm_h_std = float(self.thresholds.get("normal_hum_std", 4.40))
        zt = np.abs((features["temperature"] - norm_t_mean) / norm_t_std)
        zh = np.abs((features["humidity"] - norm_h_mean) / norm_h_std)
        zscore_val = np.maximum(zt.to_numpy(dtype=float), zh.to_numpy(dtype=float))
        zscore_flag = zscore_val > self.active_zscore_threshold

        # 4. Hybrid
        hybrid_flag = if_gated | ewma_flag

        features["iforest_score"] = if_scores
        features["iforest_raw_anomaly"] = if_raw
        features["iforest_anomaly"] = if_gated
        features["ewma_z_score"] = ewma_z
        features["ewma_z_anomaly"] = ewma_flag
        features["zscore_anomaly"] = zscore_flag
        features["hybrid_anomaly"] = hybrid_flag

        # Continuous Hybrid score
        features["hybrid_score"] = np.maximum(
            ewma_z,
            np.clip((-if_scores + self.active_if_threshold) * 15.0 + 3.5, 0, 20),
        )

        # Summary statistics
        metrics_summary = {
            "total_rows": len(features),
            "anomalies_detected": int(hybrid_flag.sum()),
            "anomaly_percentage": round(float(hybrid_flag.mean() * 100), 2),
            "if_anomalies": int(if_gated.sum()),
            "ewma_anomalies": int(ewma_flag.sum()),
            "zscore_anomalies": int(zscore_flag.sum()),
        }

        # If ground truth labels exist, calculate confusion metrics
        if "label" in features.columns:
            y_true = features["label"].to_numpy(dtype=int)
            y_pred = hybrid_flag.astype(int)
            tp = int(((y_true == 1) & (y_pred == 1)).sum())
            fp = int(((y_true == 0) & (y_pred == 1)).sum())
            fn = int(((y_true == 1) & (y_pred == 0)).sum())
            tn = int(((y_true == 0) & (y_pred == 0)).sum())
            prec = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
            rec = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
            f1 = float(2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
            metrics_summary["confusion_matrix"] = {
                "tp": tp, "fp": fp, "fn": fn, "tn": tn,
                "precision": round(prec, 3),
                "recall": round(rec, 3),
                "f1": round(f1, 3),
            }

        return features, metrics_summary

    def process_streaming_buffer(self, buffer: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Process the latest observation in a sliding window buffer and return scored frame.
        """
        if len(buffer) < 2:
            return None

        if self.is_degraded or self.scaler is None or self.iso is None:
            last = buffer[-1]
            ts = last.get("timestamp")
            if isinstance(ts, (datetime, pd.Timestamp)):
                ts = ts.isoformat()
            elif not ts:
                ts = datetime.now(timezone.utc).isoformat()
            t_val = float(last.get("temperature", 25.0))
            h_val = float(last.get("humidity", 50.0))
            return {
                "timestamp": str(ts),
                "temperature": t_val,
                "humidity": h_val,
                "temp_ewma_residual": 0.0,
                "hum_ewma_residual": 0.0,
                "temp_rate": 0.0,
                "hum_rate": 0.0,
                "iforest_score": 0.0,
                "iforest_anomaly": False,
                "ewma_z_score": 0.0,
                "ewma_z_anomaly": False,
                "is_anomaly": False,
                "hybrid_score": 0.0,
                "status": "Detector unavailable",
                "trigger": "Model degraded",
            }

        raw_df = pd.DataFrame(buffer)
        raw_df["timestamp"] = pd.to_datetime(raw_df["timestamp"])
        raw_df = raw_df.sort_values("timestamp", kind="stable").reset_index(drop=True)

        features = build_features(
            raw_df,
            gap_threshold=self.thresholds.get("GAP_THRESHOLD", config.gap_threshold_sec),
            roll_min=self.thresholds.get("ROLL_MIN", config.roll_min),
            short_window_sec=self.thresholds.get("short_window_sec", config.short_window_sec),
            long_window_sec=self.thresholds.get("long_window_sec", config.long_window_sec),
            ewma_halflife_sec=self.thresholds.get("ewma_halflife_sec", config.ewma_halflife_sec),
            ewma_macro_gap_sec=self.thresholds.get("ewma_macro_gap_sec", config.ewma_macro_gap_sec),
        )

        if len(features) == 0:
            return None

        feature_cols = self.thresholds.get("feature_cols", MODEL_FEATURE_COLS)
        X_scaled = self.scaler.transform(features[feature_cols])

        if_scores = self.iso.decision_function(X_scaled)
        if_raw = if_scores < self.active_if_threshold
        if_gated = apply_gated_persistence(
            if_raw,
            features["session_id"].to_numpy(),
            features_df=features,
            window=self.thresholds.get("persistence_window", 5),
            min_hits=self.thresholds.get("persistence_min_hits", 3),
        )

        ewma_temp_std = float(self.thresholds.get("ewma_temp_std", 0.665))
        ewma_hum_std = float(self.thresholds.get("ewma_hum_std", 3.056))
        ewma_z = compute_adaptive_ewma_z(features, ewma_temp_std, ewma_hum_std)
        ewma_flag = ewma_z > self.active_ewma_threshold

        hybrid_flag = if_gated | ewma_flag

        latest_idx = len(features) - 1
        latest_row = features.iloc[latest_idx]

        return {
            "timestamp": latest_row["timestamp"].isoformat(),
            "temperature": float(latest_row["temperature"]),
            "humidity": float(latest_row["humidity"]),
            "temp_ewma_residual": float(latest_row["temp_ewma_residual"]),
            "hum_ewma_residual": float(latest_row["hum_ewma_residual"]),
            "temp_rate": float(latest_row["temp_rate"]),
            "hum_rate": float(latest_row["hum_rate"]),
            "iforest_score": float(if_scores[latest_idx]),
            "iforest_anomaly": bool(if_gated[latest_idx]),
            "ewma_z_score": float(ewma_z[latest_idx]),
            "ewma_z_anomaly": bool(ewma_flag[latest_idx]),
            "is_anomaly": bool(hybrid_flag[latest_idx]),
            "hybrid_score": float(max(ewma_z[latest_idx], np.clip((-if_scores[latest_idx] + self.active_if_threshold) * 15.0 + 3.5, 0, 20))),
            "status": "ANOMALY" if hybrid_flag[latest_idx] else "NORMAL",
            "trigger": (
                "Hybrid (IF + EWMA-Z)" if (if_gated[latest_idx] and ewma_flag[latest_idx])
                else ("Isolation Forest" if if_gated[latest_idx]
                else ("Adaptive EWMA-Z" if ewma_flag[latest_idx] else "None"))
            ),
        }


# Singleton instance
inference_service = InferenceService()
