# eda/audit_normal_episodes.py
# READ-ONLY audit of possible blowing episodes in normal training data
# Simple sequential code, no classes or lambda, comment above every step

import pandas as pd
import numpy as np
import json
import matplotlib.pyplot as plt
from pathlib import Path

# 1. Load normal features full (has timestamp, session_id, 14 features)
# Sort by timestamp
normal = pd.read_csv('data/processed/features_v2/normal_features_full.csv')
normal['timestamp'] = pd.to_datetime(normal['timestamp'])
normal = normal.sort_values('timestamp', kind='stable').reset_index(drop=True)
print(f'Loaded normal: {len(normal)} rows, {normal["session_id"].nunique()} sessions')
print(f'Time range: {normal["timestamp"].min()} to {normal["timestamp"].max()}')
print()

# 2. Candidate rule: robust z-score > 8 for temperature_change OR humidity_change
# Robust z = (x - median) / (1.4826 * MAD)
# MAD = median(|x - median|)
# 1.4826 scales MAD to be consistent with std for normal distribution

for col in ['temperature_change', 'humidity_change']:
    median = normal[col].median()
    mad = np.median(np.abs(normal[col] - median))
    if mad == 0:
        mad = 1e-10  # avoid division by zero
    scale = 1.4826 * mad
    normal[f'{col}_robust_z'] = (normal[col] - median) / scale
    print(f'{col}: median={median:.4f}, MAD={mad:.4f}, scale={scale:.4f}')

# Mark candidate if abs(robust z) > 8 for EITHER column
normal['is_candidate'] = (normal['temperature_change_robust_z'].abs() > 8) | \
                          (normal['humidity_change_robust_z'].abs() > 8)

candidate_rows = normal[normal['is_candidate']].copy()
print(f'\nCandidate rows (robust z > 8): {len(candidate_rows)} out of {len(normal)} ({len(candidate_rows)/len(normal)*100:.2f}%)')
print()

# 3. Merge into episodes: same session, timestamps within 30 seconds
episodes = []
if len(candidate_rows) > 0:
    candidate_rows = candidate_rows.sort_values('timestamp').reset_index(drop=True)
    
    current_ep = [candidate_rows.iloc[0].name]  # list of indices
    for i in range(1, len(candidate_rows)):
        prev = candidate_rows.iloc[i-1]
        curr = candidate_rows.iloc[i]
        
        same_session = (curr['session_id'] == prev['session_id'])
        time_gap = (curr['timestamp'] - prev['timestamp']).total_seconds()
        
        if same_session and time_gap <= 30:
            current_ep.append(curr.name)
        else:
            episodes.append(current_ep)
            current_ep = [curr.name]
    episodes.append(current_ep)

print(f'Number of episodes: {len(episodes)}')
print()

# For each episode, print details
normal_temp_median = normal['temperature'].median()
normal_hum_median = normal['humidity'].median()

for ep_num, ep_indices in enumerate(episodes, 1):
    ep_rows = normal.loc[ep_indices]
    start_time = ep_rows['timestamp'].min()
    end_time = ep_rows['timestamp'].max()
    n_rows = len(ep_rows)
    peak_temp = ep_rows['temperature'].max()
    peak_hum = ep_rows['humidity'].max()
    
    print(f'Episode {ep_num}:')
    print(f'  Start: {start_time}')
    print(f'  End: {end_time}')
    print(f'  Candidate rows: {n_rows}')
    print(f'  Peak temperature: {peak_temp:.2f} (normal median: {normal_temp_median:.2f})')
    print(f'  Peak humidity: {peak_hum:.2f} (normal median: {normal_hum_median:.2f})')
    print()

# 4. Totals
print('=== TOTALS ===')
print(f'Total candidate rows: {len(candidate_rows)}')
print(f'Total episodes: {len(episodes)}')
print(f'Percentage of 36,941 rows: {len(candidate_rows)/36941*100:.2f}%')
print()

# Rolling-window contamination zone: rows within 14 rows after each episode's end
# Need to find the position of episode end in the full sorted normal dataframe
contamination_count = 0
contamination_rows = set()

for ep_indices in episodes:
    ep_rows = normal.loc[ep_indices]
    last_idx = ep_rows.index.max()  # last row index in original dataframe
    # Get next 14 rows in the full dataframe
    next_14 = normal.index[normal.index > last_idx][:14]
    contamination_rows.update(next_14)

contamination_count = len(contamination_rows)
print(f'Rows within 14 rows after episode ends (contamination zone): {contamination_count}')
print()

# 5. Sensitivity: thresholds 5, 8, 12
print('=== SENSITIVITY (information only) ===')
for thresh in [5, 8, 12]:
    mask = (normal['temperature_change_robust_z'].abs() > thresh) | \
           (normal['humidity_change_robust_z'].abs() > thresh)
    cand = normal[mask].copy()
    
    # Count episodes for this threshold
    if len(cand) > 0:
        cand = cand.sort_values('timestamp').reset_index(drop=True)
        ep_list = []
        curr_ep = [cand.iloc[0].name]
        for i in range(1, len(cand)):
            prev = cand.iloc[i-1]
            curr = cand.iloc[i]
            same_session = (curr['session_id'] == prev['session_id'])
            time_gap = (curr['timestamp'] - prev['timestamp']).total_seconds()
            if same_session and time_gap <= 30:
                curr_ep.append(curr.name)
            else:
                ep_list.append(curr_ep)
                curr_ep = [curr.name]
        ep_list.append(curr_ep)
        n_episodes = len(ep_list)
    else:
        n_episodes = 0
    
    print(f'  Threshold {thresh}: {len(cand)} candidate rows, {n_episodes} episodes')
print()

# 6. Save plot
print('=== SAVING PLOT ===')
fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)

# Temperature over time
axes[0].plot(normal['timestamp'], normal['temperature'], 'b-', alpha=0.5, linewidth=0.5, label='Temperature')
if len(candidate_rows) > 0:
    axes[0].scatter(candidate_rows['timestamp'], candidate_rows['temperature'],
                    color='red', s=10, zorder=5, label=f'Candidate (robust z > 8)')
axes[0].axhline(y=normal_temp_median, color='blue', linestyle='--', alpha=0.5, label=f'Median ({normal_temp_median:.2f})')
axes[0].set_ylabel('Temperature (°C)')
axes[0].legend(loc='upper right')
axes[0].grid(True, alpha=0.3)

# Humidity over time
axes[1].plot(normal['timestamp'], normal['humidity'], 'g-', alpha=0.5, linewidth=0.5, label='Humidity')
if len(candidate_rows) > 0:
    axes[1].scatter(candidate_rows['timestamp'], candidate_rows['humidity'],
                    color='red', s=10, zorder=5, label=f'Candidate (robust z > 8)')
axes[1].axhline(y=normal_hum_median, color='green', linestyle='--', alpha=0.5, label=f'Median ({normal_hum_median:.2f})')
axes[1].set_ylabel('Humidity (%)')
axes[1].set_xlabel('Timestamp')
axes[1].legend(loc='upper right')
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plot_path = 'eda/plots/normal_candidate_episodes.png'
fig.savefig(plot_path, dpi=150, bbox_inches='tight')
print(f'Saved: {plot_path}')
print()

# 7. Compare with Z-score baseline
print('=== Z-SCORE BASELINE COMPARISON ===')
with open('models/thresholds.json', 'r') as f:
    thresholds = json.load(f)

normal_temp_mean = thresholds['normal_temp_mean']
normal_temp_std = thresholds['normal_temp_std']
normal_hum_mean = thresholds['normal_hum_mean']
normal_hum_std = thresholds['normal_hum_std']

z_temp = np.abs((candidate_rows['temperature'] - normal_temp_mean) / normal_temp_std)
z_hum = np.abs((candidate_rows['humidity'] - normal_hum_mean) / normal_hum_std)
z_flag = (z_temp > 3) | (z_hum > 3)

print(f'Candidate rows with abs(z) > 3 for temp OR hum: {z_flag.sum()} out of {len(candidate_rows)}')
print(f'These are episodes the Z-score baseline ALREADY treats as anomalies')
print(f'Candidate rows with abs(z) <= 3 for BOTH: {(~z_flag).sum()} out of {len(candidate_rows)}')
print(f'These are episodes the Z-score baseline treats as NORMAL')

print()
print('=== DONE ===')