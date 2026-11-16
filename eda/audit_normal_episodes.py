#!/usr/bin/env python3
"""
eda/audit_normal_episodes.py
Audit raw/deduplicated normal telemetry vs quarantined anomalies vs clean training baseline.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import config


def run_audit() -> None:
    proc_dir = config.processed_dir
    plots_dir = PROJECT_ROOT / "eda" / "plots_v2"
    plots_dir.mkdir(parents=True, exist_ok=True)

    dedup = pd.read_csv(proc_dir / "normal_data_deduplicated_all.csv")
    dedup["timestamp"] = pd.to_datetime(dedup["timestamp"])
    dedup = dedup.sort_values("timestamp", kind="stable").reset_index(drop=True)

    quarantined = pd.read_csv(proc_dir / "normal_quarantined_anomalies.csv")
    quarantined["timestamp"] = pd.to_datetime(quarantined["timestamp"])

    clean = pd.read_csv(proc_dir / "normal_data_training_candidate.csv")
    clean["timestamp"] = pd.to_datetime(clean["timestamp"])

    print(f"Deduplicated normal rows : {len(dedup):,}")
    print(f"Quarantined anomaly rows : {len(quarantined):,} ({len(quarantined) / max(len(dedup), 1) * 100:.2f}%)")
    print(f"Clean training candidate : {len(clean):,}")

    # Physical rate & robust MAD check (with noise-floor guard >= 0.05 to avoid quantization zero-MAD explosion)
    dedup["dt"] = dedup["timestamp"].diff().dt.total_seconds().fillna(2.0).clip(lower=1.0)
    dedup["temp_step"] = dedup["temperature"].diff().fillna(0.0)
    dedup["hum_step"] = dedup["humidity"].diff().fillna(0.0)
    dedup.loc[dedup["dt"] > config.gap_threshold_sec, ["temp_step", "hum_step"]] = 0.0

    for col, floor in [("temp_step", 0.05), ("hum_step", 0.15)]:
        med = float(dedup[col].median())
        mad = float(np.median(np.abs(dedup[col] - med)))
        scale = max(1.4826 * mad, floor)
        dedup[f"{col}_robust_z"] = (dedup[col] - med) / scale
        print(f"  {col}: median={med:.4f}, MAD={mad:.4f}, bounded_scale={scale:.4f}")

    # Merge quarantined episodes cleanly using dedup index (no index mismatch)
    is_cand = (dedup["temp_step_robust_z"].abs() > 6.0) | (dedup["hum_step_robust_z"].abs() > 6.0) | (dedup["humidity"] > 72.0)
    cand_indices = dedup.index[is_cand].tolist()
    episodes = []
    if cand_indices:
        cur = [cand_indices[0]]
        for idx in cand_indices[1:]:
            gap = (dedup.loc[idx, "timestamp"] - dedup.loc[cur[-1], "timestamp"]).total_seconds()
            if gap <= 60.0:
                cur.append(idx)
            else:
                episodes.append(cur)
                cur = [idx]
        episodes.append(cur)

    print(f"\nDetected disturbance seed episodes in deduplicated normal set: {len(episodes)}")
    for i, ep_idx in enumerate(episodes, start=1):
        sub = dedup.loc[ep_idx]
        print(
            f"  Episode {i}: {sub['timestamp'].min()} -> {sub['timestamp'].max()} "
            f"| seed_rows={len(sub)} | T=[{sub['temperature'].min():.1f}, {sub['temperature'].max():.1f}] "
            f"| H=[{sub['humidity'].min():.1f}, {sub['humidity'].max():.1f}]"
        )

    # Save visual plot to canonical eda/plots_v2/
    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
    axes[0].plot(dedup["timestamp"], dedup["temperature"], "b-", alpha=0.5, linewidth=0.6, label="Deduplicated Normal")
    if len(quarantined) > 0:
        axes[0].scatter(quarantined["timestamp"], quarantined["temperature"], color="red", s=12, zorder=5, label="Quarantined Anomaly/Burst")
    axes[0].axhline(clean["temperature"].median(), color="blue", linestyle="--", alpha=0.5, label=f"Clean Median ({clean['temperature'].median():.1f}°C)")
    axes[0].set_ylabel("Temperature (°C)")
    axes[0].set_title("Normal Dataset Audit — Quarantined vs Clean Baseline")
    axes[0].legend(loc="upper right")
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(dedup["timestamp"], dedup["humidity"], "g-", alpha=0.5, linewidth=0.6, label="Deduplicated Normal")
    if len(quarantined) > 0:
        axes[1].scatter(quarantined["timestamp"], quarantined["humidity"], color="red", s=12, zorder=5, label="Quarantined Anomaly/Burst")
    axes[1].axhline(clean["humidity"].median(), color="green", linestyle="--", alpha=0.5, label=f"Clean Median ({clean['humidity'].median():.1f}%)")
    axes[1].set_ylabel("Humidity (% RH)")
    axes[1].set_xlabel("Timestamp")
    axes[1].legend(loc="upper right")
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    out_plot = plots_dir / "normal_candidate_episodes.png"
    fig.savefig(out_plot, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\nSaved audit plot: {out_plot}")

    # Verify post-cleaning baseline has 0 extreme single-step jumps inside sessions
    clean_dt = clean["timestamp"].diff().dt.total_seconds().fillna(2.0)
    clean_dT = clean["temperature"].diff().fillna(0.0).where(clean_dt <= config.gap_threshold_sec, 0.0)
    clean_dH = clean["humidity"].diff().fillna(0.0).where(clean_dt <= config.gap_threshold_sec, 0.0)
    print(
        f"Clean training stability check: max |dT|={clean_dT.abs().max():.2f}°C, "
        f"max |dH|={clean_dH.abs().max():.2f}% RH, H range=[{clean['humidity'].min():.1f}, {clean['humidity'].max():.1f}]"
    )


if __name__ == "__main__":
    run_audit()
