# dashboard/feature_utils.py
# Reproduces features/build_features_v2.py exactly as a single plain function.
# Every line has a comment explaining what and why.

import pandas as pd
import numpy as np

def build_features(df, gap_threshold, roll_min):
    """
    Build session-aware features from raw sensor data.
    
    Parameters
    ----------
    df : pandas.DataFrame
        Input dataframe with at least columns: timestamp, temperature, humidity.
        May also have a 'label' column which will be preserved.
    gap_threshold : int or float
        Seconds; any time_diff > gap_threshold starts a new session.
    roll_min : int
        Minimum periods for rolling windows (default 2).
    
    Returns
    -------
    pandas.DataFrame
        DataFrame with 14 feature columns + timestamp + session_id
        (and label if it was present in input).
    """
    # Make a copy to avoid modifying the original
    df = df.copy()
    
    # Ensure timestamp is datetime and sort chronologically
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp', kind='stable').reset_index(drop=True)
    
    # time_diff: seconds between consecutive rows
    df['time_diff'] = df['timestamp'].diff().dt.total_seconds()
    
    # session_id: increments when time_diff > gap_threshold
    # First row has NaN time_diff -> (NaN > threshold) is False -> cumsum stays 0
    df['session_id'] = (df['time_diff'] > gap_threshold).cumsum()
    df['session_id'] = df['session_id'].fillna(0).astype(int)
    
    # Change features computed INSIDE each session (groupby session_id)
    # temperature_change = current - previous within same session
    df['temperature_change'] = df.groupby('session_id')['temperature'].diff()
    # humidity_change = current - previous within same session
    df['humidity_change'] = df.groupby('session_id')['humidity'].diff()
    # Absolute values of change (magnitude only, ignore direction)
    df['temperature_abs_change'] = df['temperature_change'].abs()
    df['humidity_abs_change'] = df['humidity_change'].abs()
    
    # Rolling features grouped by session, windows 5 and 15, min_periods=roll_min
    # groupby(...).rolling(...) returns a MultiIndex; reset_index(level=0, drop=True)
    # drops the session_id level and aligns back to original index.
    # Window 5 - mean
    df['temp_rolling_mean_5'] = (
        df.groupby('session_id')['temperature']
          .rolling(window=5, min_periods=roll_min)
          .mean()
          .reset_index(level=0, drop=True)
    )
    # Window 5 - std
    df['temp_rolling_std_5'] = (
        df.groupby('session_id')['temperature']
          .rolling(window=5, min_periods=roll_min)
          .std()
          .reset_index(level=0, drop=True)
    )
    # Window 5 - mean humidity
    df['hum_rolling_mean_5'] = (
        df.groupby('session_id')['humidity']
          .rolling(window=5, min_periods=roll_min)
          .mean()
          .reset_index(level=0, drop=True)
    )
    # Window 5 - std humidity
    df['hum_rolling_std_5'] = (
        df.groupby('session_id')['humidity']
          .rolling(window=5, min_periods=roll_min)
          .std()
          .reset_index(level=0, drop=True)
    )
    # Window 15 - mean temperature
    df['temp_rolling_mean_15'] = (
        df.groupby('session_id')['temperature']
          .rolling(window=15, min_periods=roll_min)
          .mean()
          .reset_index(level=0, drop=True)
    )
    # Window 15 - std temperature
    df['temp_rolling_std_15'] = (
        df.groupby('session_id')['temperature']
          .rolling(window=15, min_periods=roll_min)
          .std()
          .reset_index(level=0, drop=True)
    )
    # Window 15 - mean humidity
    df['hum_rolling_mean_15'] = (
        df.groupby('session_id')['humidity']
          .rolling(window=15, min_periods=roll_min)
          .mean()
          .reset_index(level=0, drop=True)
    )
    # Window 15 - std humidity
    df['hum_rolling_std_15'] = (
        df.groupby('session_id')['humidity']
          .rolling(window=15, min_periods=roll_min)
          .std()
          .reset_index(level=0, drop=True)
    )
    
    # The 14 feature columns (same as training)
    feature_cols = [
        'temperature', 'humidity',
        'temperature_change', 'humidity_change',
        'temperature_abs_change', 'humidity_abs_change',
        'temp_rolling_mean_5', 'temp_rolling_std_5',
        'hum_rolling_mean_5', 'hum_rolling_std_5',
        'temp_rolling_mean_15', 'temp_rolling_std_15',
        'hum_rolling_mean_15', 'hum_rolling_std_15'
    ]
    
    # Drop rows with any NaN in the 14 feature columns
    # (first row of each session has NaN for change features; 
    # first roll_min-1 rows of each session have NaN for rolling features)
    df = df.dropna(subset=feature_cols).copy()
    
    # Return 14 features + timestamp + session_id (and label if present)
    output_cols = feature_cols + ['timestamp', 'session_id']
    if 'label' in df.columns:
        output_cols.append('label')
    return df[output_cols]