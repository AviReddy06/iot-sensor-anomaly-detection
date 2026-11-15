# Evaluation Protocol: AI-Based IoT Sensor Anomaly Detection

**Project:** AI-Based IoT Sensor Anomaly Detection (ESP32 + DHT11)  
**Student:** Dungu Avinash Reddy | **Roll:** RK3P25KZA09 | **Reg:** 12509090  
**Version:** 1.0 | **Date:** 2026-11-15

---

## 1. Dataset Inventory

Every dataset used in evaluation is catalogued below with provenance, role, size, event count, label source, and allowed use.

| Dataset | Provenance | Role | Rows | Events | Label Source | Allowed Use |
|---------|------------|------|------|--------|--------------|-------------|
| **test** (test_data_with_labels.csv) | Recorded (ESP32 + DHT11, student's room) | Development | 56 | 1 (10 rows) | Student-annotated (blowing on sensor) | Model selection, threshold tuning, development reporting |
| **pilot** (pilot_data.csv) | Recorded (ESP32 + DHT11, student's room) | Development | 3,087 | 2 (orig: 46 rows; rev: 504 rows) | Student-annotated, expanded post-hoc in commit 4f8ca08 | **BOTH label sets reported** — original 46-row and revised 504-row; pilot is development data due to post-hoc expansion |
| **normal** (normal_data.csv) | Recorded (ESP32 + DHT11, student's room) | Development | 49,727 | 0 (baseline) | N/A (unlabelled baseline) | Training data only; 389 rows quarantined as anomalies |
| **eval_suite** (eval_test_suite.csv) | Synthetic injections (seed 42) on held-out normal rows | Held-out | 1,950 | 143 (6 fault types) | Synthetic injection labels | Independent evaluation; **no tuning allowed** |
| **UCI #357** (Occupancy Detection) | Public benchmark (Recorded occupancy) | Held-out | ~2,000 | 400 (injected) | Synthetic injection on unoccupied rows | Cross-domain validation; **no tuning allowed** |
| **IoTsec** (Room-Climate Location A Node 1) | Public benchmark (ESORICS 2017) | Held-out | ~2,457 | 490 (injected) | Synthetic injection on clean baseline | Cross-domain validation; **no tuning allowed** |

### Key Provenance Notes
- **Recorded**: Physical sensor data collected by the student using ESP32 + DHT11
- **Synthetic**: Anomalies injected programmatically into clean baseline data (seeds: 42 for eval_suite, 357 for UCI, 2017 for IoTsec)
- **Development**: Any dataset on which model constants (thresholds, feature scaling, hyperparameters) were fitted or selected
- **Held-out**: Datasets used only for final evaluation with zero tuning

---

## 2. Evaluation Rules

### 2.1 Development vs. Held-out Classification
- **Development set**: Any dataset on which any constant was fitted (thresholds, feature scaling parameters, hyperparameters, contamination settings). This includes:
  - `normal_data.csv` (training data, 34,374 clean rows after quarantine)
  - `test.csv` (used for threshold selection in v1)
  - `pilot_data.csv` (used for threshold selection in v2; labels expanded post-hoc)
- **Held-out set**: Datasets never used for any fitting or selection:
  - `eval_suite` (synthetic, seed 42)
  - `UCI #357` (synthetic injections on benchmark data)
  - `IoTsec` (synthetic injections on benchmark data)

### 2.2 Pilot Dataset — Dual Reporting Requirement
The pilot annotations were expanded **after results were seen** (commit 4f8ca08): event 1 from 27 rows to 466, total positives from 46 to 504.
- **Both label sets MUST be reported**: Original 46-row labels AND revised 504-row labels
- Pilot results are **Development data** — they informed threshold selection
- Flag all pilot results with: `FLAG: Labels expanded post-hoc after inspecting detector output`

### 2.3 Synthetic Results — Never Mixed with Real-Event Results
- Synthetic injection results (eval_suite, UCI #357, IoTsec) are **never averaged or combined** with recorded event results (test, pilot)
- They are reported in separate tables/sections with clear "Synthetic" provenance labels
- Any summary claiming "overall performance" must separate synthetic from recorded

### 2.4 Threshold Tuning Transparency
- The 0.25th percentile threshold (-0.21657) used in "Medium" sensitivity was chosen for best F1 on the **synthetic eval_suite** (Development)
- Web backend uses: Low = 0.5th percentile, Medium = 1st percentile (default), High = 5th percentile
- The Medium default (1st percentile, -0.1768) differs from the tuned Medium (0.25th percentile, -0.21657)

### 2.5 Dataset Overlap Disclosure
- `data/raw/test.csv` (55 rows) and `data/raw/pilot_data.csv` share **35 identical rows** (22:02:14 to 22:03:23 on 2026-10-27)
- The pilot has no rows for 22:03:25–22:04:05 where test.csv holds the 10-row event
- This overlap must be disclosed in all evaluation reports

---

## 3. Models to Evaluate

| Model | Description | Threshold Source |
|-------|-------------|------------------|
| **Z-Score Baseline** | Raw Z-score > 3.0 on temperature OR humidity | Fixed (3.0) |
| **Adaptive EWMA-Z** | Gated EWMA residuals with Cauchy robust scaling | thresholds.json: ewma_zscore_threshold |
| **Isolation Forest** | Gated IF (persistence window=5, min_hits=3) | thresholds.json: iforest_threshold |
| **Hybrid (IF + EWMA-Z)** | Logical OR of IF and EWMA-Z flags | Both above |
| **v1 Baseline (from tag v1-two-method-baseline)** | 14 features, Z-score vs IF, threshold = 1st percentile normal scores | Historical (from tag) |

### Sensitivity Levels (Web Backend)
| Level | Percentile | Threshold (iforest) | Use |
|-------|------------|---------------------|-----|
| Low | 0.5th | -0.2008 | Conservative |
| Medium | 1st (default) | -0.1768 | Balanced |
| High | 5th | -0.1136 | Sensitive |

---

## 4. Metrics Required Per Evaluation

For each (model, dataset, label-set) combination, report:

### 4.1 Row-Level Metrics
- `rows`: Total rows evaluated
- `positives`: Ground truth anomaly rows
- `tp`, `fp`, `fn`: Confusion matrix counts
- `precision`, `recall`, `f1`: Standard binary classification metrics

### 4.2 Event-Level Metrics
- **Event-level recall**: Fraction of ground-truth events where ≥1 row flagged from event start to 10s after event end
- **Detection delay**: Mean seconds from event start to first flagged row (only for detected events)

### 4.3 False Alarm Rate
- **False alarms per day on normal baseline**: Group consecutive flagged normal rows (gap ≤10s) into events; count events per 24h of normal data

### 4.4 Uncertainty Quantification
- **95% Block Bootstrap Interval** over events (2,000 resamples, seed 42):
  - Resample events (not rows) with replacement
  - Compute metric on each resample
  - Report 2.5th and 97.5th percentiles
  - **Explicitly state** when interval is too wide to conclude (e.g., CI width > 0.5 for recall)

### 4.5 Random Detector Control
- Flag same fraction of rows as the detector under test
- Compute metrics for this random baseline
- Report as "Random Detector Control" row

### 4.6 Metadata
- `provenance`: "Recorded" or "Synthetic"
- `role`: "Development" or "Held-out"

---

## 5. Robustness Tests (All Synthetic, Kept Small)

| Perturbation | Parameter | Metric |
|--------------|-----------|--------|
| Additive noise | σ = 0.1°C, 0.3°C | False alarms/hr, Event recall |
| Dropped readings | 5% random dropout | False alarms/hr, Event recall |
| Step offset | +3°C step | False alarms/hr, Event recall |
| Stuck sensor | 5-minute constant value | False alarms/hr, Event recall |

---

## 6. Code Freeze Verification

- `results/freeze.json` contains SHA256 of:
  - `models/iforest.joblib`
  - `models/scaler.joblib`
  - `models/thresholds.json`
  - Feature engineering code (`features/feature_engine.py`, `features/build_features_v2.py`)
  - Commit hash
- `evaluate/run_all.py` **must verify these hashes** and refuse to run if any changed
- Local tag: `eval-freeze`

---

## 7. v1 Baseline Comparison

- Checkout tag `v1-two-method-baseline` (commit 04e6139) in temporary worktree
- Run identical evaluation on test, pilot (both label sets), eval_suite
- Report side-by-side with v2 results

---

## 8. Output Artifacts

| File | Description |
|------|-------------|
| `results/evaluation_results.json` | Full machine-readable results |
| `results/evaluation_results.csv` | Flattened table for spreadsheet import |
| `results/evaluation_results.md` | Human-readable Markdown table |
| `docs/MODEL_CARD.md` | Model card with limitations |
| `docs/DATASHEET.md` | Dataset card with provenance |

---

## 9. Commit

Final commit: "Evaluation protocol, freeze and run_all"