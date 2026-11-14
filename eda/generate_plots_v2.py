#!/usr/bin/env python3
"""Generate EDA plots v2 with gap-aware line breaks and verified shaded event windows."""

from __future__ import annotations

from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import config


def break_at_gaps(df: pd.DataFrame, gap_threshold: float = 10.0) -> pd.DataFrame:
    """Return a copy of df with a NaN break inserted cleanly BEFORE each gap > gap_threshold."""
    work = df.copy()
    work["timestamp"] = pd.to_datetime(work["timestamp"])
    work = work.sort_values("timestamp", kind="stable").reset_index(drop=True)
    time_diff = work["timestamp"].diff().dt.total_seconds()
    gap_indices = work.index[time_diff > gap_threshold].tolist()

    if not gap_indices:
        return work

    chunks = []
    last_idx = 0
    for gap_idx in gap_indices:
        if gap_idx > last_idx:
            chunks.append(work.iloc[last_idx:gap_idx])
        nan_ts = work.loc[gap_idx - 1, "timestamp"] + pd.Timedelta(seconds=1)
        chunks.append(
            pd.DataFrame({"timestamp": [nan_ts], "temperature": [np.nan], "humidity": [np.nan]})
        )
        last_idx = gap_idx
    chunks.append(work.iloc[last_idx:])
    return pd.concat(chunks, ignore_index=True)


def generate_all_plots() -> None:
    proc_dir = config.processed_dir
    raw_dir = config.raw_dir
    plots_dir = PROJECT_ROOT / "eda" / "plots_v2"
    plots_dir.mkdir(parents=True, exist_ok=True)

    normal = pd.read_csv(proc_dir / "normal_data_training_candidate.csv")
    pilot = pd.read_csv(raw_dir / "pilot_data.csv")
    test = pd.read_csv(raw_dir / "test.csv")
    annotations = pd.read_csv(proc_dir / "pilot_event_annotations.csv")

    for df in (normal, pilot, test):
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    normal = normal.sort_values("timestamp", kind="stable").reset_index(drop=True)
    pilot = pilot.sort_values("timestamp", kind="stable").reset_index(drop=True)
    test = test.sort_values("timestamp", kind="stable").reset_index(drop=True)
    annotations["start_time"] = pd.to_datetime(annotations["start_time"])
    annotations["end_time"] = pd.to_datetime(annotations["end_time"])

    plt.style.use("seaborn-v0_8-whitegrid")
    sns.set_palette("husl")
    dpi = 300

    # 1. Normal histograms & boxplots
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes[0, 0].hist(normal["temperature"], bins=50, alpha=0.75, edgecolor="black", color="skyblue")
    axes[0, 0].axvline(normal["temperature"].mean(), color="red", linestyle="--", label=f"Mean: {normal['temperature'].mean():.2f}")
    axes[0, 0].set_title("Temperature Distribution (Clean Training Baseline)")
    axes[0, 0].set_xlabel("Temperature (°C)")
    axes[0, 0].legend()

    axes[0, 1].hist(normal["humidity"], bins=50, alpha=0.75, edgecolor="black", color="lightcoral")
    axes[0, 1].axvline(normal["humidity"].mean(), color="red", linestyle="--", label=f"Mean: {normal['humidity'].mean():.2f}")
    axes[0, 1].set_title("Humidity Distribution (Clean Training Baseline)")
    axes[0, 1].set_xlabel("Humidity (% RH)")
    axes[0, 1].legend()

    axes[1, 0].boxplot(normal["temperature"], orientation="vertical", patch_artist=True, boxprops=dict(facecolor="skyblue"))
    axes[1, 0].set_title("Temperature Boxplot (Clean)")
    axes[1, 0].set_ylabel("Temperature (°C)")

    axes[1, 1].boxplot(normal["humidity"], orientation="vertical", patch_artist=True, boxprops=dict(facecolor="lightcoral"))
    axes[1, 1].set_title("Humidity Boxplot (Clean)")
    axes[1, 1].set_ylabel("Humidity (% RH)")
    plt.tight_layout()
    plt.savefig(plots_dir / "normal_data_histograms.png", dpi=dpi, bbox_inches="tight")
    plt.close()

    # 2. Normal time series with clean gap breaks
    normal_gapped = break_at_gaps(normal, gap_threshold=config.gap_threshold_sec)
    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
    axes[0].plot(normal_gapped["timestamp"], normal_gapped["temperature"], alpha=0.65, linewidth=0.7, color="blue")
    axes[0].set_title("Temperature Over Time (Clean Training Baseline, Gaps >10s Broken)")
    axes[0].set_ylabel("Temperature (°C)")
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(normal_gapped["timestamp"], normal_gapped["humidity"], alpha=0.65, linewidth=0.7, color="orange")
    axes[1].set_title("Humidity Over Time (Clean Training Baseline, Gaps >10s Broken)")
    axes[1].set_xlabel("Timestamp")
    axes[1].set_ylabel("Humidity (% RH)")
    axes[1].grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(plots_dir / "normal_data_timeseries.png", dpi=dpi, bbox_inches="tight")
    plt.close()

    # 3. Normal correlation & intervals
    plt.figure(figsize=(6, 5))
    sns.heatmap(normal[["temperature", "humidity"]].corr(), annot=True, cmap="coolwarm", center=0, square=True, fmt=".3f")
    plt.title("Correlation Heatmap (Clean Training Baseline)")
    plt.savefig(plots_dir / "normal_data_correlation.png", dpi=dpi, bbox_inches="tight")
    plt.close()

    plt.figure(figsize=(9, 4))
    intervals = normal["timestamp"].diff().dt.total_seconds().dropna()
    plt.hist(intervals[intervals <= 10], bins=20, alpha=0.75, edgecolor="black", color="teal")
    plt.axvline(2.0, color="red", linestyle="--", linewidth=2, label="Expected: 2.0s")
    plt.title("Sampling Interval Distribution (<= 10s)")
    plt.xlabel("Interval (s)")
    plt.legend()
    plt.savefig(plots_dir / "normal_data_intervals.png", dpi=dpi, bbox_inches="tight")
    plt.close()

    # 4. Pilot timeseries with gap-aware breaks, original vs revised annotations
    pilot_gapped = break_at_gaps(pilot, gap_threshold=config.gap_threshold_sec)
    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
    axes[0].plot(pilot_gapped["timestamp"], pilot_gapped["temperature"], alpha=0.75, linewidth=0.9, color="#9B2C2C")

    # Shading intervals:
    # Revised extension in light straw
    for _, ann in annotations.iterrows():
        axes[0].axvspan(ann["start_time"], ann["end_time"], alpha=0.35, color="#E8B04A", label="Revised Addition (504 rows)" if _ == 0 else "")

    # Original 46 rows in dark straw
    orig_windows = [
        (pd.to_datetime("2026-10-27 23:09:38"), pd.to_datetime("2026-10-27 23:10:30")),
        (pd.to_datetime("2026-10-28 00:34:20"), pd.to_datetime("2026-10-28 00:34:56")),
    ]
    for idx, (s, e) in enumerate(orig_windows):
        axes[0].axvspan(s, e, alpha=0.75, color="#8B6914", label="Original Annotation (46 rows)" if idx == 0 else "")

    axes[0].set_title("Pilot Temperature Over Time — Original (Dark Straw) vs Post-Hoc Revised (Light Straw)")
    axes[0].set_ylabel("Temperature (°C)")
    axes[0].legend(loc="upper right")
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(pilot_gapped["timestamp"], pilot_gapped["humidity"], alpha=0.75, linewidth=0.9, color="#1D5C8C")
    for _, ann in annotations.iterrows():
        axes[1].axvspan(ann["start_time"], ann["end_time"], alpha=0.35, color="#E8B04A")
    for s, e in orig_windows:
        axes[1].axvspan(s, e, alpha=0.75, color="#8B6914")

    axes[1].set_title("Pilot Humidity Over Time — Event Windows Annotated")
    axes[1].set_xlabel("Timestamp")
    axes[1].set_ylabel("Humidity (% RH)")
    axes[1].grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(plots_dir / "pilot_data_timeseries.png", dpi=dpi, bbox_inches="tight")
    plt.close()

    # 5. Pilot anomaly detail
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    event1 = pilot[(pilot["timestamp"] >= "2026-10-27 23:09:00") & (pilot["timestamp"] <= "2026-10-27 23:12:00")]
    axes[0, 0].plot(event1["timestamp"], event1["temperature"], "o-", markersize=3, color="blue")
    axes[0, 0].set_title("Event 1 Onset: Temperature (23:09 - 23:12)")
    axes[0, 0].set_ylabel("Temperature (°C)")
    axes[0, 0].grid(True, alpha=0.3)
    axes[0, 0].tick_params(axis="x", rotation=45)

    axes[0, 1].plot(event1["timestamp"], event1["humidity"], "o-", markersize=3, color="orange")
    axes[0, 1].set_title("Event 1 Onset: Humidity (23:09 - 23:12)")
    axes[0, 1].set_ylabel("Humidity (% RH)")
    axes[0, 1].grid(True, alpha=0.3)
    axes[0, 1].tick_params(axis="x", rotation=45)

    event2 = pilot[(pilot["timestamp"] >= "2026-10-28 00:33:30") & (pilot["timestamp"] <= "2026-10-28 00:36:00")]
    axes[1, 0].plot(event2["timestamp"], event2["temperature"], "o-", markersize=3, color="blue")
    axes[1, 0].set_title("Event 2: Temperature (00:33:30 - 00:36:00)")
    axes[1, 0].set_ylabel("Temperature (°C)")
    axes[1, 0].grid(True, alpha=0.3)
    axes[1, 0].tick_params(axis="x", rotation=45)

    axes[1, 1].plot(event2["timestamp"], event2["humidity"], "o-", markersize=3, color="orange")
    axes[1, 1].set_title("Event 2: Humidity (00:33:30 - 00:36:00)")
    axes[1, 1].set_xlabel("Timestamp")
    axes[1, 1].set_ylabel("Humidity (% RH)")
    axes[1, 1].grid(True, alpha=0.3)
    axes[1, 1].tick_params(axis="x", rotation=45)
    plt.tight_layout()
    plt.savefig(plots_dir / "pilot_data_anomaly_detail.png", dpi=dpi, bbox_inches="tight")
    plt.close()

    # 6. Legacy test plots
    anomaly_start = pd.to_datetime("2026-10-27 22:03:29")
    anomaly_end = pd.to_datetime("2026-10-27 22:03:47")
    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    axes[0].plot(test["timestamp"], test["temperature"], "o-", color="blue", markersize=4, label="Temperature")
    axes[0].axvspan(anomaly_start, anomaly_end, alpha=0.3, color="red", label="Anomaly Window")
    axes[0].set_title("Test Set: Anomaly Window - Temperature")
    axes[0].set_ylabel("Temperature (°C)")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(test["timestamp"], test["humidity"], "o-", color="orange", markersize=4, label="Humidity")
    axes[1].axvspan(anomaly_start, anomaly_end, alpha=0.3, color="red", label="Anomaly Window")
    axes[1].set_title("Test Set: Anomaly Window - Humidity")
    axes[1].set_xlabel("Timestamp")
    axes[1].set_ylabel("Humidity (% RH)")
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(plots_dir / "test_data_timeseries.png", dpi=dpi, bbox_inches="tight")
    plt.close()

    fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    anomaly_data = test[(test["timestamp"] >= anomaly_start) & (test["timestamp"] <= anomaly_end)]
    axes[0].plot(anomaly_data["timestamp"], anomaly_data["temperature"], "o-", color="red", markersize=6)
    axes[0].set_title("Test Set: Anomaly Detail - Temperature")
    axes[0].set_ylabel("Temperature (°C)")
    axes[0].grid(True, alpha=0.3)
    axes[0].tick_params(axis="x", rotation=45)

    axes[1].plot(anomaly_data["timestamp"], anomaly_data["humidity"], "o-", color="red", markersize=6)
    axes[1].set_title("Test Set: Anomaly Detail - Humidity")
    axes[1].set_xlabel("Timestamp")
    axes[1].set_ylabel("Humidity (% RH)")
    axes[1].grid(True, alpha=0.3)
    axes[1].tick_params(axis="x", rotation=45)
    plt.tight_layout()
    plt.savefig(plots_dir / "test_data_anomaly_detail.png", dpi=dpi, bbox_inches="tight")
    plt.close()

    print("All EDA plots regenerated cleanly:")
    for f in sorted(plots_dir.glob("*.png")):
        print(f"  {f.name} ({f.stat().st_size:,} bytes)")


if __name__ == "__main__":
    generate_all_plots()
