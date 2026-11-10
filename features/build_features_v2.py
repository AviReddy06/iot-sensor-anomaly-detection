#!/usr/bin/env python3
"""
features/build_features_v2.py
Generate unified time-aware and session-aware engineered features for all datasets.
"""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import config
from features.feature_engine import MODEL_FEATURE_COLS, RAW_COLS, build_features


def build_all_feature_sets() -> None:
    """Compute engineered features for normal, pilot, legacy test, and eval_suite datasets."""
    proc_dir = config.processed_dir
    out_dir = config.features_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    inputs = {
        "normal": proc_dir / "normal_data_training_candidate.csv",
        "pilot": proc_dir / "pilot_data_prepared.csv",
        "test": proc_dir / "test_data_with_labels.csv",
        "eval_suite": proc_dir / "eval_test_suite.csv",
    }

    for name, path in inputs.items():
        if not path.exists():
            print(f"[SKIP] {name}: missing {path}")
            continue

        print(f"\n=== Building features for {name} ===")
        raw_df = pd.read_csv(path)
        feat_df = build_features(
            raw_df,
            gap_threshold=config.gap_threshold_sec,
            roll_min=config.roll_min,
            short_window_sec=config.short_window_sec,
            long_window_sec=config.long_window_sec,
            ewma_halflife_sec=config.ewma_halflife_sec,
            ewma_macro_gap_sec=config.ewma_macro_gap_sec,
        )

        # Model feature matrix only (strictly drift-resilient MODEL_FEATURE_COLS)
        feat_df[MODEL_FEATURE_COLS].to_csv(out_dir / f"{name}_features.csv", index=False)
        # Full table with raw temp/humidity + metadata/labels for inspection, evaluation & dashboards
        feat_df.to_csv(out_dir / f"{name}_features_full.csv", index=False)

        print(
            f"  Input rows: {len(raw_df)} -> Feature rows: {len(feat_df)} "
            f"| Sessions: {feat_df['session_id'].nunique()} "
            f"| Model cols: {len(MODEL_FEATURE_COLS)} (+{len(RAW_COLS)} raw)"
        )

    print("\n=== Feature build complete ===")


if __name__ == "__main__":
    build_all_feature_sets()
