# Train models on session-aware features
# Simple sequential code, no classes, no lambda, no functions
# Every step has a comment explaining what and why

import pandas as pd
import numpy as np
import json
import joblib
from pathlib import Path
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support

# a. Load data and define 14 feature columns
# Load normal training features (no labels)
normal = pd.read_csv('data/processed/features_v2/normal_features.csv')
# Load test features full (has label column)
test_full = pd.read_csv('data/processed/features_v2/test_features_full.csv')
# Load pilot features (no labels)
pilot = pd.read_csv('data/processed/features_v2/pilot_features.csv')

# The 14 feature columns by name (all columns in normal_features.csv are features)
feature_cols = list(normal.columns)
print('Feature columns (14):', feature_cols)
print('Normal shape:', normal.shape)
print('Test shape:', test_full.shape)
print('Pilot shape:', pilot.shape)
print()

# Separate test features and labels
test_features = test_full[feature_cols].copy()
test_labels = test_full['label'].copy()
print('Test label distribution:', test_labels.value_counts().to_dict())
print()

# b. Z-SCORE BASELINE on raw temperature and humidity
# Compute mean and std from NORMAL data only
normal_temp_mean = normal['temperature'].mean()
normal_temp_std = normal['temperature'].std()
normal_hum_mean = normal['humidity'].mean()
normal_hum_std = normal['humidity'].std()

print('Z-score thresholds from normal data:')
print('  temperature: mean=', normal_temp_mean, 'std=', normal_temp_std)
print('  humidity: mean=', normal_hum_mean, 'std=', normal_hum_std)
print()

# Flag a row if abs(z) > 3 in EITHER column
def zscore_flag(df):
    z_temp = np.abs((df['temperature'] - normal_temp_mean) / normal_temp_std)
    z_hum = np.abs((df['humidity'] - normal_hum_mean) / normal_hum_std)
    return (z_temp > 3) | (z_hum > 3)

# Apply to test
test_zscore_flag = zscore_flag(test_features)
print('Z-score flags on test: normal flagged=', test_zscore_flag.sum(), 'out of', len(test_features))
print()

# c. ISOLATION FOREST
# Fit StandardScaler on normal only
scaler = StandardScaler()
normal_scaled = scaler.fit_transform(normal)
test_scaled = scaler.transform(test_features)
pilot_scaled = scaler.transform(pilot)

# IsolationForest on scaled normal only
iso = IsolationForest(n_estimators=200, random_state=42, contamination='auto')
iso.fit(normal_scaled)

# Threshold = 1st percentile of decision_function on normal training data
# This is set BEFORE touching test results
normal_scores = iso.decision_function(normal_scaled)
iforest_threshold = np.percentile(normal_scores, 1)
print('Isolation Forest threshold (1st percentile of normal scores):', iforest_threshold)
print()

# Sensitivity table (0.5, 1, 2, 5 percentile) - NOT USED FOR ANY DECISION
print('Sensitivity table (NOT USED FOR ANY DECISION):')
for p in [0.5, 1, 2, 5]:
    thresh = np.percentile(normal_scores, p)
    print(f'  {p}th percentile: {thresh}')
print()

# Flag if score < threshold
test_iforest_scores = iso.decision_function(test_scaled)
test_iforest_flag = test_iforest_scores < iforest_threshold
print('Isolation Forest flags on test: normal flagged=', test_iforest_flag.sum(), 'out of', len(test_features))
print()

# d. EVALUATE both methods on test set
# True labels: 1 = anomaly, 0 = normal
y_true = test_labels.values

# Z-score evaluation
cm_z = confusion_matrix(y_true, test_zscore_flag)
print('=== Z-SCORE EVALUATION ===')
print('Confusion matrix (rows=true, cols=pred):')
print(cm_z)
prec_z, rec_z, f1_z, _ = precision_recall_fscore_support(y_true, test_zscore_flag, average='binary')
print(f'Precision: {prec_z:.4f}')
print(f'Recall: {rec_z:.4f}')
print(f'F1: {f1_z:.4f}')
print()

# Isolation Forest evaluation
cm_if = confusion_matrix(y_true, test_iforest_flag)
print('=== ISOLATION FOREST EVALUATION ===')
print('Confusion matrix (rows=true, cols=pred):')
print(cm_if)
prec_if, rec_if, f1_if, _ = precision_recall_fscore_support(y_true, test_iforest_flag, average='binary')
print(f'Precision: {prec_if:.4f}')
print(f'Recall: {rec_if:.4f}')
print(f'F1: {f1_if:.4f}')
print()

# List the 10 true-anomaly timestamps and whether each method caught them
print('=== TRUE ANOMALY TIMESTAMPS ===')
anomaly_indices = np.where(y_true == 1)[0]
anomaly_timestamps = test_full.iloc[anomaly_indices]['timestamp'].values
for i, (idx, ts) in enumerate(zip(anomaly_indices, anomaly_timestamps)):
    z_caught = bool(test_zscore_flag[idx])
    if_caught = bool(test_iforest_flag[idx])
    print(f'  {i+1}. {ts} | z-score: {"CAUGHT" if z_caught else "MISSED"} | iforest: {"CAUGHT" if if_caught else "MISSED"}')
print()

# False alarms in TWO groups:
# (i) label-0 rows within 14 rows after the last anomaly row (rolling window contamination)
# (ii) all other label-0 rows
last_anomaly_idx = anomaly_indices[-1]
print(f'Last anomaly index in test: {last_anomaly_idx} (timestamp: {anomaly_timestamps[-1]})')
print('Window of 14 rows after last anomaly: indices', last_anomaly_idx+1, 'to', min(last_anomaly_idx+14, len(test_features)-1))

# Group (i): label-0 rows within 14 rows after last anomaly
window_start = last_anomaly_idx + 1
window_end = min(last_anomaly_idx + 14, len(test_features) - 1)
window_mask = (np.arange(len(test_features)) >= window_start) & (np.arange(len(test_features)) <= window_end)
label0_mask = (y_true == 0)

group1_mask = window_mask & label0_mask
group2_mask = label0_mask & (~window_mask)

print()
print('=== FALSE ALARM GROUPS ===')
print('Group (i) - label-0 within 14 rows after last anomaly:', group1_mask.sum(), 'rows')
print('Group (ii) - all other label-0 rows:', group2_mask.sum(), 'rows')
print()

# False alarms per method
z_false_g1 = test_zscore_flag[group1_mask].sum()
z_false_g2 = test_zscore_flag[group2_mask].sum()
if_false_g1 = test_iforest_flag[group1_mask].sum()
if_false_g2 = test_iforest_flag[group2_mask].sum()

print('Z-score false alarms:')
print(f'  Group (i): {z_false_g1}')
print(f'  Group (ii): {z_false_g2}')
print(f'  Total: {z_false_g1 + z_false_g2}')
print()
print('Isolation Forest false alarms:')
print(f'  Group (i): {if_false_g1}')
print(f'  Group (ii): {if_false_g2}')
print(f'  Total: {if_false_g1 + if_false_g2}')
print()

# e. PILOT: percentage of rows flagged by each method
pilot_zscore_flag = zscore_flag(pilot)
pilot_iforest_scores = iso.decision_function(pilot_scaled)
pilot_iforest_flag = pilot_iforest_scores < iforest_threshold

print('=== PILOT EVALUATION (no labels, sanity check) ===')
print(f'Total pilot rows: {len(pilot)}')
print(f'Z-score flagged: {pilot_zscore_flag.sum()} ({pilot_zscore_flag.mean()*100:.2f}%)')
print(f'Isolation Forest flagged: {pilot_iforest_flag.sum()} ({pilot_iforest_flag.mean()*100:.2f}%)')
print()

# Pilot excluding test period (2026-10-27 22:02:14 to 22:04:05)
# Need timestamps from pilot full
pilot_full = pd.read_csv('data/processed/features_v2/pilot_features_full.csv')
test_start = pd.Timestamp('2026-10-27 22:02:14')
test_end = pd.Timestamp('2026-10-27 22:04:05')
pilot_full['timestamp'] = pd.to_datetime(pilot_full['timestamp'])
in_test_period = (pilot_full['timestamp'] >= test_start) & (pilot_full['timestamp'] <= test_end)
pilot_outside = pilot_full[~in_test_period]

print(f'Pilot rows in test period: {in_test_period.sum()}')
print(f'Pilot rows outside test period: {len(pilot_outside)}')
print()

# Need to align flags with pilot_outside
# Since pilot and pilot_full have same row order (after dropna), we can use the mask
pilot_outside_z = pilot_zscore_flag[~in_test_period.values]
pilot_outside_if = pilot_iforest_flag[~in_test_period.values]

print('Pilot OUTSIDE test period:')
print(f'  Z-score flagged: {pilot_outside_z.sum()} ({pilot_outside_z.mean()*100:.2f}%)')
print(f'  Isolation Forest flagged: {pilot_outside_if.sum()} ({pilot_outside_if.mean()*100:.2f}%)')
print()

# f. Distribution shift check
print('=== DISTRIBUTION SHIFT ===')
print(f'Normal: temp mean={normal["temperature"].mean():.2f}, hum mean={normal["humidity"].mean():.2f}')
print(f'Test:   temp mean={test_features["temperature"].mean():.2f}, hum mean={test_features["humidity"].mean():.2f}')
print(f'Pilot:  temp mean={pilot["temperature"].mean():.2f}, hum mean={pilot["humidity"].mean():.2f}')
print()
print('Normal humidity ~62-64%, Pilot/Test humidity ~58-60%: significant shift')
print('This shift could cause false alarms since normal model never saw low humidity baseline')
print()

# g. SAVE models and thresholds
models_dir = Path('models')
models_dir.mkdir(parents=True, exist_ok=True)

joblib.dump(iso, models_dir / 'iforest.joblib')
joblib.dump(scaler, models_dir / 'scaler.joblib')

thresholds = {
    'iforest_threshold': float(iforest_threshold),
    'zscore_threshold': 3.0,
    'normal_temp_mean': float(normal_temp_mean),
    'normal_temp_std': float(normal_temp_std),
    'normal_hum_mean': float(normal_hum_mean),
    'normal_hum_std': float(normal_hum_std),
    'feature_cols': feature_cols,
    'GAP_THRESHOLD': 10,
    'ROLL_MIN': 2
}

with open(models_dir / 'thresholds.json', 'w') as f:
    json.dump(thresholds, f, indent=2)

print('=== SAVED ===')
print(f'  models/iforest.joblib')
print(f'  models/scaler.joblib')
print(f'  models/thresholds.json')
print('Done.')