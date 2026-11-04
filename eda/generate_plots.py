#!/usr/bin/env python3
"""Generate EDA plots for all datasets."""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Load data
normal = pd.read_csv('data/raw/normal_data.csv', header=None, names=['timestamp', 'temperature', 'humidity'])
pilot = pd.read_csv('data/raw/pilot_data.csv')
test = pd.read_csv('data/raw/test.csv')

normal['timestamp'] = pd.to_datetime(normal['timestamp'])
pilot['timestamp'] = pd.to_datetime(pilot['timestamp'])
test['timestamp'] = pd.to_datetime(test['timestamp'])

plots_dir = Path('eda/plots')
plots_dir.mkdir(parents=True, exist_ok=True)

plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette('husl')

# ============================================================
# normal_data.csv plots
# ============================================================

# Histograms
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

temp_mean = normal['temperature'].mean()
temp_median = normal['temperature'].median()
axes[0, 0].hist(normal['temperature'], bins=50, alpha=0.7, edgecolor='black', color='skyblue')
axes[0, 0].axvline(temp_mean, color='red', linestyle='--', label='Mean: {:.2f}'.format(temp_mean))
axes[0, 0].axvline(temp_median, color='green', linestyle='--', label='Median: {:.2f}'.format(temp_median))
axes[0, 0].set_title('Temperature Distribution (normal_data.csv)')
axes[0, 0].set_xlabel('Temperature (deg C)')
axes[0, 0].set_ylabel('Frequency')
axes[0, 0].legend()

hum_mean = normal['humidity'].mean()
hum_median = normal['humidity'].median()
axes[0, 1].hist(normal['humidity'], bins=50, alpha=0.7, edgecolor='black', color='lightcoral')
axes[0, 1].axvline(hum_mean, color='red', linestyle='--', label='Mean: {:.2f}'.format(hum_mean))
axes[0, 1].axvline(hum_median, color='green', linestyle='--', label='Median: {:.2f}'.format(hum_median))
axes[0, 1].set_title('Humidity Distribution (normal_data.csv)')
axes[0, 1].set_xlabel('Humidity (% RH)')
axes[0, 1].set_ylabel('Frequency')
axes[0, 1].legend()

axes[1, 0].boxplot(normal['temperature'], vert=True, patch_artist=True,
                   boxprops=dict(facecolor='skyblue'), medianprops=dict(color='red'))
axes[1, 0].set_title('Temperature Boxplot (normal_data.csv)')
axes[1, 0].set_ylabel('Temperature (deg C)')
axes[1, 0].set_xticklabels(['Temperature'])

axes[1, 1].boxplot(normal['humidity'], vert=True, patch_artist=True,
                   boxprops=dict(facecolor='lightcoral'), medianprops=dict(color='red'))
axes[1, 1].set_title('Humidity Boxplot (normal_data.csv)')
axes[1, 1].set_ylabel('Humidity (% RH)')
axes[1, 1].set_xticklabels(['Humidity'])

plt.tight_layout()
plt.savefig('eda/plots/normal_data_histograms.png', dpi=150, bbox_inches='tight')
plt.close()

# Time series
fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
axes[0].plot(normal['timestamp'], normal['temperature'], alpha=0.6, linewidth=0.5, color='blue')
axes[0].set_title('Temperature Over Time (normal_data.csv)')
axes[0].set_ylabel('Temperature (deg C)')
axes[0].grid(True, alpha=0.3)

axes[1].plot(normal['timestamp'], normal['humidity'], alpha=0.6, linewidth=0.5, color='orange')
axes[1].set_title('Humidity Over Time (normal_data.csv)')
axes[1].set_xlabel('Timestamp')
axes[1].set_ylabel('Humidity (% RH)')
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('eda/plots/normal_data_timeseries.png', dpi=150, bbox_inches='tight')
plt.close()

# Scatter
plt.figure(figsize=(8, 6))
plt.scatter(normal['temperature'], normal['humidity'], alpha=0.3, s=5, c='purple')
plt.title('Temperature vs Humidity (normal_data.csv)')
plt.xlabel('Temperature (deg C)')
plt.ylabel('Humidity (% RH)')
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('eda/plots/normal_data_scatter.png', dpi=150, bbox_inches='tight')
plt.close()

# Correlation
plt.figure(figsize=(6, 5))
corr = normal[['temperature', 'humidity']].corr()
sns.heatmap(corr, annot=True, cmap='coolwarm', center=0, square=True, fmt='.3f')
plt.title('Correlation Heatmap (normal_data.csv)')
plt.tight_layout()
plt.savefig('eda/plots/normal_data_correlation.png', dpi=150, bbox_inches='tight')
plt.close()

# Intervals
plt.figure(figsize=(10, 5))
intervals = normal['timestamp'].diff().dt.total_seconds().dropna()
plt.hist(intervals[intervals <= 10], bins=20, alpha=0.7, edgecolor='black', color='teal')
plt.axvline(2.0, color='red', linestyle='--', linewidth=2, label='Expected: 2.0s')
plt.title('Sampling Interval Distribution (normal_data.csv, intervals <= 10s)')
plt.xlabel('Interval (seconds)')
plt.ylabel('Frequency')
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('eda/plots/normal_data_intervals.png', dpi=150, bbox_inches='tight')
plt.close()

# ============================================================
# pilot_data.csv plots
# ============================================================

fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
axes[0].plot(pilot['timestamp'], pilot['temperature'], alpha=0.7, linewidth=0.8, color='blue')
axes[0].set_title('Temperature Over Time (pilot_data.csv)')
axes[0].set_ylabel('Temperature (deg C)')
axes[0].grid(True, alpha=0.3)

axes[1].plot(pilot['timestamp'], pilot['humidity'], alpha=0.7, linewidth=0.8, color='orange')
axes[1].set_title('Humidity Over Time (pilot_data.csv)')
axes[1].set_xlabel('Timestamp')
axes[1].set_ylabel('Humidity (% RH)')
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('eda/plots/pilot_data_timeseries.png', dpi=150, bbox_inches='tight')
plt.close()

# Anomaly detail
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
event1 = pilot[(pilot['timestamp'] >= '2026-10-27 23:09:00') & (pilot['timestamp'] <= '2026-10-27 23:11:00')]
axes[0, 0].plot(event1['timestamp'], event1['temperature'], 'o-', color='blue')
axes[0, 0].set_title('Event 1: Temperature (23:09 - 23:11)')
axes[0, 0].set_ylabel('Temperature (deg C)')
axes[0, 0].grid(True, alpha=0.3)
axes[0, 0].tick_params(axis='x', rotation=45)

axes[0, 1].plot(event1['timestamp'], event1['humidity'], 'o-', color='orange')
axes[0, 1].set_title('Event 1: Humidity (23:09 - 23:11)')
axes[0, 1].set_ylabel('Humidity (% RH)')
axes[0, 1].grid(True, alpha=0.3)
axes[0, 1].tick_params(axis='x', rotation=45)

event2 = pilot[(pilot['timestamp'] >= '2026-10-28 00:33:30') & (pilot['timestamp'] <= '2026-10-28 00:35:30')]
axes[1, 0].plot(event2['timestamp'], event2['temperature'], 'o-', color='blue')
axes[1, 0].set_title('Event 2: Temperature (00:33:30 - 00:35:30)')
axes[1, 0].set_ylabel('Temperature (deg C)')
axes[1, 0].grid(True, alpha=0.3)
axes[1, 0].tick_params(axis='x', rotation=45)

axes[1, 1].plot(event2['timestamp'], event2['humidity'], 'o-', color='orange')
axes[1, 1].set_title('Event 2: Humidity (00:33:30 - 00:35:30)')
axes[1, 1].set_xlabel('Timestamp')
axes[1, 1].set_ylabel('Humidity (% RH)')
axes[1, 1].grid(True, alpha=0.3)
axes[1, 1].tick_params(axis='x', rotation=45)

plt.tight_layout()
plt.savefig('eda/plots/pilot_data_anomaly_detail.png', dpi=150, bbox_inches='tight')
plt.close()

# ============================================================
# test.csv plots
# ============================================================

anomaly_start = pd.to_datetime('2026-10-27 22:03:29')
anomaly_end = pd.to_datetime('2026-10-27 22:03:47')

fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
axes[0].plot(test['timestamp'], test['temperature'], 'o-', color='blue', markersize=4, label='Temperature')
axes[0].axvspan(anomaly_start, anomaly_end, alpha=0.3, color='red', label='Anomaly Window')
axes[0].set_title('Temperature Over Time (test.csv) - Injected Anomaly')
axes[0].set_ylabel('Temperature (deg C)')
axes[0].legend()
axes[0].grid(True, alpha=0.3)
axes[0].tick_params(axis='x', rotation=45)

axes[1].plot(test['timestamp'], test['humidity'], 'o-', color='orange', markersize=4, label='Humidity')
axes[1].axvspan(anomaly_start, anomaly_end, alpha=0.3, color='red', label='Anomaly Window')
axes[1].set_title('Humidity Over Time (test.csv) - Injected Anomaly')
axes[1].set_xlabel('Timestamp')
axes[1].set_ylabel('Humidity (% RH)')
axes[1].legend()
axes[1].grid(True, alpha=0.3)
axes[1].tick_params(axis='x', rotation=45)

plt.tight_layout()
plt.savefig('eda/plots/test_data_timeseries.png', dpi=150, bbox_inches='tight')
plt.close()

# Anomaly detail
fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
anomaly_data = test[(test['timestamp'] >= anomaly_start) & (test['timestamp'] <= anomaly_end)]
axes[0].plot(anomaly_data['timestamp'], anomaly_data['temperature'], 'o-', color='red', markersize=6)
axes[0].set_title('Injected Anomaly Detail: Temperature')
axes[0].set_ylabel('Temperature (deg C)')
axes[0].grid(True, alpha=0.3)
axes[0].tick_params(axis='x', rotation=45)

axes[1].plot(anomaly_data['timestamp'], anomaly_data['humidity'], 'o-', color='red', markersize=6)
axes[1].set_title('Injected Anomaly Detail: Humidity')
axes[1].set_xlabel('Timestamp')
axes[1].set_ylabel('Humidity (% RH)')
axes[1].grid(True, alpha=0.3)
axes[1].tick_params(axis='x', rotation=45)

plt.tight_layout()
plt.savefig('eda/plots/test_data_anomaly_detail.png', dpi=150, bbox_inches='tight')
plt.close()

print('All plots generated successfully!')
for f in sorted(plots_dir.glob('*')):
    print('  {} ({} bytes)'.format(f.name, f.stat().st_size))