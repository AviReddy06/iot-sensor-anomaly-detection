"""
features/feature_engine.py
Shared, time-aware, session-aware feature engineering and detection post-processing module.

Used identically by batch scripts (features/build_features_v2.py, training, evaluation)
and real-time / uploaded CSV scoring in the Streamlit dashboards.
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import config


RAW_COLS: List[str] = ["temperature", "humidity"]

MODEL_FEATURE_COLS: List[str] = [
    "temp_ewma_residual",
    "hum_ewma_residual",
    "temp_ewma_abs_residual",
    "hum_ewma_abs_residual",
    "ewma_joint_norm",
    "temp_rate",
    "hum_rate",
    "rate_joint_norm",
    "temp_rolling_std_10s",
    "hum_rolling_std_10s",
    "temp_jitter_10s",
    "hum_jitter_10s",
]


def default_feature_params() -> Dict[str, Any]:
    """Return default feature engineering parameters from config.yaml."""
    return {
        "gap_threshold": config.gap_threshold_sec,
        "roll_min": config.roll_min,
        "short_window_sec": config.short_window_sec,
        "long_window_sec": config.long_window_sec,
        "ewma_halflife_sec": config.ewma_halflife_sec,
        "ewma_macro_gap_sec": config.ewma_macro_gap_sec,
    }


def _compute_gated_ewma_baseline(
    temps: np.ndarray,
    hums: np.ndarray,
    trates: np.ndarray,
    hrates: np.ndarray,
    tdiffs: np.ndarray,
    ewma_sec: float,
    macro_gap: float,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Causal rate-gated + Cauchy-weighted EWMA baseline tracker.

    - Adapts smoothly to gradual room/diurnal ambient shifts across hours.
    - Suppresses baseline updates during sudden thermal/breath excursions so sustained
      anomalies (10-30+ minutes) do not poison the baseline or cause false post-recovery spikes.
    - Resets cleanly when an offline gap exceeds `macro_gap` seconds.
    """
    n = len(temps)
    base_t = np.zeros(n, dtype=float)
    base_h = np.zeros(n, dtype=float)
    if n == 0:
        return base_t, base_h

    curr_t = float(temps[0])
    curr_h = float(hums[0])
    base_t[0] = curr_t
    base_h[0] = curr_h

    for i in range(1, n):
        dt_m = float(tdiffs[i])
        if dt_m > macro_gap:
            curr_t = float(temps[i])
            curr_h = float(hums[i])
        else:
            if trates[i] <= 0.10 and hrates[i] <= 0.35:
                et = abs(float(temps[i]) - curr_t)
                eh = abs(float(hums[i]) - curr_h)
                w_t = 1.0 / (1.0 + (et / 2.0) ** 4)
                w_h = 1.0 / (1.0 + (eh / 7.0) ** 4)
                w_joint = min(w_t, w_h)
                alpha = 1.0 - 0.5 ** (max(dt_m, 1.0) / max(ewma_sec, 1.0))
                eff_alpha = alpha * w_joint
                curr_t = (1.0 - eff_alpha) * curr_t + eff_alpha * float(temps[i])
                curr_h = (1.0 - eff_alpha) * curr_h + eff_alpha * float(hums[i])
        base_t[i] = curr_t
        base_h[i] = curr_h

    return base_t, base_h


def build_features(
    df: pd.DataFrame,
    gap_threshold: Optional[float] = None,
    roll_min: Optional[int] = None,
    short_window_sec: Optional[float] = None,
    long_window_sec: Optional[float] = None,
    ewma_halflife_sec: Optional[float] = None,
    ewma_macro_gap_sec: Optional[float] = None,
) -> pd.DataFrame:
    """
    Build time-aware, session-aware features from raw `(timestamp, temperature, humidity)` data.

    - Splits continuous measurement sessions whenever elapsed gap > `gap_threshold` seconds.
    - Guards burst duplicates safely (`dt_eff = max(dt, 1.0)`).
    - Tracks drift-aware baseline via causal rate-gated Cauchy EWMA (`ewma_halflife_sec`).
    - Measures short-window dispersion (`short_window_sec`), second-order reversal jitter,
      and joint physical excursion norms.
    """
    params = default_feature_params()
    gap_th = float(params["gap_threshold"] if gap_threshold is None else gap_threshold)
    min_p = int(params["roll_min"] if roll_min is None else roll_min)
    short_sec = float(params["short_window_sec"] if short_window_sec is None else short_window_sec)
    long_sec = float(params["long_window_sec"] if long_window_sec is None else long_window_sec)
    ewma_sec = float(params["ewma_halflife_sec"] if ewma_halflife_sec is None else ewma_halflife_sec)
    macro_gap = float(params["ewma_macro_gap_sec"] if ewma_macro_gap_sec is None else ewma_macro_gap_sec)

    work = df.copy()
    work["timestamp"] = pd.to_datetime(work["timestamp"], errors="coerce")
    work["temperature"] = pd.to_numeric(work["temperature"], errors="coerce")
    work["humidity"] = pd.to_numeric(work["humidity"], errors="coerce")
    work = work.dropna(subset=["timestamp", "temperature", "humidity"])
    work = work.sort_values("timestamp", kind="stable").reset_index(drop=True)

    extra_cols = ["temp_abs_rate", "hum_abs_rate", "temp_local_dev_30s", "hum_local_dev_30s"]
    if len(work) == 0:
        return pd.DataFrame(columns=RAW_COLS + MODEL_FEATURE_COLS + extra_cols + ["timestamp", "time_diff", "session_id"])

    work["time_diff"] = work["timestamp"].diff().dt.total_seconds()
    work["session_id"] = (work["time_diff"] > gap_th).cumsum().fillna(0).astype(int)

    session_dt = work.groupby("session_id")["timestamp"].diff().dt.total_seconds()
    dt_eff = session_dt.clip(lower=1.0)

    temp_diff = work.groupby("session_id")["temperature"].diff()
    hum_diff = work.groupby("session_id")["humidity"].diff()
    work["temp_rate"] = temp_diff / dt_eff
    work["hum_rate"] = hum_diff / dt_eff
    work["temp_abs_rate"] = work["temp_rate"].abs()
    work["hum_abs_rate"] = work["hum_rate"].abs()

    # Second-order curvature / reversal jitter (small on monotonic ambient drift, large on chatter/spikes)
    work["temp_rev_jitter"] = (temp_diff - temp_diff.groupby(work["session_id"]).shift(1)).abs().fillna(0.0)
    work["hum_rev_jitter"] = (hum_diff - hum_diff.groupby(work["session_id"]).shift(1)).abs().fillna(0.0)

    # Causal rate-gated Cauchy-weighted baseline EWMA
    temps = work["temperature"].to_numpy(dtype=float)
    hums = work["humidity"].to_numpy(dtype=float)
    trates = work["temp_abs_rate"].fillna(0.0).to_numpy(dtype=float)
    hrates = work["hum_abs_rate"].fillna(0.0).to_numpy(dtype=float)
    tdiffs = work["time_diff"].fillna(0.0).to_numpy(dtype=float)

    base_t, base_h = _compute_gated_ewma_baseline(
        temps, hums, trates, hrates, tdiffs, ewma_sec=ewma_sec, macro_gap=macro_gap
    )
    work["temp_ewma_residual"] = temps - base_t
    work["hum_ewma_residual"] = hums - base_h
    work["temp_ewma_abs_residual"] = np.abs(work["temp_ewma_residual"])
    work["hum_ewma_abs_residual"] = np.abs(work["hum_ewma_residual"])

    # Time-based rolling dispersion and local deviation within each session
    short_win = f"{max(1, int(round(short_sec)))}s"
    long_win = f"{max(2, int(round(long_sec)))}s"

    for col in (
        "temp_rolling_std_10s",
        "hum_rolling_std_10s",
        "temp_local_dev_30s",
        "hum_local_dev_30s",
        "temp_jitter_10s",
        "hum_jitter_10s",
    ):
        work[col] = np.nan

    for _, grp in work.groupby("session_id", sort=False):
        idx = grp.index
        ts_idx = pd.DatetimeIndex(grp["timestamp"])
        t_ser = pd.Series(grp["temperature"].to_numpy(), index=ts_idx)
        h_ser = pd.Series(grp["humidity"].to_numpy(), index=ts_idx)
        tj_ser = pd.Series(grp["temp_rev_jitter"].to_numpy(), index=ts_idx)
        hj_ser = pd.Series(grp["hum_rev_jitter"].to_numpy(), index=ts_idx)

        work.loc[idx, "temp_rolling_std_10s"] = t_ser.rolling(short_win, min_periods=min_p).std(ddof=1).fillna(0.0).to_numpy()
        work.loc[idx, "hum_rolling_std_10s"] = h_ser.rolling(short_win, min_periods=min_p).std(ddof=1).fillna(0.0).to_numpy()
        work.loc[idx, "temp_local_dev_30s"] = grp["temperature"].to_numpy() - t_ser.rolling(long_win, min_periods=min_p).mean().to_numpy()
        work.loc[idx, "hum_local_dev_30s"] = grp["humidity"].to_numpy() - h_ser.rolling(long_win, min_periods=min_p).mean().to_numpy()
        work.loc[idx, "temp_jitter_10s"] = tj_ser.rolling(short_win, min_periods=1).mean().to_numpy()
        work.loc[idx, "hum_jitter_10s"] = hj_ser.rolling(short_win, min_periods=1).mean().to_numpy()

    # Physical joint L2 norms for excursion and rate
    work["ewma_joint_norm"] = np.sqrt(
        (work["temp_ewma_abs_residual"] / 0.5) ** 2 + (work["hum_ewma_abs_residual"] / 2.0) ** 2
    )
    work["rate_joint_norm"] = np.sqrt(
        (work["temp_abs_rate"] / 0.05) ** 2 + (work["hum_abs_rate"] / 0.2) ** 2
    )

    required = RAW_COLS + MODEL_FEATURE_COLS
    work = work.dropna(subset=required).reset_index(drop=True)

    output_cols = RAW_COLS + MODEL_FEATURE_COLS + extra_cols + ["timestamp", "time_diff", "session_id"]
    for extra in ("label", "fault_type", "source_session"):
        if extra in work.columns:
            output_cols.append(extra)

    return work[output_cols]


def apply_gated_persistence(
    flags: np.ndarray,
    session_ids: np.ndarray,
    features_df: Optional[pd.DataFrame] = None,
    window: Optional[int] = None,
    min_hits: Optional[int] = None,
) -> np.ndarray:
    """
    Filter transient single-row jitter while preserving genuine sudden spikes.

    A sample is confirmed anomalous only when `flags[i]` is True AND either:
      1) At least `min_hits` samples in the trailing `window` within the same session are flagged, OR
      2) A sharp physical jump/excursion is directly observed at row `i`.
    """
    win = int(config.get("detection.persistence_window", 5) if window is None else window)
    hits_req = int(config.get("detection.persistence_min_hits", 3) if min_hits is None else min_hits)

    flags_arr = np.asarray(flags, dtype=bool)
    sess_arr = np.asarray(session_ids)
    out = np.zeros(len(flags_arr), dtype=bool)
    if len(flags_arr) == 0:
        return out

    sharp_mask = np.zeros(len(flags_arr), dtype=bool)
    if features_df is not None:
        t_rate = features_df["temp_abs_rate"].to_numpy(dtype=float) if "temp_abs_rate" in features_df else features_df["temp_rate"].abs().to_numpy(dtype=float)
        h_rate = features_df["hum_abs_rate"].to_numpy(dtype=float) if "hum_abs_rate" in features_df else features_df["hum_rate"].abs().to_numpy(dtype=float)
        t_res = features_df["temp_ewma_abs_residual"].to_numpy(dtype=float)
        h_res = features_df["hum_ewma_abs_residual"].to_numpy(dtype=float)
        sharp_mask = (t_rate >= 0.4) | (h_rate >= 1.5) | (t_res >= 2.5) | (h_res >= 9.0)

    for sid in np.unique(sess_arr):
        idx = np.where(sess_arr == sid)[0]
        f = flags_arr[idx].astype(int)
        csum = np.cumsum(f)
        hits = csum.copy()
        if win < len(f):
            hits[win:] = csum[win:] - csum[:-win]
        confirmed = flags_arr[idx] & ((hits >= hits_req) | sharp_mask[idx])
        out[idx] = confirmed

    return out


def compute_adaptive_ewma_z(
    features_df: pd.DataFrame,
    ewma_temp_std: float,
    ewma_hum_std: float,
) -> np.ndarray:
    """Compute max standardized adaptive EWMA residual across temperature and humidity."""
    t_scale = max(float(ewma_temp_std), 0.25)
    h_scale = max(float(ewma_hum_std), 0.80)
    t_z = np.abs(features_df["temp_ewma_residual"].to_numpy(dtype=float)) / t_scale
    h_z = np.abs(features_df["hum_ewma_residual"].to_numpy(dtype=float)) / h_scale
    return np.maximum(t_z, h_z)
