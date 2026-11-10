"""Unit tests for preprocessing & quarantine logic (`preprocess/clean_datasets.py`)."""

from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

from preprocess.clean_datasets import (
    build_eval_test_suite,
    load_raw_normal,
    quarantine_unlabeled_anomalies,
)


def test_load_raw_normal_handles_blank_first_line(tmp_path: Path):
    csv_file = tmp_path / "headerless_normal.csv"
    csv_file.write_text(
        "\n2026-10-29T16:39:00,25.9,60.8\n2026-10-29T16:39:02,26.0,60.7\n",
        encoding="utf-8",
    )
    df = load_raw_normal(csv_file)
    assert list(df.columns) == ["timestamp", "temperature", "humidity"]
    assert len(df) == 2
    assert np.isclose(df["temperature"].iloc[0], 25.9)


def test_quarantine_preserves_steady_baseline_and_removes_spike(synthetic_steady_df: pd.DataFrame):
    df = synthetic_steady_df.copy()
    # Inject a breath saturation spike around rows 100..108
    df.loc[100:108, "humidity"] = [75.0, 88.0, 95.0, 91.0, 84.0, 77.0, 72.5, 68.0, 62.0]
    df.loc[100:108, "temperature"] = [28.4, 29.2, 30.1, 30.0, 29.5, 29.0, 28.6, 28.3, 28.1]

    clean, quarantined = quarantine_unlabeled_anomalies(df, gap_threshold=10.0)
    assert len(quarantined) >= 9
    assert clean["humidity"].max() <= 72.0
    assert len(clean) + len(quarantined) == len(df)


def test_build_eval_test_suite_contains_all_six_faults_and_live():
    ts = pd.date_range("2026-11-01 08:00:00", periods=600, freq="2s")
    holdout = pd.DataFrame({
        "timestamp": ts,
        "temperature": np.full(600, 25.5),
        "humidity": np.full(600, 60.0),
    })
    live = pd.DataFrame({
        "timestamp": pd.date_range("2026-11-10 12:00:00", periods=20, freq="2s"),
        "temperature": np.full(20, 29.5),
        "humidity": np.full(20, 54.0),
    })
    suite = build_eval_test_suite(holdout, live_baseline=live, seed=42)
    faults = set(suite["fault_type"].unique())
    expected = {
        "normal_holdout",
        "live_dht11_normal",
        "breath_spike",
        "heat_source_burst",
        "cold_draft_drop",
        "offset_fault",
        "slow_drift_fault",
        "chatter_noise_fault",
    }
    assert expected.issubset(faults)
    assert int((suite["label"] == 1).sum()) == 143


def test_raw_datasets_remain_immutable(project_root: Path):
    raw_dir = project_root / "data" / "raw"
    for fname, min_rows in [
        ("normal_data.csv", 49700),
        ("pilot_data.csv", 3080),
        ("test.csv", 55),
        ("test_labels.csv", 1),
    ]:
        p = raw_dir / fname
        assert p.exists(), f"Missing raw file {p}"
        line_count = sum(1 for _ in p.open("r", encoding="utf-8", errors="ignore"))
        assert line_count >= min_rows
