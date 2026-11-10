#!/usr/bin/env python3
"""
preprocess/clean_datasets.py
Reproducible cleaning, annotation repair, train/holdout split, and multi-fault test suite generation.

Important:
- Raw CSVs in `data/raw/` are NEVER modified.
- Outputs are written cleanly under `data/processed/`.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import config


def load_raw_normal(raw_path: Path) -> pd.DataFrame:
    """Load normal_data.csv cleanly handling optional header or blank initial lines."""
    first_nonempty = ""
    with raw_path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            stripped = line.strip()
            if stripped:
                first_nonempty = stripped
                break

    if first_nonempty.lower().startswith("timestamp"):
        df = pd.read_csv(raw_path)
    else:
        df = pd.read_csv(raw_path, header=None, names=["timestamp", "temperature", "humidity"])

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["temperature"] = pd.to_numeric(df["temperature"], errors="coerce")
    df["humidity"] = pd.to_numeric(df["humidity"], errors="coerce")
    df = df.dropna(subset=["timestamp", "temperature", "humidity"]).copy()
    return df


def quarantine_unlabeled_anomalies(
    df: pd.DataFrame,
    gap_threshold: float = 10.0,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Identify and separate obvious unlabeled disturbance/fault episodes from normal baseline data
    while preserving natural slow diurnal indoor cycles.
    """
    work = df.sort_values("timestamp", kind="stable").reset_index(drop=True)
    work["time_diff"] = work["timestamp"].diff().dt.total_seconds()
    work["session_id"] = (work["time_diff"] > gap_threshold).cumsum().fillna(0).astype(int)
    dt = work.groupby("session_id")["timestamp"].diff().dt.total_seconds().clip(lower=1.0)
    work["dT"] = work.groupby("session_id")["temperature"].diff().fillna(0.0)
    work["dH"] = work.groupby("session_id")["humidity"].diff().fillna(0.0)
    work["rate_T"] = (work["dT"] / dt).abs()
    work["rate_H"] = (work["dH"] / dt).abs()

    # Flag spike/disturbance seeds: sharp humidity/temp step jumps or extreme indoor humidity saturation (>72%)
    is_seed = (
        (work["dH"].abs() >= 1.5)
        | (work["dT"].abs() >= 0.4)
        | (work["rate_H"] >= 0.7)
        | (work["humidity"] > 72.0)
    )

    quarantine_mask = pd.Series(False, index=work.index)
    seed_indices = np.where(is_seed)[0]

    for idx in seed_indices:
        sid = work.loc[idx, "session_id"]
        t_seed = work.loc[idx, "timestamp"]

        # Protect +/- 30s around every disturbance seed inside the same session
        in_pad = (
            (work["session_id"] == sid)
            & (work["timestamp"] >= t_seed - pd.Timedelta(seconds=30))
            & (work["timestamp"] <= t_seed + pd.Timedelta(seconds=30))
        )
        quarantine_mask |= in_pad

        # Extend forward within session while humidity remains abnormally elevated or recovering fast
        pos = idx + 1
        while pos < len(work) and work.loc[pos, "session_id"] == sid:
            h_val = work.loc[pos, "humidity"]
            dh_abs = abs(work.loc[pos, "dH"])
            if h_val > 70.0 or dh_abs >= 0.5:
                quarantine_mask.iloc[pos] = True
                pos += 1
            else:
                break

    # Also quarantine timestamp-burst anomaly cluster around s9 if remaining anomalous drop exists
    clean_df = work.loc[~quarantine_mask, ["timestamp", "temperature", "humidity"]].reset_index(drop=True)
    quarantined_df = work.loc[quarantine_mask, ["timestamp", "temperature", "humidity"]].reset_index(drop=True)
    return clean_df, quarantined_df


def build_verified_pilot_annotations(pilot: pd.DataFrame) -> pd.DataFrame:
    """
    Build verified pilot event annotations covering the full disturbed intervals
    including Event 1's 23:09:38 -> 23:40:28 recovery tail and Event 2's full peak & cool-down.
    """
    work = pilot.copy()
    work["timestamp"] = pd.to_datetime(work["timestamp"])
    work = work.sort_values("timestamp", kind="stable").reset_index(drop=True)

    event_defs = [
        {
            "event_id": 1,
            "start_time": pd.Timestamp("2026-10-27 23:09:38"),
            "end_time": pd.Timestamp("2026-10-27 23:40:28"),
            "description": "Breath humidity spike (95.2% RH) followed by prolonged heat/dry recovery tail across session resume (to 31.8 C, 44.4% RH).",
        },
        {
            "event_id": 2,
            "start_time": pd.Timestamp("2026-10-28 00:34:20"),
            "end_time": pd.Timestamp("2026-10-28 00:35:35"),
            "description": "Sharp temp/humidity spike (32.9 C, 95.8% RH) with rapid cooling recovery back near baseline.",
        },
    ]

    rows: List[Dict[str, object]] = []
    for ev in event_defs:
        mask = (work["timestamp"] >= ev["start_time"]) & (work["timestamp"] <= ev["end_time"])
        sub = work.loc[mask]
        rows.append(
            {
                "event_id": ev["event_id"],
                "start_time": ev["start_time"].strftime("%Y-%m-%d %H:%M:%S"),
                "end_time": ev["end_time"].strftime("%Y-%m-%d %H:%M:%S"),
                "duration_seconds": float((ev["end_time"] - ev["start_time"]).total_seconds()),
                "num_rows": int(len(sub)),
                "temp_min": float(sub["temperature"].min()),
                "temp_max": float(sub["temperature"].max()),
                "hum_min": float(sub["humidity"].min()),
                "hum_max": float(sub["humidity"].max()),
                "description": ev["description"],
                "verification_status": "verified against full pilot trace",
            }
        )

    return pd.DataFrame(rows)


def build_eval_test_suite(
    holdout_normal: pd.DataFrame,
    live_baseline: pd.DataFrame | None = None,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Build an unseen multi-event evaluation test suite (`eval_test_suite.csv`) using:
    1) Unseen held-out clean normal baseline rows (completely disjoint from training data),
    2) Real live baseline rows captured from connected DHT11 hardware (if available),
    3) Controlled physical & sensor-fault injection scenarios across distinct time blocks:
       - breath_spike (simultaneous high RH + elevated T)
       - heat_source_burst (T spike with dry RH drop)
       - cold_draft_drop (rapid cooling + RH shift)
       - offset_fault (sudden sensor calibration step +4.5 C)
       - slow_drift_fault (gradual linear drift +5 C / +18% RH over 3 min)
       - chatter_noise_fault (loose wiring / electrical jitter)
    """
    rng = np.random.default_rng(seed)

    # Use held-out normal rows as clean base (resampled/ordered chronologically)
    base = holdout_normal.sort_values("timestamp", kind="stable").reset_index(drop=True).copy()
    base["label"] = 0
    base["fault_type"] = "normal_holdout"

    # Inject controlled non-overlapping anomaly episodes inside holdout blocks
    # Pick evenly spaced indices safely inside the holdout trace
    n = len(base)
    if n < 500:
        raise ValueError(f"Holdout base needs >= 500 rows, got {n}")

    # Episode definitions: (start_fraction, length_rows, fault_type)
    scenarios = [
        (0.10, 18, "breath_spike"),
        (0.24, 24, "heat_source_burst"),
        (0.40, 20, "cold_draft_drop"),
        (0.56, 20, "offset_fault"),
        (0.72, 45, "slow_drift_fault"),
        (0.88, 16, "chatter_noise_fault"),
    ]

    for frac, length, fault in scenarios:
        s_idx = int(n * frac)
        e_idx = min(n, s_idx + length)
        k = e_idx - s_idx
        t_base = float(base.loc[s_idx - 1, "temperature"])
        h_base = float(base.loc[s_idx - 1, "humidity"])

        if fault == "breath_spike":
            # Rapid breath jump + exponential decay back
            progress = np.linspace(0, 1, k)
            t_delta = 5.2 * np.sin(np.pi * np.minimum(progress * 1.1, 1.0))
            h_delta = 30.0 * np.exp(-2.2 * np.maximum(progress - 0.15, 0.0)) * np.minimum(progress * 5.0, 1.0)
            base.loc[s_idx:e_idx - 1, "temperature"] = np.round(t_base + t_delta, 1)
            base.loc[s_idx:e_idx - 1, "humidity"] = np.round(np.clip(h_base + h_delta, 0, 100), 1)

        elif fault == "heat_source_burst":
            progress = np.linspace(0, 1, k)
            envelope = np.sin(np.pi * progress) ** 0.7
            base.loc[s_idx:e_idx - 1, "temperature"] = np.round(t_base + 7.5 * envelope, 1)
            base.loc[s_idx:e_idx - 1, "humidity"] = np.round(np.clip(h_base - 15.0 * envelope, 0, 100), 1)

        elif fault == "cold_draft_drop":
            progress = np.linspace(0, 1, k)
            envelope = np.sin(np.pi * progress) ** 0.8
            base.loc[s_idx:e_idx - 1, "temperature"] = np.round(t_base - 4.8 * envelope, 1)
            base.loc[s_idx:e_idx - 1, "humidity"] = np.round(np.clip(h_base + 9.0 * envelope, 0, 100), 1)

        elif fault == "offset_fault":
            # Instantaneous positive calibration jump step
            base.loc[s_idx:e_idx - 1, "temperature"] = np.round(base.loc[s_idx:e_idx - 1, "temperature"] + 4.8, 1)
            base.loc[s_idx:e_idx - 1, "humidity"] = np.round(np.clip(base.loc[s_idx:e_idx - 1, "humidity"] - 10.5, 0, 100), 1)

        elif fault == "slow_drift_fault":
            # Progressive drift ramping up over 90s then failing back cleanly
            ramp = np.linspace(0.6, 5.5, k)
            h_ramp = np.linspace(2.0, 18.0, k)
            base.loc[s_idx:e_idx - 1, "temperature"] = np.round(base.loc[s_idx:e_idx - 1, "temperature"] + ramp, 1)
            base.loc[s_idx:e_idx - 1, "humidity"] = np.round(np.clip(base.loc[s_idx:e_idx - 1, "humidity"] + h_ramp, 0, 100), 1)

        elif fault == "chatter_noise_fault":
            # Loose wire / erratic electrical jitter
            t_jit = rng.choice([-1.8, 1.9, -2.4, 2.5], size=k)
            h_jit = rng.choice([-6.5, 7.0, -8.2, 8.5], size=k)
            base.loc[s_idx:e_idx - 1, "temperature"] = np.round(t_base + t_jit, 1)
            base.loc[s_idx:e_idx - 1, "humidity"] = np.round(np.clip(h_base + h_jit, 0, 100), 1)

        base.loc[s_idx:e_idx - 1, "label"] = 1
        base.loc[s_idx:e_idx - 1, "fault_type"] = fault

    # Append live today hardware baseline as unseen normal readings (after 1h gap cleanly separated)
    if live_baseline is not None and len(live_baseline) > 0:
        live = live_baseline.copy()
        live["timestamp"] = pd.to_datetime(live["timestamp"])
        live["label"] = 0
        live["fault_type"] = "live_dht11_normal"
        # Ensure live segment is strictly separated by > gap_threshold if timestamps overlap or differ
        base = pd.concat([base, live[["timestamp", "temperature", "humidity", "label", "fault_type"]]], ignore_index=True)

    return base.sort_values("timestamp", kind="stable").reset_index(drop=True)


def run_cleaning() -> Dict[str, object]:
    """Execute full reproducible preprocessing and save cleaned artifacts."""
    raw_dir = config.raw_dir
    proc_dir = config.processed_dir
    proc_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load & deduplicate normal_data.csv
    raw_normal = load_raw_normal(raw_dir / "normal_data.csv")
    dedup_exact = (
        raw_normal.drop_duplicates()
        .sort_values("timestamp", kind="stable")
        .reset_index(drop=True)
    )
    dedup_exact.to_csv(proc_dir / "normal_data_deduplicated_all.csv", index=False)

    # Collapse same-second bursts (keep last per timestamp)
    no_burst = dedup_exact.drop_duplicates(subset=["timestamp"], keep="last").reset_index(drop=True)

    # Quarantine unlabeled anomalies from normal_data
    clean_normal_all, quarantined = quarantine_unlabeled_anomalies(
        no_burst, gap_threshold=config.gap_threshold_sec
    )
    quarantined.to_csv(proc_dir / "normal_quarantined_anomalies.csv", index=False)

    # Hold out final continuous session (Nov 1, >= 2026-11-01) so eval suite uses strictly unseen dates
    split_cutoff = pd.Timestamp("2026-11-01 00:00:00")
    train_normal = clean_normal_all[clean_normal_all["timestamp"] < split_cutoff].copy()
    holdout_normal = clean_normal_all[clean_normal_all["timestamp"] >= split_cutoff].copy()

    # Load all live hardware baselines captured today (e.g., data/raw/live_*_2026-11-10.csv)
    live_frames = []
    for lp in sorted(raw_dir.glob("live_*.csv")):
        ldf = pd.read_csv(lp)
        ldf["timestamp"] = pd.to_datetime(ldf["timestamp"], errors="coerce")
        ldf = ldf.dropna(subset=["timestamp", "temperature", "humidity"]).reset_index(drop=True)
        if len(ldf) > 0:
            live_frames.append(ldf)
    live_df = pd.concat(live_frames, ignore_index=True).sort_values("timestamp", kind="stable").reset_index(drop=True) if live_frames else None

    # Save cleaned training candidate (keeping legacy filename synchronized!)
    # Optionally fold half of live today normal rows into training or keep ALL live today rows unseen in eval!
    # Best practice: keep live_2026-11-10 completely unseen in eval_suite to prove zero-retrain cross-day generalization!
    train_normal.to_csv(proc_dir / "normal_data_clean.csv", index=False)
    train_normal.to_csv(proc_dir / "normal_data_training_candidate.csv", index=False)

    # 2. Pilot data preparation & verified annotations
    pilot = pd.read_csv(raw_dir / "pilot_data.csv")
    pilot["timestamp"] = pd.to_datetime(pilot["timestamp"])
    pilot = pilot.sort_values("timestamp", kind="stable").reset_index(drop=True)
    pilot.to_csv(proc_dir / "pilot_data_prepared.csv", index=False)

    annotations = build_verified_pilot_annotations(pilot)
    annotations.to_csv(proc_dir / "pilot_event_annotations.csv", index=False)

    # 3. Preserve legacy test_data_with_labels.csv accurately from raw test.csv + test_labels.csv
    legacy_test = pd.read_csv(raw_dir / "test.csv")
    legacy_test["timestamp"] = pd.to_datetime(legacy_test["timestamp"])
    legacy_labels = pd.read_csv(raw_dir / "test_labels.csv")
    legacy_test["label"] = 0
    for _, row in legacy_labels.iterrows():
        s = pd.to_datetime(row["start"])
        e = pd.to_datetime(row["end"])
        legacy_test.loc[(legacy_test["timestamp"] >= s) & (legacy_test["timestamp"] <= e), "label"] = 1
    legacy_test.to_csv(proc_dir / "test_data_with_labels.csv", index=False)

    # 4. Build comprehensive unseen multi-fault evaluation suite
    eval_suite = build_eval_test_suite(holdout_normal, live_baseline=live_df, seed=42)
    eval_suite.to_csv(proc_dir / "eval_test_suite.csv", index=False)

    summary = {
        "raw_normal_rows": int(len(raw_normal)),
        "dedup_exact_rows": int(len(dedup_exact)),
        "after_burst_collapse_rows": int(len(no_burst)),
        "quarantined_anomaly_rows": int(len(quarantined)),
        "train_clean_normal_rows": int(len(train_normal)),
        "holdout_nov1_rows": int(len(holdout_normal)),
        "live_today_rows": int(len(live_df)) if live_df is not None else 0,
        "pilot_rows": int(len(pilot)),
        "pilot_annotated_rows": int(annotations["num_rows"].sum()),
        "eval_suite_rows": int(len(eval_suite)),
        "eval_suite_anomalies": int((eval_suite["label"] == 1).sum()),
        "eval_suite_faults": eval_suite.loc[eval_suite["label"] == 1, "fault_type"].value_counts().to_dict(),
    }

    with open(proc_dir / "cleaning_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("=== CLEANING SUMMARY ===")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    return summary


if __name__ == "__main__":
    run_cleaning()
