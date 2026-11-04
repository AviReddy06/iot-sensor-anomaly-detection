# Preprocessing Report: IoT Sensor Anomaly Detection

**Project:** AI-Based IoT Sensor Anomaly Detection  
**Phase:** 2 - Data Preprocessing and Cleaning  
**Date:** 2026-11-03

---

## 1. Original Row Counts

| Dataset | Original Rows | Original Columns | Header |
|---------|---------------|------------------|--------|
| `normal_data.csv` | 49,728 | 3 | ❌ Missing |
| `pilot_data.csv` | 3,087 | 3 | ✅ Yes |
| `test.csv` | 56 | 3 | ✅ Yes |
| `test_labels.csv` | 1 | 3 | ✅ Yes |

---

## 2. Normal Data Cleaning

### 2.1 Loading and Type Conversion
- **Header issue:** `normal_data.csv` had no header row. Loaded with `header=None` and assigned column names: `timestamp`, `temperature`, `humidity`.
- **Timestamps:** Converted to `datetime64[ns]` using `pd.to_datetime()`.
- **Sensor values:** Converted to `float64`.

### 2.2 Missing and Invalid Values
- **Missing values:** 0 across all columns in all datasets.
- **DHT11 range check:**
  - Temperature (0-50°C): 0 out-of-range in all datasets.
  - Humidity (20-90% RH): 
    - Normal data: 13 rows with humidity > 90% (max 97.2%)
    - Pilot data: 27 rows with humidity > 90% (max 95.8%)
    - Test data: 0 out-of-range
  - **Action:** Flagged but NOT removed — may be real environmental readings or sensor saturation.

### 2.3 Exact Duplicate Removal
| Metric | Count |
|--------|-------|
| Original rows | 49,728 |
| Exact duplicate rows (all 3 columns identical) | **12,776** |
| Rows after deduplication | **36,952** |
| Duplicates removed | **12,776** |

- **Method:** `df.drop_duplicates(keep="first")` — keeps first occurrence, removes subsequent exact duplicates.
- **Audit file:** `normal_data_duplicate_audit.csv` (12,776 rows) saved for review.
- **Verification:** 36,952 + 12,776 = 49,728 ✓

### 2.4 Repeated Timestamps with Different Values
After exact deduplication, some timestamps still appear multiple times with different sensor values:

| Metric | Count |
|--------|-------|
| Total rows with duplicate timestamps | **304** |
| Unique timestamps with duplicates | **15** |
| Max rows at one timestamp | **80** (at 2026-10-30 18:33:40) |

- **Action:** All 304 rows **kept** in dataset. Saved report: `normal_data_repeated_timestamps_report.csv`.
- **Note:** These likely indicate a logging bug (bursts of readings at same second). Not auto-removed.

### 2.5 Suspicious Tail Investigation
The EDA reported a "suspicious tail" with temperature=22.4°C and humidity=89-92%. **Investigation found this combination does not exist in the actual data.**

| Search Criteria | Rows Found |
|-----------------|------------|
| Temperature ≤ 23°C | 1,412 |
| Humidity ≥ 85% | 32 |
| **Temperature ≤ 23°C AND Humidity ≥ 85%** | **0** |

- **Low-temperature rows** (≤23°C) have normal humidity (~50-55%).
- **High-humidity rows** (≥85%) have temperatures 24-27°C.
- **Conclusion:** The EDA's "suspicious tail" was an artifact. No rows match the reported anomaly pattern.
- **Action:** No rows removed. The training candidate dataset is identical to the full deduplicated dataset.

### 2.6 Two Dataset Versions Created

| Version | File | Rows | Description |
|---------|------|------|-------------|
| **All observations** | `normal_data_deduplicated_all.csv` | 36,952 | Exact duplicates removed, all other rows kept |
| **Training candidate** | `normal_data_training_candidate.csv` | 36,952 | Identical to above (no suspicious rows found to exclude) |

> ⚠️ **Note:** The training candidate is a *candidate* for normal-only training. Verify environmental conditions match deployment before use.

---

## 3. Timestamp Handling

- **Parsing:** All timestamps successfully converted to `datetime64[ns]`.
- **Invalid timestamps:** 0 found.
- **Repeated timestamps:** Preserved (304 rows with 15 unique timestamps).
- **Recording gaps:** Preserved. Large gaps documented:
  - 10 gaps > 10 minutes
  - Max gap: ~39.5 hours (likely logger stopped)
- **No interpolation** performed. No artificial observations created.
- **Original row order** preserved (no sorting applied).

---

## 4. Pilot Dataset Preparation

| Metric | Value |
|--------|-------|
| Original rows | 3,087 |
| Missing values | 0 |
| Duplicates | 0 |
| Rows preserved | 3,087 |

### Anomaly Events Verified

| Event | Time Range | Duration | Rows | Temp Range | Humidity Range |
|-------|------------|----------|------|------------|----------------|
| **Event 1** | 2026-10-27 23:09:38 – 23:10:30 | 52 sec | 26 | 26.6 – 27.4°C | 82.6 – 95.2% |
| **Event 2** | 2026-10-28 00:34:20 – 00:34:56 | 36 sec | 19 | 27.7 – 32.9°C | 74.7 – 95.8% |

### Files Created
- `pilot_data_prepared.csv` — All 3,087 rows, unchanged.
- `pilot_event_annotations.csv` — 2 events with preliminary annotations.

> ⚠️ **Important:** Pilot data contains **REAL anomalies**. Do NOT use for normal-only training. Event annotations are **preliminary** — require manual verification.

---

## 5. Test Dataset Preparation

### Label Conversion
- **Source:** `test_labels.csv` — 1 event-level label (2026-10-27 22:03:29 to 22:03:47, label="anomaly").
- **Method:** Each test row checked if timestamp falls within anomaly window.
- **Result:**

| Label | Count | Description |
|-------|-------|-------------|
| 0 (Normal) | 46 | Outside anomaly window |
| 1 (Anomaly) | 10 | Inside anomaly window (indices 37-46) |

- **Verification:** Matches EDA expectation of 10 anomaly rows ✓
- **File:** `test_data_with_labels.csv` (56 rows with `label` column added)
- **Original `test_labels.csv` unchanged.**

---

## 6. Dataset Comparison

### Temperature Statistics

| Statistic | Normal (All) | Normal (Train Cand.) | Pilot | Test |
|-----------|--------------|----------------------|-------|------|
| Count | 36,952 | 36,952 | 3,087 | 56 |
| Mean | 25.84°C | 25.84°C | 27.29°C | 27.11°C |
| Std | 0.73°C | 0.73°C | 1.47°C | 2.36°C |
| Min | 22.4°C | 22.4°C | 26.0°C | 26.2°C |
| Median | 26.0°C | 26.0°C | 26.8°C | 26.2°C |
| Max | 27.0°C | 27.0°C | 32.9°C | 34.2°C |

### Humidity Statistics

| Statistic | Normal (All) | Normal (Train Cand.) | Pilot | Test |
|-----------|--------------|----------------------|-------|------|
| Count | 36,952 | 36,952 | 3,087 | 56 |
| Mean | 61.71% | 61.70% | 57.54% | 62.13% |
| Std | 4.04% | 4.04% | 5.23% | 6.58% |
| Min | 46.8% | 46.8% | 44.4% | 59.3% |
| Median | 63.0% | 63.0% | 58.8% | 59.5% |
| Max | 97.2% | 97.2% | 95.8% | 82.1% |

### Key Findings
1. **Humidity baseline shift:** Normal data (~62-64%) vs Pilot/Test (~59-60%).
2. **Temperature median similar:** ~26.0°C across all datasets.
3. **Pilot/Test have wider spreads** due to contained anomalies.
4. **Test humidity median (59.5%)** closer to Pilot (58.8%) than Normal (63.0%).

> ⚠️ **Dataset shift confirmed.** Different environmental conditions during collection. Ensure training data matches deployment environment.

---

## 7. Files Generated

All files saved to `data/processed/`. Original files in `data/raw/` **unchanged**.

| File | Rows | Description |
|------|------|-------------|
| `normal_data_deduplicated_all.csv` | 36,952 | Normal data, exact duplicates removed |
| `normal_data_training_candidate.csv` | 36,952 | Identical to above (no suspicious rows found) |
| `normal_data_duplicate_audit.csv` | 12,776 | Exact duplicates removed (for audit) |
| `normal_data_suspected_tail.csv` | 0 | No suspicious tail found (EDA artifact) |
| `normal_data_repeated_timestamps_report.csv` | 304 | Timestamps with different sensor values |
| `pilot_data_prepared.csv` | 3,087 | Pilot data, all rows preserved |
| `pilot_event_annotations.csv` | 2 | Preliminary event annotations |
| `test_data_with_labels.csv` | 56 | Test data with row-level labels (0/1) |

---

## 8. Decisions Requiring Manual Review

| Issue | Status | Action Needed |
|-------|--------|---------------|
| **Repeated timestamps (304 rows)** | Flagged, kept | Investigate: logging bug vs. real rapid changes |
| **Pilot event boundaries** | Preliminary annotations | Manually verify event start/end times |
| **Dataset shift (humidity baseline)** | Documented | Ensure training data matches deployment environment |
| **High humidity readings (>90%)** | Flagged, kept | Determine if sensor saturation or real environment |

---

## 9. Summary

| Operation | Input Rows | Output Rows | Change |
|-----------|------------|-------------|--------|
| Normal: exact dedup | 49,728 | 36,952 | -12,776 (25.7%) |
| Normal: repeated ts | 36,952 | 36,952 | 0 (flagged only) |
| Normal: suspicious tail | 36,952 | 36,952 | 0 (none found) |
| Pilot: prepare | 3,087 | 3,087 | 0 (preserved) |
| Test: add labels | 56 | 56 | 0 (labels added) |

**All original files in `data/raw/` remain unchanged.** ✅