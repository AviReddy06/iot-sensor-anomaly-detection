# EDA Report: IoT Sensor Anomaly Detection

**Project:** AI-Based IoT Sensor Anomaly Detection  
**Sensor:** ESP32 + DHT11 (GPIO 4)  
**Date:** 2026-11-03  
**Analyst:** Senior Data Scientist / ML Engineer

---

## 1. Dataset Inventory

| Dataset | Rows | Columns | Header | Duplicates (All Cols) | Duplicate Timestamps | Date Range |
|---------|------|---------|--------|----------------------|---------------------|------------|
| `normal_data.csv` | 49,728 | 3 | ❌ Missing | 12,776 | 13,065 | 2026-10-29 to 2026-11-01 (~3 days) |
| `pilot_data.csv` | 3,087 | 3 | ✅ Yes | 0 | 0 | 2026-10-27 to 2026-10-28 (~3 hours) |
| `test.csv` | 56 | 3 | ✅ Yes | 0 | 0 | 2026-10-27 22:02 to 22:04 (~2 min) |
| `test_labels.csv` | 1 | 3 | ✅ Yes | N/A | N/A | Single event label |

### Key Observations

1. **`normal_data.csv` lacks a header row** — the first data row was being interpreted as column names. We manually assigned column names: `timestamp`, `temperature`, `humidity`.
2. **Massive duplication in `normal_data.csv`**: 13,065 duplicate timestamps (26.3% of rows), 12,776 exact duplicate rows.
3. **`pilot_data.csv` and `test.csv` are clean** — no duplicates, proper headers.
4. **`test_labels.csv` contains an EVENT-LEVEL label**, not row-level. It marks a time window (22:03:29 to 22:03:47) as "anomaly".

---

## 2. Statistical Analysis of normal_data.csv (Candidate Training Set)

### Temperature Statistics
| Statistic | Value |
|-----------|-------|
| Count | 49,728 |
| Mean | 25.81 °C |
| Std Dev | 0.74 °C |
| Min | 22.40 °C |
| 25th %ile (Q1) | 25.80 °C |
| Median (Q2) | 26.00 °C |
| 75th %ile (Q3) | 26.20 °C |
| Max | 27.00 °C |
| Variance | 0.54 |
| IQR | 0.40 °C |
| Lower Fence (Q1 - 1.5×IQR) | 25.20 °C |
| Upper Fence (Q3 + 1.5×IQR) | 26.80 °C |

### Humidity Statistics
| Statistic | Value |
|-----------|-------|
| Count | 49,728 |
| Mean | 62.07 % RH |
| Std Dev | 4.26 % RH |
| Min | 46.80 % RH |
| 25th %ile (Q1) | 61.00 % RH |
| Median (Q2) | 63.50 % RH |
| 75th %ile (Q3) | 64.40 % RH |
| Max | 97.20 % RH |
| Variance | 18.14 |
| IQR | 3.40 % RH |
| Lower Fence (Q1 - 1.5×IQR) | 55.90 % RH |
| Upper Fence (Q3 + 1.5×IQR) | 69.50 % RH |

### Interpretation

**Temperature:**
- Very tight distribution: middle 50% spans only 0.4°C (25.8–26.2°C)
- IQR outliers: 6,447 readings below 25.2°C (13.0%), 0 above 26.8°C
- Z-score outliers (|z|>3): 12 readings, all at the very end of the dataset (2026-11-01 17:51:08–17:51:32) showing temperature crash to 22.4°C

**Humidity:**
- Much wider spread: variance 18.14 vs 0.54 for temperature
- IQR outliers: 427 below 55.9% (0.9%), 7,705 above 69.5% (15.5%)
- Z-score outliers (|z|>3): 14 readings, same tail period + one at 2026-10-31 20:22:22
- **Maximum 97.2% is far above upper fence** — these high-humidity readings are frequent, not rare outliers

**Key Insight for ML:** Humidity has ~33x higher variance than temperature. The model must handle this multivariate scale difference. The high-humidity "outliers" by IQR (15.5% of data) suggest the IQR upper fence is too conservative for this sensor/environment — these may be legitimate environmental variations.

---

## 3. Timestamp and Sampling Interval Analysis (normal_data.csv)

| Interval | Count | Percentage | Notes |
|----------|-------|------------|-------|
| 0.0 s | 13,065 | 26.3% | **Duplicate timestamps** |
| 1.0 s | 11 | 0.02% | Timing jitter |
| 2.0 s | 35,727 | 71.8% | **Expected ESP32 interval** ✓ |
| 3.0 s | 914 | 1.8% | Slight delays |
| >10 s | 10 | 0.02% | Large gaps (max 39.5 hours) |

### Large Gaps (>10 minutes)
| Gap Duration | Approx. Time |
|--------------|--------------|
| 725 s | 12 minutes |
| 1,119 s | 18 minutes |
| 1,842 s | 30 minutes |
| 3,269 s | 54 minutes |
| 3,285 s | 55 minutes |
| 6,550 s | 1.8 hours |
| 6,965 s | 1.9 hours |
| 10,751 s | 3.0 hours |
| 12,689 s | 3.5 hours |
| 142,210 s | **39.5 hours** |

### Interpretation
- **71.8% of intervals match the expected 2.0 seconds** — ESP32 firmware timing is working correctly for the majority of readings.
- **26.3% are 0-second intervals** — duplicate timestamps indicate a logging bug (multiple rows written per sensor reading).
- **39.5-hour gap** likely represents a period when the logger was stopped or ESP32 was powered off.
- **Data is NOT continuous** — significant missing periods exist. Do not interpolate across large gaps.

---

## 4. Duplicate Analysis (normal_data.csv)

### Three Types of Duplicates

| Type | Count | Percentage | Description |
|------|-------|------------|-------------|
| Exact duplicate rows (all 3 cols) | 12,776 | 25.7% | Identical timestamp, temperature, humidity |
| Duplicate timestamps | 13,065 | 26.3% | Same timestamp, possibly different values |
| Duplicate temp+humidity (diff timestamps) | 48,574 | 97.7% | Stable environment produces same readings |

### Duplicate Timestamp Clusters (Top 10)
| Timestamp | Row Count |
|-----------|-----------|
| 2026-10-30 18:33:40 | 80 |
| 2026-10-30 18:36:30 | 54 |
| 2026-10-30 18:40:04 | 53 |
| 2026-10-30 18:44:56 | 53 |
| 2026-10-30 18:49:48 | 53 |
| 2026-10-30 18:54:40 | 53 |
| 2026-10-30 18:59:32 | 53 |
| 2026-10-30 19:04:24 | 53 |
| 2026-10-30 19:09:16 | 53 |
| 2026-10-30 19:14:08 | 53 |

### Example: Timestamp with Different Values
At `2026-10-30 18:33:40`, 80 rows exist with varying values:
- Temperature: 26.0 or 26.1 °C
- Humidity: 62.0, 62.1, or 62.2 % RH

### Interpretation
- **Pattern suggests a logging bug**: clusters of 50-80 rows at the exact same timestamp.
- Likely cause: Python logger wrote the same serial buffer multiple times, or ESP32 sent burst data.
- **Critical for ML**: These duplicates will severely bias any model — certain (timestamp, temp, humidity) combinations appear 50-80x more often than they actually occurred.
- **304 rows** have duplicate timestamps but DIFFERENT sensor values (13,065 - 12,761), indicating race conditions in logging.

---

## 5. Analysis of pilot_data.csv (Contains Anomaly Events)

### Statistical Summary
| | Temperature | Humidity |
|---|---|---|
| Mean | 27.29 °C | 57.54 % RH |
| Std Dev | 1.47 °C | 5.23 % RH |
| Min | 26.00 °C | 44.40 % RH |
| Max | 32.90 °C | 95.80 % RH |

### Sampling Intervals
- 3,006 intervals of 2.0s (97.4%)
- 78 intervals of 3.0s (2.5%)
- 1 gap of 910s (15 min)
- 1 gap of 3,857s (**64 minutes**)

### Anomaly Events Identified

#### Event 1: 2026-10-27 23:09:38 – 23:10:30 (~52 seconds)
- **Temperature**: rises from ~26.1°C to 27.4°C (+1.3°C)
- **Humidity**: **massive spike from ~58% to 95.2%** (+37%!)
- Largest humidity jump: 25.5% in 2 seconds
- Gradual return to normal over ~50 seconds

#### Event 2: 2026-10-28 00:34:20 – 00:34:56 (~36 seconds)
- **Temperature**: jumps from ~26.8°C to 32.9°C (+6.1°C!)
- **Humidity**: jumps from ~57% to 95.8% (+38%!)
- Largest humidity jump: 37.3% in 2 seconds
- Largest temperature jump: 4.4°C in 2 seconds
- Both spike simultaneously

### Interpretation
- **Simultaneous temperature AND humidity spikes** suggest real physical events (steam, cooking, shower, sensor exposure to moisture/heat).
- These are **real environmental anomalies**, not sensor noise.
- **Must NOT use pilot_data.csv for normal-only training** — it contains confirmed anomalies.

---

## 6. Analysis of test.csv and test_labels.csv

### test.csv Statistical Summary
| | Temperature | Humidity |
|---|---|---|
| Mean | 27.11 °C | 62.13 % RH |
| Std Dev | 2.36 °C | 6.58 % RH |
| Min | 26.20 °C | 59.30 % RH |
| Max | 34.20 °C | 82.10 % RH |

### Sampling
- 55 intervals, mean 2.02s, std 0.13s
- Clean, regular 2-second sampling (mostly)

### test_labels.csv
| start | end | label |
|-------|-----|-------|
| 2026-10-27T22:03:29 | 2026-10-27T22:03:47 | anomaly |

### Label Alignment
- **Event-level label**: Single row marks 18-second window
- **10 test rows** fall in this window (indices 37–46)
- **46 test rows** are normal baseline (outside window)

### Injected Anomaly Details (rows 37–46)
| Timestamp | Temperature | Humidity |
|-----------|-------------|----------|
| 22:03:29 | 32.5 °C | 75.0 % |
| 22:03:31 | 33.1 °C | 78.2 % |
| 22:03:33 | 33.8 °C | 80.5 % |
| 22:03:35 | **34.2 °C** | **82.1 %** |
| 22:03:37 | 33.9 °C | 81.8 % |
| 22:03:39 | 33.2 °C | 79.5 % |
| 22:03:41 | 32.0 °C | 75.3 % |
| 22:03:43 | 27.5 °C | 68.0 % |
| 22:03:45 | 26.5 °C | 62.0 % |
| 22:03:47 | 26.3 °C | 60.2 % |

- Temperature spikes **+8.0°C** (26.2 → 34.2) then returns
- Humidity spikes **+22.7%** (59.4 → 82.1) then returns
- Duration: 18 seconds (10 readings)
- **Sharp, clear anomaly** — much more pronounced than pilot data events

### Critical Note
- The label is **EVENT-LEVEL**, not row-level
- For evaluation, must expand to row-level: 10 anomaly rows, 46 normal rows
- **Never use test.csv for training or threshold tuning** — hold-out only

---

## 7. Cross-Dataset Comparison

| Statistic | normal_data | pilot_data | test_data (normal rows) |
|-----------|-------------|------------|------------------------|
| **Temp Mean** | 25.81 °C | 27.29 °C | 26.20 °C |
| **Temp Median** | 26.00 °C | 26.80 °C | 26.20 °C |
| **Hum Mean** | 62.07 % | 57.54 % | 59.48 % |
| **Hum Median** | 63.50 % | 58.80 % | 59.50 % |

### Key Finding: **Dataset Shift**
- **normal_data.csv** has higher humidity baseline (~62-64%) vs **pilot/test** (~59-60%)
- Temperature baseline is similar (~26.0-26.2°C median)
- **Implication**: A model trained on `normal_data.csv` may not generalize to deployment conditions matching pilot/test environment
- Different collection sessions = different environmental conditions

---

## 8. Statistical Anomaly Investigation (normal_data.csv)

### IQR Outliers
| Feature | Low Outliers | High Outliers | Total |
|---------|-------------|---------------|-------|
| Temperature | 6,447 (13.0%) | 0 | 6,447 |
| Humidity | 427 (0.9%) | 7,705 (15.5%) | 8,132 |

### Z-Score Outliers (|z| > 3)
| Feature | Count | Details |
|---------|-------|---------|
| Temperature | 12 | All at end: 2026-11-01 17:51:08–17:51:32, temp=22.4°C |
| Humidity | 14 | Same tail + one at 2026-10-31 20:22:22 (95.0%) |

### Suspicious Tail (Last 12 Rows)
| Timestamp | Temperature | Humidity |
|-----------|-------------|----------|
| 2026-11-01 17:51:08 | 22.4 °C | 92.0 % |
| 2026-11-01 17:51:10 | 22.4 °C | 91.8 % |
| ... | 22.4 °C | 90–92 % |
| 2026-11-01 17:51:32 | 22.4 °C | 89.8 % |

**Simultaneous temperature crash (22.4°C) + humidity spike (90-92%)** — physically unusual (cold air holds less moisture). Possible causes:
1. Sensor failure / condensation on sensor
2. Environmental event (AC near humidifier?)
3. Sensor artifact from power cycling

**Recommendation**: Flag these 12 rows; investigate before training. Do NOT auto-remove.

---

## 9. Visualizations Generated

All plots saved to `eda/plots/`:

| Plot | Description |
|------|-------------|
| `normal_data_histograms.png` | Temp/humidity histograms + boxplots |
| `normal_data_timeseries.png` | Full time series (3 days) |
| `normal_data_scatter.png` | Temp vs Humidity scatter |
| `normal_data_correlation.png` | Correlation heatmap |
| `normal_data_intervals.png` | Sampling interval histogram |
| `pilot_data_timeseries.png` | Pilot data full time series |
| `pilot_data_anomaly_detail.png` | Zoomed anomaly events (2 events) |
| `test_data_timeseries.png` | Test data with anomaly window highlighted |
| `test_data_anomaly_detail.png` | Injected anomaly zoom |

---

## 10. Summary and Recommendations

### Dataset Suitability for ML Stages

| Stage | Recommended Dataset | Notes |
|-------|---------------------|-------|
| Training (normal) | `normal_data.csv` (cleaned) | Remove duplicates, investigate tail, verify conditions match deployment |
| Validation | `pilot_data.csv` | Contains real anomalies — good for threshold tuning |
| Testing | `test.csv` + expanded labels | Small but clean; only for final evaluation |

### Recommended Data Cleaning Decisions

1. **DO NOT MODIFY ORIGINAL CSVs** — keep raw data immutable in `data/raw/`
2. **Create cleaned versions** in `data/processed/`:
   - Remove exact duplicate rows (keep first occurrence)
   - For duplicate timestamps with different values: investigate pattern, possibly keep first or average
   - **Flag but don't auto-remove** the suspicious tail (last 12 rows of normal_data.csv)
   - Add sequence numbers to detect dropped packets
3. **Handle large gaps**: Don't interpolate across gaps >1 hour
4. **Align datasets**: Consider if normal_data.csv conditions match deployment environment
5. **Expand test labels**: Create row-level labels from event-level for evaluation metrics
6. **Track data lineage**: Every processed dataset should reference source raw file and cleaning steps

### Teaching Notes: Key Concepts Applied

| Concept | Why It Matters | Python/Pandas Function |
|---------|----------------|------------------------|
| **Descriptive Statistics** | Understand central tendency & spread of normal data | `df.describe()`, `df.quantile()` |
| **IQR (Interquartile Range)** | Robust outlier detection without Gaussian assumption | `Q3 - Q1`, fences at `Q1-1.5×IQR`, `Q3+1.5×IQR` |
| **Z-Score** | Standardized outlier detection (assumes Gaussian) | `(x - mean) / std` |
| **Time Series Diff** | Detect sampling irregularities | `df['ts'].diff().dt.total_seconds()` |
| **Duplicate Detection** | Identify logging bugs that bias training | `df.duplicated()`, `df.duplicated(subset=[...])` |
| **Event vs Row Labels** | Critical for correct evaluation | Manual expansion: `df[(df.ts >= start) & (df.ts <= end)]` |
| **Cross-Dataset Comparison** | Detect distribution shift (dataset shift) | Compare `describe()` across datasets |

### Why This Matters for Anomaly Detection

1. **Training data quality determines model quality** — duplicates and artifacts in normal_data.csv will teach the model that repeated identical readings are "normal"
2. **Validation on real anomalies** — pilot_data.csv provides genuine anomaly examples for threshold tuning
3. **Hold-out test integrity** — test.csv must remain completely unseen until final evaluation
4. **Environmental conditions matter** — dataset shift between normal_data and pilot/test means we must verify deployment conditions match training data
5. **Statistical outliers ≠ faults** — 15.5% of normal_data humidity readings are IQR "outliers" but may be legitimate variation

---

## Appendix: Plot Files

All plots available in `eda/plots/`:
- normal_data_histograms.png (129 KB)
- normal_data_timeseries.png (83 KB)
- normal_data_scatter.png (57 KB)
- normal_data_correlation.png (32 KB)
- normal_data_intervals.png (39 KB)
- pilot_data_timeseries.png (86 KB)
- pilot_data_anomaly_detail.png (208 KB)
- test_data_timeseries.png (108 KB)
- test_data_anomaly_detail.png (89 KB)

---

*Report generated from `eda/notebooks/01_eda.ipynb`*