#!/usr/bin/env python3
"""
eda/generate_report_figures.py
Generate 300 DPI figures for the report:
1. Event-level recall per detector with 95% block bootstrap CI
2. False alarms per day per detector on normal baseline
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Load evaluation results
results_path = PROJECT_ROOT / "results" / "evaluation_results.json"
with open(results_path, "r", encoding="utf-8") as f:
    results = json.load(f)

# Filter to test set and eval_suite (where we have event_recall and fa_per_day)
test_results = [r for r in results if r.get("dataset") in ("test", "eval_suite") and "event_recall" in r]

# Prepare data for plotting
detectors = []
event_recalls = []
event_recall_ci_low = []
event_recall_ci_high = []
fa_per_day = []

# Order: Z-Score, EWMA-Z, Isolation Forest, Hybrid
model_order = [
    "Z-Score Baseline",
    "Adaptive EWMA-Z",
    "Isolation Forest",
    "Hybrid (IF + EWMA-Z)",
]

for model in model_order:
    # Get test set result
    test_r = next((r for r in test_results if r["dataset"] == "test" and r["model"] == model), None)
    if test_r:
        detectors.append(model)
        event_recalls.append(test_r.get("event_recall", 0))
        event_recall_ci_low.append(test_r.get("bootstrap_ci_low", 0))
        event_recall_ci_high.append(test_r.get("bootstrap_ci_high", 0))
        fa_per_day.append(test_r.get("false_alarms_per_day", 0))

# Figure 1: Event-Level Recall with 95% CI
fig, ax = plt.subplots(figsize=(10, 6))

x = np.arange(len(detectors))
width = 0.6

bars = ax.bar(x, event_recalls, width, color=['#1D5C8C', '#1D5C8C', '#9B2C2C', '#9B2C2C'], 
              edgecolor='white', linewidth=1.5, label='Event Recall')

# Error bars for CI (ensure positive values)
for i, (low, high) in enumerate(zip(event_recall_ci_low, event_recall_ci_high)):
    yerr_low = max(0, event_recalls[i] - low)
    yerr_high = max(0, high - event_recalls[i])
    if yerr_low > 0 or yerr_high > 0:
        ax.errorbar(i, event_recalls[i], yerr=[[yerr_low], [yerr_high]],
                    fmt='none', color='black', capsize=5, capthick=2, linewidth=1.5)

# Add value labels on bars
for i, (val, low, high) in enumerate(zip(event_recalls, event_recall_ci_low, event_recall_ci_high)):
    ax.text(i, val + 0.02, f'{val:.3f}', ha='center', va='bottom', fontweight='bold', fontsize=11)
    if high - low > 0.5:
        ax.text(i, high + 0.08, '⚠ Wide CI', ha='center', va='bottom', fontsize=9, color='red', style='italic')

ax.set_ylabel('Event-Level Recall', fontsize=13, fontweight='bold')
ax.set_title('Event-Level Recall per Detector (Test Set)\n95% Block Bootstrap CI (2000 resamples, seed 42)', 
             fontsize=14, fontweight='bold', pad=15)
ax.set_xticks(x)
ax.set_xticklabels(detectors, fontsize=11, rotation=15, ha='right')
ax.set_ylim(0, 1.15)
ax.yaxis.grid(True, linestyle='--', alpha=0.5)
ax.set_axisbelow(True)

# Style
for spine in ['top', 'right']:
    ax.spines[spine].set_visible(False)
for spine in ['left', 'bottom']:
    ax.spines[spine].set_linewidth(1.5)

plt.tight_layout()
fig.savefig(PROJECT_ROOT / "results" / "figures" / "event_recall_bar.png", dpi=300, bbox_inches='tight')
print("Saved: results/figures/event_recall_bar.png")

# Figure 2: False Alarms Per Day
fig2, ax2 = plt.subplots(figsize=(10, 6))

# Use log scale for FA/day due to large range (0 to ~800)
colors = ['#1D5C8C', '#1D5C8C', '#9B2C2C', '#9B2C2C']
bars2 = ax2.bar(x, fa_per_day, width, color=colors, edgecolor='white', linewidth=1.5)

# Value labels
for i, val in enumerate(fa_per_day):
    if val > 0:
        ax2.text(i, val * 1.1 if val > 10 else val + 10, f'{val:.1f}', ha='center', va='bottom', 
                 fontweight='bold', fontsize=11)
    else:
        ax2.text(i, 5, '0.0', ha='center', va='bottom', fontweight='bold', fontsize=11)

ax2.set_ylabel('False Alarms Per Day (Log Scale)', fontsize=13, fontweight='bold')
ax2.set_title('False Alarms Per Day on Normal Baseline (Test Set)\n(Log scale — Hybrid/IF ~793, EWMA-Z/Z-Score = 0)', 
              fontsize=14, fontweight='bold', pad=15)
ax2.set_xticks(x)
ax2.set_xticklabels(detectors, fontsize=11, rotation=15, ha='right')
ax2.set_yscale('log')
ax2.set_ylim(0.1, 2000)
ax2.yaxis.grid(True, which='both', linestyle='--', alpha=0.5)
ax2.set_axisbelow(True)

# Add note about Hybrid/IF high FA
ax2.annotate('Hybrid & IF: ~793 FA/day\n(due to single thermal event\nin 1.4 min test window →\nextrapolated to 24h)',
             xy=(3, 792.7), xytext=(2.5, 500),
             arrowprops=dict(arrowstyle='->', color='red', lw=2),
             fontsize=10, color='red', fontweight='bold',
             bbox=dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor='red', alpha=0.9))

for spine in ['top', 'right']:
    ax2.spines[spine].set_visible(False)
for spine in ['left', 'bottom']:
    ax2.spines[spine].set_linewidth(1.5)

plt.tight_layout()
fig2.savefig(PROJECT_ROOT / "results" / "figures" / "fa_per_day_bar.png", dpi=300, bbox_inches='tight')
print("Saved: results/figures/fa_per_day_bar.png")

print("\nFigures generated successfully at 300 DPI!")