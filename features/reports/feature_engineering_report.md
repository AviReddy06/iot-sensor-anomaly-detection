# Feature Engineering Report: IoT Sensor Anomaly Detection

**Project:** AI-Based IoT Sensor Anomaly Detection  
**Phase:** 3 - Feature Engineering  
**Date:** 2026-11-03

---

## 1. Input Datasets

| Dataset | Source | Rows | Description |
|---------|--------|------|-------------|
| Normal training candidate | `data/processed/normal_data_training_candidate.csv` | 36,952 | Deduplicated normal data |
| Pilot data | `data/processed/pilot_data_prepared.csv` | 3,087 | Contains 2 verified anomaly events |
| Test data with labels | `data/processed/test_data_with_labels.csv` | 56 | 46 normal, 10 anomaly (row-level labels) |

---

## 2. Raw Features

| Feature | Description | Unit |
|---------|-------------|------|
| `temperature` | DHT11 sensor reading | °C |
| `humidity` | DHT11 sensor reading | % RH |

**Note:** `timestamp` is used for ordering and gap detection but **not** used as a direct ML feature.

---

## 3. Engineered Features

### 3.1 Change Features (4)

| Feature | Formula | Interpretation |
|---------|---------|----------------|
| `temperature_change` | `temperature - temperature.shift(1)` | Positive = increase, Negative = decrease |
| `humidity_change` | `humidity - humidity.shift(1)` | Positive = increase, Negative = decrease |
| `temperature_abs_change` | `abs(temperature_change)` | Magnitude of temperature change (ignores direction) |
| `humidity_abs_change` | `abs(humidity_change)` | Magnitude of humidity change (ignores direction) |

**Why:** Sudden jumps in sensor readings are often anomalous. Change features make these jumps explicit.

**Missing values:** 1 per dataset (first row has no previous value).

### 3.2 Rolling Statistical Features (10)

| Feature | Window | Description |
|---------|--------|-------------|
| `temp_rolling_mean_5` | 5 obs | Mean temperature of last 5 readings |
| `temp_rolling_std_5` | 5 obs | Std deviation of last 5 temperature readings |
| `hum_rolling_mean_5` | 5 obs | Mean humidity of last 5 readings |
| `hum_rolling_std_5` | 5 obs | Std deviation of last 5 humidity readings |
| `temp_rolling_mean_15` | 15 obs | Mean temperature of last 15 readings |
| `temp_rolling_std_15` | 15 obs | Std deviation of last 15 temperature readings |
| `hum_rolling_mean_15` | 15 obs | Mean humidity of last 15 readings |
| `hum_rolling_std_15` | 15 obs | Std deviation of last 15 humidity readings |

**Why:** 
- Rolling mean captures recent baseline/trend
- Rolling std captures recent stability/volatility
- Anomalous readings often deviate from recent mean or occur during high volatility

**Missing values:** 
- Window 5: first 4 rows of each session
- Window 15: first 14 rows of each session
- Additional missing at session boundaries

---

## 4. Timestamp Gap Handling

### 4.1 Gap Detection
- Computed `time_diff = timestamp.diff()` in seconds
- Identified gaps > 10 seconds as recording interruptions

| Dataset | Total Intervals | Gaps > 10s | Largest Gap |
|---------|----------------|------------|-------------|
| Normal | 36,951 | 10 | 142,210s (39.5 hours) |
| Pilot | 3,086 | 2 | 3,857s (64 min) |
| Test | 55 | 0 | 3s |

### 4.2 Session-Based Rolling Features
- Created `session_id` that increments after each gap > 10 seconds
- Rolling features computed **within each session** using `groupby('session_id')`
- **Never** calculates statistics across recording gaps
- Session boundaries add additional missing values (first row of each new session)

### 4.3 Session Counts

| Dataset | Sessions | Session Sizes |
|---------|----------|---------------|
| Normal | 11 | 4065, 721, 873, 1222, 343, 289, 715, 432, 14232, 639, 281 |
| Pilot | 3 | 143, 1292, 1652 |
| Test | 1 | 56 |

---

## 5. Missing Value Analysis

### 5.1 Sources of Missing Values
| Source | Affected Features | Rows Affected |
|--------|-------------------|---------------|
| First row (no previous) | Change features (4) | 1 per dataset |
| Rolling window 5 | 8 rolling features | First 4 rows of each session |
| Rolling window 15 | 8 rolling features | First 14 rows of each session |
| Session boundaries | 8 rolling features | First row of each new session |

### 5.2 Missing Value Counts (Before Cleaning)

| Dataset | Change Features | Rolling 5 | Rolling 15 | Total Rows with Any Missing |
|---------|----------------|-----------|------------|----------------------------|
| Normal | 1 | 22 | 32 | 32 |
| Pilot | 1 | 5 | 17 | 17 |
| Test | 1 | 4 | 14 | 14 |

### 5.3 Handling Strategy
- **Do NOT impute** — would create artificial data
- **Do NOT delete blindly** — documented exactly which rows and why
- **Decision:** Drop rows with any missing engineered features
- **Impact:** Negligible (0.4% of normal, 0.5% of pilot, 25% of test)
  - Test has higher % because it's very small (56 rows)

---

## 6. Final Feature Datasets

### 6.1 Feature Columns (14 for ML)

| # | Feature | Type |
|---|---------|------|
| 1 | `temperature` | Raw |
| 2 | `humidity` | Raw |
| 3 | `temperature_change` | Engineered |
| 4 | `humidity_change` | Engineered |
| 5 | `temperature_abs_change` | Engineered |
| 6 | `humidity_abs_change` | Engineered |
| 7 | `temp_rolling_mean_5` | Engineered |
| 8 | `temp_rolling_std_5` | Engineered |
| 9 | `hum_rolling_mean_5` | Engineered |
| 10 | `hum_rolling_std_5` | Engineered |
| 11 | `temp_rolling_mean_15` | Engineered |
| 12 | `temp_rolling_std_15` | Engineered |
| 13 | `hum_rolling_mean_15` | Engineered |
| 14 | `hum_rolling_std_15` | Engineered |

### 6.2 Final Dataset Sizes

| Dataset | Original Rows | After Dropping Missing | Features | Labels |
|---------|---------------|------------------------|----------|--------|
| Normal | 36,952 | **36,798** | 14 | — |
| Pilot | 3,087 | **3,045** | 14 | — |
| Test | 56 | **42** | 14 | 32 normal, 10 anomaly |

### 6.3 Test Label Distribution (After Cleaning)
| Label | Count | Description |
|-------|-------|-------------|
| 0 | 32 | Normal |
| 1 | 10 | Anomaly |

---

## 7. Files Generated

All files saved to `data/processed/features/`:

| File | Rows | Columns | Purpose |
|------|------|---------|---------|
| `normal_features.csv` | 36,798 | 14 | ML training features |
| `normal_features_full.csv` | 36,798 | 17 | With timestamp, time_diff, session_id |
| `pilot_features.csv` | 3,045 | 14 | Validation features |
| `pilot_features_full.csv` | 3,045 | 17 | With metadata |
| `test_features.csv` | 42 | 14 | Final evaluation features |
| `test_features_full.csv` | 42 | 18 | With label, timestamp, metadata |
| `test_labels.csv` | 42 | 1 | Row-level labels (0/1) |

---

## 8. Dataset-Specific Observations

### Normal Data
- 36,798 clean feature rows after removing missing values
- 11 sessions due to large recording gaps
- Temperature very stable (std ~0.73), humidity more variable (std ~4.0)
- High-humidity readings (>90%) present but retained

### Pilot Data
- 3,045 clean feature rows
- 3 sessions (2 large gaps)
- Contains 2 verified anomaly events (not for training)
- Wider feature distributions due to anomalies

### Test Data
- Only 42 rows after cleaning (25% reduction due to small size)
- 10 anomaly rows preserved, 32 normal rows
- Single session (no gaps > 10s)
- **Reserved for final evaluation only** — never used for training/threshold tuning

---

## 9. Key Decisions & Rationale

| Decision | Rationale |
|----------|-----------|
| Gap threshold = 10 seconds | Distinguishes normal 2-3s intervals from true recording stops |
| Session-based rolling | Prevents statistics from mixing different recording periods |
| Drop missing rows (don't impute) | Preserves data integrity; no artificial values created |
| Keep absolute change features | Direction-agnostic magnitude helps detect any sudden change |
| Two window sizes (5, 15) | Captures both short-term and medium-term behavior |
| Separate test labels file | Prevents accidental label leakage during training |

---

## 10. Next Steps (Phase 4: Model Training)

1. Load `normal_features.csv` for Isolation Forest training
2. Use `pilot_features.csv` for validation/threshold tuning
3. Reserve `test_features.csv` + `test_labels.csv` for final evaluation only
4. Feature scaling not required for Isolation Forest (tree-based)
5. Verify model performance on pilot anomaly events before final test

---

*Report generated from `features/notebooks/03_feature_engineering.ipynb`*