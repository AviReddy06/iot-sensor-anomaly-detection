"""
dashboard/feature_utils.py
Thin wrapper exposing shared session/time-aware feature engineering and scoring helpers
to Streamlit dashboards.
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from features.feature_engine import (
    MODEL_FEATURE_COLS,
    RAW_COLS,
    apply_gated_persistence,
    build_features,
    compute_adaptive_ewma_z,
    default_feature_params,
)

__all__ = [
    "RAW_COLS",
    "MODEL_FEATURE_COLS",
    "apply_gated_persistence",
    "build_features",
    "compute_adaptive_ewma_z",
    "default_feature_params",
]
