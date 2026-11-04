"""
Rebuild engineered features with session-aware fix.

This script processes three datasets (normal, pilot, test) and creates
session-aware features:
- Change features (diff) computed INSIDE each session
- Rolling features (mean, std) computed INSIDE each session with min_periods=2
- No cross-gap contamination
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Constants
GAP_THRESHOLD = 10   # seconds; matches the earlier saved features
ROLL_MIN = 2         # min_periods for rolling windows (allows partial windows)

# Input files
inputs = {
    'normal': 'data/processed/normal_data_training_candidate.csv',
    'pilot':  'data/processed/pilot_data_prepared.csv',
    'test':   'data/processed/test_data_with_labels.csv',
}

# Output folder
out_dir = Path('data/processed/features_v2')
out_dir.mkdir(parents=True, exist_ok=True)

# 14 feature columns (same as before)
feature_cols = [
    'temperature', 'humidity',
    'temperature_change', 'humidity_change',
    'temperature_abs_change', 'humidity_abs_change',
    'temp_rolling_mean_5', 'temp_rolling_std_5',
    'hum_rolling_mean_5', 'hum_rolling_std_5',
    'temp_rolling_mean_15', 'temp_rolling_std_15',
    'hum_rolling_mean_15', 'hum_rolling_std_15',
]

# Process each dataset
for name, path in inputs.items():
    print(f'\n=== Processing {name} ===')

    # a. Read CSV, convert timestamp, sort, reset index
    df = pd.read_csv(path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp', kind='stable').reset_index(drop=True)

    # b. Create time_diff = timestamp.diff().dt.total_seconds()
    df['time_diff'] = df['timestamp'].diff().dt.total_seconds()

    # c. Create session_id FIRST: (time_diff > GAP_THRESHOLD).cumsum()
    #    First row has NaN time_diff -> cumsum treats False as 0 -> session 0
    df['session_id'] = (df['time_diff'] > GAP_THRESHOLD).cumsum()
    # Fill NaN (first row) with 0 and convert to int
    df['session_id'] = df['session_id'].fillna(0).astype(int)

    # d. Change features computed INSIDE each session
    #    groupby('session_id')['col'].diff() computes diff within each session
    df['temperature_change'] = df.groupby('session_id')['temperature'].diff()
    df['humidity_change'] = df.groupby('session_id')['humidity'].diff()
    df['temperature_abs_change'] = df['temperature_change'].abs()
    df['humidity_abs_change'] = df['humidity_change'].abs()

    # e. Rolling features grouped by session, windows 5 and 15, min_periods=ROLL_MIN
    #    Rolling after groupby returns a MultiIndex (session_id, original_index).
    #    We use .reset_index(level=0, drop=True) to drop the session_id level
    #    and keep the original index aligned with df.
    #    Window 5
    df['temp_rolling_mean_5'] = (
        df.groupby('session_id')['temperature']
          .rolling(window=5, min_periods=ROLL_MIN)
          .mean()
          .reset_index(level=0, drop=True)
    )
    df['temp_rolling_std_5'] = (
        df.groupby('session_id')['temperature']
          .rolling(window=5, min_periods=ROLL_MIN)
          .std()
          .reset_index(level=0, drop=True)
    )
    df['hum_rolling_mean_5'] = (
        df.groupby('session_id')['humidity']
          .rolling(window=5, min_periods=ROLL_MIN)
          .mean()
          .reset_index(level=0, drop=True)
    )
    df['hum_rolling_std_5'] = (
        df.groupby('session_id')['humidity']
          .rolling(window=5, min_periods=ROLL_MIN)
          .std()
          .reset_index(level=0, drop=True)
    )
    # Window 15
    df['temp_rolling_mean_15'] = (
        df.groupby('session_id')['temperature']
          .rolling(window=15, min_periods=ROLL_MIN)
          .mean()
          .reset_index(level=0, drop=True)
    )
    df['temp_rolling_std_15'] = (
        df.groupby('session_id')['temperature']
          .rolling(window=15, min_periods=ROLL_MIN)
          .std()
          .reset_index(level=0, drop=True)
    )
    df['hum_rolling_mean_15'] = (
        df.groupby('session_id')['humidity']
          .rolling(window=15, min_periods=ROLL_MIN)
          .mean()
          .reset_index(level=0, drop=True)
    )
    df['hum_rolling_std_15'] = (
        df.groupby('session_id')['humidity']
          .rolling(window=15, min_periods=ROLL_MIN)
          .std()
          .reset_index(level=0, drop=True)
    )

    # f. Before dropping, print NaN counts in 14 feature columns and rows per session
    print(f'  Rows before dropna: {len(df)}')
    nan_counts = df[feature_cols].isna().sum()
    total_nan_rows = df[feature_cols].isna().any(axis=1).sum()
    print(f'  Rows with >=1 NaN in 14 feature cols: {total_nan_rows}')
    for col in feature_cols:
        if nan_counts[col] > 0:
            print(f'    {col}: {nan_counts[col]} NaN')
    session_counts = df['session_id'].value_counts().sort_index()
    print(f'  Sessions: {len(session_counts)}')
    for sid, cnt in session_counts.items():
        print(f'    session {sid}: {cnt} rows')

    # g. Drop rows with any NaN in the 14 feature columns
    df_clean = df.dropna(subset=feature_cols).copy()
    print(f'  Rows after dropna: {len(df_clean)}')

    # h. Save to new folder
    #    {name}_features.csv: 14 feature columns only
    #    {name}_features_full.csv: 14 features + timestamp, time_diff, session_id, and label (for test)
    feature_only = df_clean[feature_cols]
    feature_only.to_csv(out_dir / f'{name}_features.csv', index=False)

    full_cols = feature_cols + ['timestamp', 'time_diff', 'session_id']
    if 'label' in df_clean.columns:
        full_cols.append('label')
    df_clean[full_cols].to_csv(out_dir / f'{name}_features_full.csv', index=False)

    print(f'  Saved: {out_dir / f"{name}_features.csv"} ({len(feature_only)} rows)')
    print(f'  Saved: {out_dir / f"{name}_features_full.csv"} ({len(df_clean)} rows)')

print('\n=== Done ===')