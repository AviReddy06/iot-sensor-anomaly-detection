"""Unit tests for session/time-aware feature engineering (`features/feature_engine.py`)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from features.feature_engine import (
    MODEL_FEATURE_COLS,
    apply_gated_persistence,
    build_features,
    compute_adaptive_ewma_z,
)


def test_build_features_schema_and_no_nans(synthetic_steady_df: pd.DataFrame):
    feat = build_features(synthetic_steady_df)
    assert len(feat) > 190
    for col in MODEL_FEATURE_COLS:
        assert col in feat.columns
        assert feat[col].isna().sum() == 0


def test_session_splitting_across_time_gap():
    ts1 = pd.date_range("2026-11-10 10:00:00", periods=10, freq="2s")
    ts2 = pd.date_range("2026-11-10 10:02:00", periods=10, freq="2s")  # > 10s gap
    df = pd.DataFrame({
        "timestamp": list(ts1) + list(ts2),
        "temperature": [25.0] * 10 + [35.0] * 10,
        "humidity": [60.0] * 10 + [40.0] * 10,
    })
    feat = build_features(df, gap_threshold=10.0)
    assert feat["session_id"].nunique() == 2
    # First row after session boundary must have been dropped cleanly (no cross-gap rate spike)
    assert feat["temp_rate"].abs().max() < 0.01
    assert feat["hum_rate"].abs().max() < 0.01


def test_gated_ewma_resists_sustained_excursion_without_post_recovery_poisoning():
    n = 120
    ts = pd.date_range("2026-11-10 11:00:00", periods=n, freq="2s")
    temp = np.full(n, 26.0)
    hum = np.full(n, 60.0)
    # Sustained heat/breath anomaly across samples 40..80 (+6 C, +25% RH)
    temp[40:80] = 32.0
    hum[40:80] = 85.0
    df = pd.DataFrame({"timestamp": ts, "temperature": temp, "humidity": hum})

    feat = build_features(df, ewma_halflife_sec=600)
    # Post-recovery rows (indices > 85) should return near zero residual (no baseline poisoning)
    tail = feat.iloc[-20:]
    assert tail["temp_ewma_abs_residual"].mean() < 0.25
    assert tail["hum_ewma_abs_residual"].mean() < 1.0


def test_apply_gated_persistence_filters_single_row_jitter_only():
    sess = np.zeros(12, dtype=int)
    flags = np.array([False, False, True, False, False, True, True, True, False, False, False, False])
    calm_df = pd.DataFrame({
        "temp_abs_rate": np.full(12, 0.01),
        "hum_abs_rate": np.full(12, 0.05),
        "temp_ewma_abs_residual": np.full(12, 0.2),
        "hum_ewma_abs_residual": np.full(12, 0.5),
    })
    filtered = apply_gated_persistence(flags, sess, features_df=calm_df, window=5, min_hits=3)
    # Isolated 1-row blip at index 2 is suppressed; 3-in-5 hit at index 7 is confirmed; trailing False stays False
    assert not filtered[2]
    assert filtered[7]
    assert not filtered[8]
    assert not filtered[9]


def test_compute_adaptive_ewma_z_floor_protection():
    df = pd.DataFrame({
        "temp_ewma_residual": [0.0, 2.0],
        "hum_ewma_residual": [0.0, -5.0],
    })
    ez = compute_adaptive_ewma_z(df, ewma_temp_std=0.0, ewma_hum_std=0.0)
    assert np.isfinite(ez).all()
    assert ez[0] == 0.0
    assert ez[1] > 5.0
