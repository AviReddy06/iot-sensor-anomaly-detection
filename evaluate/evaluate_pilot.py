# evaluate/evaluate_pilot.py
# Evaluate saved models on pilot data
# Simple sequential code, no classes or lambda, comment above every step

import pandas as pd
import numpy as np
import joblib
import json
from pathlib import Path
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support

# 1. Load data and models
pilot = pd.read_csv('data/processed/features_v2/pilot_features_full.csv')
pilot['timestamp'] = pd.to_datetime(pilot['timestamp'])
pilot = pilot.sort_values('timestamp', kind='stable').reset_index(drop=True)
print(f'Loaded pilot: {len(pilot)} rows, {pilot["session_id"].nunique()} sessions')
print(f'Time range: {pilot["timestamp"].min()} to {pilot["timestamp"].max()}')
print()

# Load models and thresholds
iso = joblib.load('models/iforest.joblib')
scaler = joblib.load('models/scaler.joblib')
with open('models/thresholds.json', 'r') as f:
    thresholds = json.load(f)

# Load pilot event annotations
annotations = pd.read_csv('data/processed/pilot_event_annotations.csv')
annotations['start_time'] = pd.to_datetime(annotations['start_time'])
annotations['end_time'] = pd.to_datetime(annotations['end_time'])
print('Event annotations:')
print(annotations[['event_id', 'start_time', 'end_time', 'duration_seconds', 'num_rows']].to_string())
print()

# 2. Build row-level label: 1 if timestamp between any event's start and end (inclusive)
labels = pd.Series(0, index=pilot.index, dtype=int)
for _, row in annotations.iterrows():
    mask = (pilot['timestamp'] >= row['start_time']) & (pilot['timestamp'] <= row['end_time'])
    labels[mask] = 1

print('Label distribution:')
print(labels.value_counts().sort_index())
print()

# 3. Predictions - NO TUNING
feature_cols = thresholds['feature_cols']

# IF predictions
pilot_features = pilot[feature_cols].copy()
pilot_scaled = scaler.transform(pilot_features)
pilot_scores = iso.decision_function(pilot_scaled)
iforest_threshold = thresholds['iforest_threshold']
iforest_flag = pilot_scores < iforest_threshold

# Z-score predictions
z_temp = np.abs((pilot['temperature'] - thresholds['normal_temp_mean']) / thresholds['normal_temp_std'])
z_hum = np.abs((pilot['humidity'] - thresholds['normal_hum_mean']) / thresholds['normal_hum_std'])
zscore_threshold = thresholds['zscore_threshold']
zscore_flag = (z_temp > zscore_threshold) | (z_hum > zscore_threshold)

# 4. Metrics for both methods
y_true = labels.values

# Isolation Forest
cm_if = confusion_matrix(y_true, iforest_flag)
prec_if, rec_if, f1_if, _ = precision_recall_fscore_support(y_true, iforest_flag, average='binary', zero_division=0)

print('=== ISOLATION FOREST ===')
print(f'Confusion matrix (TN, FP, FN, TP): {cm_if[0,0]}, {cm_if[0,1]}, {cm_if[1,0]}, {cm_if[1,1]}')
print(f'Precision: {prec_if:.4f}')
print(f'Recall: {rec_if:.4f}')
print(f'F1: {f1_if:.4f}')
print()

# Z-score
cm_z = confusion_matrix(y_true, zscore_flag)
prec_z, rec_z, f1_z, _ = precision_recall_fscore_support(y_true, zscore_flag, average='binary', zero_division=0)

print('=== Z-SCORE ===')
print(f'Confusion matrix (TN, FP, FN, TP): {cm_z[0,0]}, {cm_z[0,1]}, {cm_z[1,0]}, {cm_z[1,1]}')
print(f'Precision: {prec_z:.4f}')
print(f'Recall: {rec_z:.4f}')
print(f'F1: {f1_z:.4f}')
print()

# Per-event breakdown
print('=== PER-EVENT RECALL ===')
for _, row in annotations.iterrows():
    start = row['start_time']
    end = row['end_time']
    mask = (pilot['timestamp'] >= start) & (pilot['timestamp'] <= end)
    event_indices = pilot.index[mask]
    if len(event_indices) > 0:
        if_caught = iforest_flag[event_indices].sum()
        z_caught = zscore_flag[event_indices].sum()
        print(f'Event {int(row["event_id"])} ({start} to {end}): {len(event_indices)} rows | IF caught: {if_caught} | Z-score caught: {z_caught}')
print()

# 5. False positive split
# (a) within 14 rows after an event ends
# (b) elsewhere

# Find the last row index of each event in the sorted pilot dataframe
event_end_indices = []
for _, row in annotations.iterrows():
    end = row['end_time']
    # Last row with timestamp <= end
    mask = pilot['timestamp'] <= end
    if mask.any():
        event_end_indices.append(pilot.index[mask].max())

# Rows within 14 rows after any event end
within_14_after = set()
for end_idx in event_end_indices:
    next_14 = pilot.index[(pilot.index > end_idx) & (pilot.index <= end_idx + 14)]
    within_14_after.update(next_14)

# False positives
if_fp = iforest_flag & (y_true == 0)
z_fp = zscore_flag & (y_true == 0)

# Split
if_fp_a = if_fp & pilot.index.isin(within_14_after)
if_fp_b = if_fp & (~pilot.index.isin(within_14_after))
z_fp_a = z_fp & pilot.index.isin(within_14_after)
z_fp_b = z_fp & (~pilot.index.isin(within_14_after))

print('=== FALSE POSITIVE SPLIT ===')
print(f'Isolation Forest:')
print(f'  Total FP: {if_fp.sum()}')
print(f'  Group (a) within 14 rows after event: {if_fp_a.sum()}')
print(f'  Group (b) elsewhere: {if_fp_b.sum()}')

print(f'Z-score:')
print(f'  Total FP: {z_fp.sum()}')
print(f'  Group (a) within 14 rows after event: {z_fp_a.sum()}')
print(f'  Group (b) elsewhere: {z_fp_b.sum()}')
print()

# Group (b) stats for both methods
for name, fp_b in [('IF', if_fp_b), ('Z-score', z_fp_b)]:
    if fp_b.sum() > 0:
        subset = pilot[fp_b]
        mean_hum = subset['humidity'].mean()
        share_below_55 = (subset['humidity'] < 55).mean()
        print(f'{name} Group (b): {fp_b.sum()} rows, mean humidity={mean_hum:.2f}, share <55%={share_below_55:.2%}')
    else:
        print(f'{name} Group (b): 0 rows')
print()

# 6. Sanity check on earlier audit: normal data change feature distributions
normal = pd.read_csv('data/processed/features_v2/normal_features_full.csv')
print('=== NORMAL DATA CHANGE FEATURE DISTRIBUTIONS (info only) ===')
print()

for col in ['temperature_change', 'humidity_change']:
    print(f'{col}:')
    vc = normal[col].value_counts().head(10)
    print(f'  Top 10 values:')
    for val, cnt in vc.items():
        print(f'    {val:.4f}: {cnt}')
    print(f'  Distinct values: {normal[col].nunique()}')
    print()

# Robust z-score recomputation for normal data
for col in ['temperature_change', 'humidity_change']:
    median = normal[col].median()
    mad = np.median(np.abs(normal[col] - median))
    if mad == 0:
        mad = 1e-10
    scale = 1.4826 * mad
    robust_z = (normal[col] - median) / scale
    
    for thresh in [5, 8, 12]:
        count = (robust_z.abs() > thresh).sum()
        print(f'  {col}: abs(robust z) > {thresh} -> {count} rows ({count/len(normal)*100:.2f}%)')
    print()

print('=== DONE ===')