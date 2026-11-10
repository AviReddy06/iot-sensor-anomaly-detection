#!/usr/bin/env python3
"""
evaluate/benchmark_external.py
Benchmark the pipeline architecture on two public indoor temperature/humidity datasets,
kept strictly isolated from ESP32 room calibration:

  1) UCI Occupancy Detection (#357) [Candanedo & Feldheim, 2016] - 60s indoor telemetry
  2) IoTsec Room-Climate-Datasets (Location A/B/C, ESORICS 2017) - sub-minute multi-node telemetry

Caches downloaded data in `data/benchmarks/` and updates `external_benchmarks` inside
`models/evaluation_summary.json` without modifying ESP32 model weights (`models/*.joblib`).
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any, Dict, Tuple
import zipfile

import numpy as np
import pandas as pd
import requests
from sklearn.ensemble import IsolationForest
from sklearn.metrics import precision_recall_fscore_support, roc_auc_score, average_precision_score
from sklearn.preprocessing import StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import config
from features.feature_engine import (
    MODEL_FEATURE_COLS,
    apply_gated_persistence,
    build_features,
    compute_adaptive_ewma_z,
)


UCI_URL = "https://archive.ics.uci.edu/static/public/357/occupancy+detection.zip"
IOTSEC_BASE = "https://raw.githubusercontent.com/IoTsec/Room-Climate-Datasets/master"


def ensure_uci_cached(bench_dir: Path) -> Path:
    zip_path = bench_dir / "occupancy_detection_357.zip"
    if not zip_path.exists():
        print(f"Downloading UCI #357 to {zip_path}...")
        resp = requests.get(UCI_URL, timeout=60)
        resp.raise_for_status()
        zip_path.write_bytes(resp.content)
    return zip_path


def ensure_iotsec_cached(bench_dir: Path, loc: str, meas: str) -> Path:
    csv_path = bench_dir / f"room_climate_{loc}_{meas}.csv"
    if not csv_path.exists():
        url = f"{IOTSEC_BASE}/datasets-location_{loc}/room_climate-location_{loc}-measurement{meas}.csv"
        print(f"Downloading IoTsec {loc}-{meas} to {csv_path}...")
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        csv_path.write_bytes(resp.content)
    return csv_path


def inject_faults_on_clean_trace(
    clean_df: pd.DataFrame,
    seed: int = 101,
    temp_amp: float = 3.5,
    hum_amp: float = 12.0,
) -> pd.DataFrame:
    """Inject realistic sensor fault episodes onto unoccupied baseline telemetry for fair domain benchmarking."""
    rng = np.random.default_rng(seed)
    out = clean_df.sort_values("timestamp", kind="stable").reset_index(drop=True).copy()
    out["label"] = 0
    n = len(out)
    if n < 120:
        raise ValueError(f"Expected >= 120 baseline rows for benchmark injection, got {n}")

    # Inject 4 realistic anomaly episodes across unseen clean rows
    episodes = [
        (int(n * 0.15), max(8, int(n * 0.04)), "spike"),
        (int(n * 0.38), max(10, int(n * 0.05)), "offset"),
        (int(n * 0.62), max(14, int(n * 0.07)), "drift"),
        (int(n * 0.82), max(8, int(n * 0.04)), "chatter"),
    ]
    for s_idx, length, kind in episodes:
        e_idx = min(n, s_idx + length)
        k = e_idx - s_idx
        t0 = float(out.loc[s_idx - 1, "temperature"])
        h0 = float(out.loc[s_idx - 1, "humidity"])
        p = np.linspace(0, 1, k)
        if kind == "spike":
            env = np.sin(np.pi * p) ** 0.7
            out.loc[s_idx : e_idx - 1, "temperature"] = t0 + temp_amp * env
            out.loc[s_idx : e_idx - 1, "humidity"] = np.clip(h0 + hum_amp * env, 0, 100)
        elif kind == "offset":
            out.loc[s_idx : e_idx - 1, "temperature"] = out.loc[s_idx : e_idx - 1, "temperature"] + temp_amp
            out.loc[s_idx : e_idx - 1, "humidity"] = np.clip(out.loc[s_idx : e_idx - 1, "humidity"] - hum_amp * 0.7, 0, 100)
        elif kind == "drift":
            out.loc[s_idx : e_idx - 1, "temperature"] = out.loc[s_idx : e_idx - 1, "temperature"] + np.linspace(0.5, temp_amp * 1.2, k)
            out.loc[s_idx : e_idx - 1, "humidity"] = np.clip(out.loc[s_idx : e_idx - 1, "humidity"] + np.linspace(2.0, hum_amp, k), 0, 100)
        elif kind == "chatter":
            out.loc[s_idx : e_idx - 1, "temperature"] = t0 + rng.choice([-1.5, 1.6, -2.0, 2.0], size=k)
            out.loc[s_idx : e_idx - 1, "humidity"] = np.clip(h0 + rng.choice([-5.0, 5.5, -7.0, 7.0], size=k), 0, 100)
        out.loc[s_idx : e_idx - 1, "label"] = 1

    return out


def score_domain(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    gap_threshold: float,
    short_sec: float,
    long_sec: float,
    ewma_sec: float,
    macro_gap: float,
) -> Dict[str, Any]:
    """Fit domain-isolated scalers & detectors on train_df and score test_df."""
    feat_tr = build_features(
        train_df,
        gap_threshold=gap_threshold,
        roll_min=2,
        short_window_sec=short_sec,
        long_window_sec=long_sec,
        ewma_halflife_sec=ewma_sec,
        ewma_macro_gap_sec=macro_gap,
    )
    feat_te = build_features(
        test_df,
        gap_threshold=gap_threshold,
        roll_min=2,
        short_window_sec=short_sec,
        long_window_sec=long_sec,
        ewma_halflife_sec=ewma_sec,
        ewma_macro_gap_sec=macro_gap,
    )

    scaler = StandardScaler()
    X_tr = scaler.fit_transform(feat_tr[MODEL_FEATURE_COLS])
    X_te = scaler.transform(feat_te[MODEL_FEATURE_COLS])

    iso = IsolationForest(n_estimators=200, random_state=42, contamination="auto", n_jobs=-1)
    iso.fit(X_tr)
    if_th = float(np.percentile(iso.decision_function(X_tr), 0.5))

    ewma_t_std = max(float(feat_tr["temp_ewma_residual"].std()), 0.10)
    ewma_h_std = max(float(feat_tr["hum_ewma_residual"].std()), 0.30)
    ez_tr = compute_adaptive_ewma_z(feat_tr, ewma_t_std, ewma_h_std)
    ez_th = max(3.5, float(np.percentile(ez_tr, 99.7)))

    raw_t_mean, raw_t_std = float(feat_tr["temperature"].mean()), max(float(feat_tr["temperature"].std()), 0.1)
    raw_h_mean, raw_h_std = float(feat_tr["humidity"].mean()), max(float(feat_tr["humidity"].std()), 0.1)

    y = feat_te["label"].to_numpy(dtype=int)

    # Z-score baseline
    z_val = np.maximum(
        np.abs((feat_te["temperature"] - raw_t_mean) / raw_t_std),
        np.abs((feat_te["humidity"] - raw_h_mean) / raw_h_std),
    ).to_numpy()
    z_pred = (z_val > 3.0).astype(int)

    # Adaptive EWMA-Z (calibrated strictly on domain training distribution)
    ez_val = compute_adaptive_ewma_z(feat_te, ewma_t_std, ewma_h_std)
    ez_pred = (ez_val > ez_th).astype(int)

    # Isolation Forest + persistence
    if_scores = iso.decision_function(X_te)
    if_pred = apply_gated_persistence(if_scores < if_th, feat_te["session_id"].to_numpy(), features_df=feat_te).astype(int)

    # Hybrid (IF | EWMA-Z)
    hyb_pred = ((if_pred == 1) | (ez_pred == 1)).astype(int)
    hyb_cont = np.maximum(ez_val / max(ez_th, 1e-6), np.clip((-if_scores + if_th) * 5.0 + 1.0, 0, 10))

    metrics: Dict[str, Any] = {"train_rows": int(len(feat_tr)), "test_rows": int(len(feat_te)), "anomalies": int(y.sum()), "models": {}}
    for name, pred, cont in [
        ("Z-Score Baseline", z_pred, z_val),
        ("Adaptive EWMA-Z", ez_pred, ez_val),
        ("Isolation Forest", if_pred, -if_scores),
        ("Hybrid (IF + EWMA-Z)", hyb_pred, hyb_cont),
    ]:
        p, r, f1, _ = precision_recall_fscore_support(y, pred, average="binary", zero_division=0)
        metrics["models"][name] = {
            "precision": round(float(p), 4),
            "recall": round(float(r), 4),
            "f1": round(float(f1), 4),
            "pr_auc": round(float(average_precision_score(y, cont)), 4),
            "roc_auc": round(float(roc_auc_score(y, cont)), 4),
            "fp": int(((pred == 1) & (y == 0)).sum()),
            "fn": int(((pred == 0) & (y == 1)).sum()),
        }
    return metrics


def run_external_benchmarks() -> Dict[str, Any]:
    """Run external domain benchmarks on UCI #357 and IoTsec Room Climate datasets."""
    bench_dir = config.benchmarks_dir
    bench_dir.mkdir(parents=True, exist_ok=True)
    external_results: Dict[str, Any] = {}

    # ------------------------------------------------------------
    # Benchmark 1: UCI Occupancy Detection (#357) [60s cadence]
    # Use continuous weekend unoccupied segments (no artificial gap-splicing)
    # ------------------------------------------------------------
    zip_path = ensure_uci_cached(bench_dir)
    with zipfile.ZipFile(zip_path) as zf:
        uci_train_raw = pd.read_csv(zf.open("datatraining.txt"))
        uci_test2_raw = pd.read_csv(zf.open("datatest2.txt"))

    def longest_clean_run(df: pd.DataFrame) -> pd.DataFrame:
        work = df.copy()
        work["occ_grp"] = (work["Occupancy"] != work["Occupancy"].shift()).cumsum()
        best_grp = work[work["Occupancy"] == 0].groupby("occ_grp").size().idxmax()
        sub = work[work["occ_grp"] == best_grp][["date", "Temperature", "Humidity"]].rename(
            columns={"date": "timestamp", "Temperature": "temperature", "Humidity": "humidity"}
        )
        sub["timestamp"] = pd.to_datetime(sub["timestamp"])
        return sub.sort_values("timestamp", kind="stable").reset_index(drop=True)

    uci_train = longest_clean_run(uci_train_raw)
    uci_base = longest_clean_run(uci_test2_raw)
    uci_eval = inject_faults_on_clean_trace(uci_base.iloc[:2000], seed=357, temp_amp=3.2, hum_amp=10.0)
    uci_res = score_domain(
        uci_train,
        uci_eval,
        gap_threshold=180.0,   # 3 min gap at 60s sampling
        short_sec=300.0,       # 5 min short rolling window
        long_sec=900.0,        # 15 min long window
        ewma_sec=14400.0,      # 4h baseline EWMA
        macro_gap=7200.0,
    )
    external_results["UCI_Occupancy_357"] = {
        "source": "UCI ML Repository #357 (60s cadence, Temp+RH only, isolated calibration)",
        **uci_res,
    }

    # ------------------------------------------------------------
    # Benchmark 2: IoTsec Room Climate (ESORICS 2017) [Node 1]
    # ------------------------------------------------------------
    a_train_path = ensure_iotsec_cached(bench_dir, "A", "01")
    a_test_path = ensure_iotsec_cached(bench_dir, "A", "06")

    def load_iotsec_single_node(path: Path, node_id: int = 1) -> pd.DataFrame:
        raw = pd.read_csv(path, header=None)
        sub = raw[raw[3] == node_id].copy()
        df = pd.DataFrame({
            "timestamp": pd.to_datetime(sub[1], unit="ms"),
            "temperature": pd.to_numeric(sub[4], errors="coerce"),
            "humidity": pd.to_numeric(sub[5], errors="coerce"),
        }).dropna()
        return df.sort_values("timestamp", kind="stable").reset_index(drop=True)

    iot_train = load_iotsec_single_node(a_train_path, node_id=1)
    iot_base = load_iotsec_single_node(a_test_path, node_id=1)
    iot_eval = inject_faults_on_clean_trace(iot_base, seed=2017, temp_amp=3.0, hum_amp=11.0)
    iot_res = score_domain(
        iot_train,
        iot_eval,
        gap_threshold=20.0,
        short_sec=20.0,
        long_sec=60.0,
        ewma_sec=2400.0,
        macro_gap=1800.0,
    )
    external_results["IoTsec_Room_Climate"] = {
        "source": "IoTsec Room-Climate-Datasets (Location A Node 1, ESORICS 2017, isolated calibration)",
        **iot_res,
    }

    # Update models/evaluation_summary.json cleanly
    summary_path = config.model_dir / "evaluation_summary.json"
    summary_data: Dict[str, Any] = {}
    if summary_path.exists():
        summary_data = json.loads(summary_path.read_text(encoding="utf-8"))
    summary_data["external_benchmarks"] = external_results
    summary_path.write_text(json.dumps(summary_data, indent=2), encoding="utf-8")

    print("\n=== EXTERNAL BENCHMARKS (STRICTLY ISOLATED CALIBRATION) ===")
    for ds_name, info in external_results.items():
        print(f"\n[{ds_name}] train={info['train_rows']}, test={info['test_rows']}, anomalies={info['anomalies']}")
        for mname, m in info["models"].items():
            print(
                f"  {mname:22s} | P={m['precision']:.3f} R={m['recall']:.3f} F1={m['f1']:.3f} "
                f"| PR={m['pr_auc']:.3f} ROC={m['roc_auc']:.3f} | FP={m['fp']:3d} FN={m['fn']:3d}"
            )

    return external_results


if __name__ == "__main__":
    run_external_benchmarks()
