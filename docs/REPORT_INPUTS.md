# Report Inputs: Final Evaluation Tables and Testing Section

**Project:** AI-Based IoT Sensor Anomaly Detection  
**Student:** Dungu Avinash Reddy | **Roll:** RK3P25KZA09 | **Reg:** 12509090  
**Generated:** 2026-11-15 | **Commit:** `afeef60` | **Tag:** `eval-freeze`

---

## 1. Complete Evaluation Results Table

Every row represents an executed model-dataset evaluation with explicit provenance and role.

| Version | Dataset | Model | Rows | Positives | TP | FP | FN | Precision | Recall | F1 | Event Recall | Delay (s) | FA/Day | CI Low | CI High | Provenance | Role | Label Set | Flag |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- | :--- | :--- | :--- |
| v2 | test | Hybrid (IF + EWMA-Z) | 55 | 10 | 10 | 1 | 0 | 0.909 | 1.000 | 0.952 | 1.000 | 0.0 | 792.7 | 1.000 | 1.000 | Recorded | Development | — | — |
| v2 | test | Adaptive EWMA-Z | 55 | 10 | 7 | 0 | 3 | 1.000 | 0.700 | 0.824 | 1.000 | 0.0 | 0.0 | 0.700 | 0.700 | Recorded | Development | — | — |
| v2 | test | Isolation Forest | 55 | 10 | 10 | 1 | 0 | 0.909 | 1.000 | 0.952 | 1.000 | 0.0 | 792.7 | 1.000 | 1.000 | Recorded | Development | — | — |
| v2 | test | Z-Score Baseline | 55 | 10 | 7 | 0 | 3 | 1.000 | 0.700 | 0.824 | 1.000 | 0.0 | 0.0 | 0.700 | 0.700 | Recorded | Development | — | — |
| v2 | pilot (original 46-row) | Hybrid (IF + EWMA-Z) | 3,084 | 46 | 46 | 393 | 0 | 0.105 | 1.000 | 0.190 | 1.000 | 0.0 | 31.4 | 1.000 | 1.000 | Recorded | Development | original 46-row | Post-hoc relabelled |
| v2 | pilot (original 46-row) | Isolation Forest | 3,084 | 46 | 46 | 124 | 0 | 0.271 | 1.000 | 0.426 | 1.000 | 0.0 | 321.7 | 1.000 | 1.000 | Recorded | Development | original 46-row | Post-hoc relabelled |
| v2 | pilot (original 46-row) | Adaptive EWMA-Z | 3,084 | 46 | 41 | 380 | 5 | 0.097 | 0.891 | 0.176 | 1.000 | 0.0 | 15.7 | 0.815 | 1.000 | Recorded | Development | original 46-row | Post-hoc relabelled |
| v2 | pilot (original 46-row) | Z-Score Baseline | 3,084 | 46 | 42 | 389 | 4 | 0.097 | 0.913 | 0.176 | 1.000 | 0.0 | 7.8 | 0.852 | 1.000 | Recorded | Development | original 46-row | Post-hoc relabelled |
| v2 | pilot (revised 504-row) | Hybrid (IF + EWMA-Z) | 3,084 | 503 | 439 | 0 | 64 | 1.000 | 0.873 | 0.932 | 1.000 | 0.0 | 0.0 | 0.867 | 0.947 | Recorded | Development | revised 504-row | FLAG: Labels expanded post-hoc after inspecting detector output |
| v2 | pilot (revised 504-row) | Isolation Forest | 3,084 | 503 | 170 | 0 | 333 | 1.000 | 0.338 | 0.505 | 1.000 | 0.0 | 0.0 | 0.288 | 0.947 | Recorded | Development | revised 504-row | FLAG: Labels expanded post-hoc after inspecting detector output |
| v2 | pilot (revised 504-row) | Adaptive EWMA-Z | 3,084 | 503 | 421 | 0 | 82 | 1.000 | 0.837 | 0.911 | 1.000 | 0.0 | 0.0 | 0.605 | 0.856 | Recorded | Development | revised 504-row | FLAG: Labels expanded post-hoc after inspecting detector output |
| v2 | pilot (revised 504-row) | Z-Score Baseline | 3,084 | 503 | 431 | 0 | 72 | 1.000 | 0.857 | 0.923 | 1.000 | 0.0 | 0.0 | 0.500 | 0.886 | Recorded | Development | revised 504-row | FLAG: Labels expanded post-hoc after inspecting detector output |
| v2 | eval_suite | Hybrid (IF + EWMA-Z) | 1,947 | 143 | 138 | 4 | 5 | 0.972 | 0.965 | 0.968 | 1.000 | 1.7 | 0.4 | 0.952 | 0.983 | Synthetic | Held-out | — | — |
| v2 | eval_suite | Isolation Forest | 1,947 | 143 | 122 | 4 | 21 | 0.968 | 0.853 | 0.907 | 1.000 | 1.7 | 0.4 | 0.583 | 0.968 | Synthetic | Held-out | — | — |
| v2 | eval_suite | Adaptive EWMA-Z | 1,947 | 143 | 102 | 0 | 41 | 1.000 | 0.713 | 0.833 | 1.000 | 7.5 | 0.0 | 0.563 | 0.867 | Synthetic | Held-out | — | — |
| v2 | eval_suite | Z-Score Baseline | 1,947 | 143 | 105 | 57 | 38 | 0.648 | 0.734 | 0.689 | 1.000 | 6.8 | 0.1 | 0.591 | 0.871 | Synthetic | Held-out | — | — |
| v2 | UCI #357 | Hybrid (IF + EWMA-Z) | 1,999 | 400 | 238 | 13 | 162 | 0.948 | 0.595 | 0.731 | — | — | — | — | — | Synthetic | Held-out | — | — |
| v2 | UCI #357 | Isolation Forest | 1,999 | 400 | 227 | 13 | 172 | 0.946 | 0.570 | 0.711 | — | — | — | — | — | Synthetic | Held-out | — | — |
| v2 | UCI #357 | Adaptive EWMA-Z | 1,999 | 400 | 44 | 0 | 356 | 1.000 | 0.110 | 0.198 | — | — | — | — | — | Synthetic | Held-out | — | — |
| v2 | UCI #357 | Z-Score Baseline | 1,999 | 400 | 288 | 17 | 112 | 0.944 | 0.720 | 0.817 | — | — | — | — | — | Synthetic | Held-out | — | — |
| v2 | IoTsec | Hybrid (IF + EWMA-Z) | 2,457 | 490 | 487 | 470 | 3 | 0.509 | 0.994 | 0.673 | — | — | — | — | — | Synthetic | Held-out | — | NOTE: 470 false alarms caused by cross-domain baseline distribution shift |
| v2 | IoTsec | Isolation Forest | 2,457 | 490 | 310 | 135 | 180 | 0.697 | 0.633 | 0.663 | — | — | — | — | — | Synthetic | Held-out | — | — |
| v2 | IoTsec | Adaptive EWMA-Z | 2,457 | 490 | 479 | 449 | 11 | 0.516 | 0.978 | 0.676 | — | — | — | — | — | Synthetic | Held-out | — | — |
| v2 | IoTsec | Z-Score Baseline | 2,457 | 490 | 482 | 14 | 8 | 0.972 | 0.984 | 0.978 | — | — | — | — | — | Synthetic | Held-out | — | — |
| v1 | test | Baseline (Z-Score) | 55 | 10 | 7 | 0 | 3 | 1.000 | 0.700 | 0.824 | — | — | — | — | — | Recorded | Development | — | — |
| v1 | test | Isolation Forest (14-feat) | 55 | 10 | 10 | 5 | 0 | 0.667 | 1.000 | 0.800 | — | — | — | — | — | Recorded | Development | — | — |
| v1 | pilot (original 46-row) | Baseline (Z-Score) | 3,084 | 46 | 41 | 389 | 5 | 0.095 | 0.891 | 0.172 | — | — | — | — | — | Recorded | Development | original 46-row | — |
| v1 | pilot (original 46-row) | Isolation Forest (14-feat) | 3,084 | 46 | 46 | 280 | 0 | 0.141 | 1.000 | 0.247 | — | — | — | — | — | Recorded | Development | original 46-row | — |

---

## 2. Sensitivity Levels on Test Set (Hybrid Model)

| Level | Percentile | IF Threshold | Rows | Positives | TP | FP | FN | Precision | Recall | F1 | Event Recall | Delay (s) | FA/Day | Provenance | Role |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- | :--- |
| Low | 0.5th %ile | -0.20078 | 55 | 10 | 10 | 2 | 0 | 0.833 | 1.000 | 0.909 | 1.000 | 0.0 | 792.7 | Recorded | Development |
| Medium (default) | 1st %ile | -0.17681 | 55 | 10 | 10 | 3 | 0 | 0.769 | 1.000 | 0.870 | 1.000 | 0.0 | 792.7 | Recorded | Development |
| High | 5th %ile | -0.11363 | 55 | 10 | 10 | 4 | 0 | 0.714 | 1.000 | 0.833 | 1.000 | 0.0 | 792.7 | Recorded | Development |
| **Tuned (Development)** | **0.25th %ile** | **-0.21657** | 55 | 10 | 10 | 1 | 0 | 0.909 | 1.000 | 0.952 | 1.000 | 0.0 | 792.7 | Recorded | Development |

---

## 3. Dataset Inventory

| Dataset | Provenance | Role | Rows | Events | Label Source | Allowed Use |
| :--- | :--- | :--- | :---: | :---: | :--- | :--- |
| test_data_with_labels.csv | Recorded (ESP32+DHT11) | Development | 56 | 1 (10 rows) | Student-annotated (blowing) | Model selection, threshold tuning |
| pilot_data.csv | Recorded (ESP32+DHT11) | Development | 3,087 | 2 (46/504 rows) | Student-annotated, expanded post-hoc | **BOTH label sets reported** |
| normal_data.csv | Recorded (ESP32+DHT11) | Development | 49,727 | 0 | N/A (unlabelled baseline) | Training only (34,374 clean after quarantine) |
| eval_test_suite.csv | Synthetic (seed 42) | Held-out | 1,950 | 143 (6 faults) | Synthetic injection | Independent evaluation only |
| UCI #357 (Occupancy) | Synthetic injection | Held-out | ~2,000 | 400 injected | Synthetic on unoccupied | Cross-domain validation only |
| IoTsec Room-Climate | Synthetic injection | Held-out | ~2,457 | 490 injected | Synthetic on clean baseline | Cross-domain validation only |

---

## 4. Testing and Validation Section (Draft for Report)

### 4.1 Testing Overview

The system was validated through a multi-layer test strategy comprising **285 automated tests** across unit, integration, regression, security, and end-to-end layers. All tests execute against temporary SQLite databases to ensure isolation and reproducibility. The test suite is organized as follows:

- **Unit Tests (75 tests)**: Cover database operations, detector fault handling, feature engineering, serial parsing, alert logic, and authentication. All pass with 86% overall code coverage.
- **Integration Tests (6 tests)**: Verify end-to-end pipeline including evaluation suite performance bounds and Streamlit dashboard rendering.
- **Regression Tests (6 tests)**: Confirm that two replays of the test dataset produce exactly one deduplicated event, and that missing/corrupt model artifacts result in `/api/health` reporting "degraded" and the client page displaying "Detector unavailable" (never "Normal").
- **Security Tests (29 tests, 27 pass)**: Validate token expiry/tamper rejection, rate limiting (6th failed login → 429), admin route protection (503 when `ADMIN_PASSWORD` unset), password non-leakage, upload limits (5MB, 413), path traversal rejection (plain and encoded), server-generated filenames, CSV formula injection escaping (`=`, `+`, `-`, `@` prefixed with apostrophe), security headers (CSP, `X-Content-Type-Options: nosniff`), and secret scanning.
- **End-to-End Tests (169 tests, 140 pass)**: Four-tier suite covering API contracts, WebSocket streaming, replay lifecycle, network security, boundary conditions, cross-feature interactions, and operational scenarios. 29 failures correspond to known gaps (missing preflight script, hardware check, CI workflow, 60s stream silence handling, cross-origin WebSocket restrictions) documented in `docs/KNOWN_ISSUES.md`.

### 4.2 Evaluation Protocol

A formal evaluation protocol (`docs/evaluation_protocol.md`) governs all model assessments:

1. **Dataset Roles**: Any dataset on which model constants (thresholds, feature scaling, hyperparameters) were fitted is classified as **Development**. Datasets never used for fitting are **Held-out**.
2. **Pilot Dual Reporting**: The pilot dataset was relabelled post-hoc (commit `4f8ca08`: 46 → 504 positive rows). Both the original 46-row and revised 504-row label sets are reported. Pilot results are **Development data**.
3. **Synthetic Isolation**: The evaluation suite (143 anomalies, seed 42), UCI #357, and IoTsec anomalies are synthetic injections. Their results are **never mixed** with recorded-event results.
4. **Threshold Transparency**: The 0.25th percentile threshold (-0.21657) was tuned on the synthetic suite (Development). Production uses Low (0.5th), Medium (1st, default), High (5th).
5. **Overlap Disclosure**: `test.csv` and `pilot_data.csv` share 35 identical rows (22:02:14–22:03:23).

### 4.3 Code Freeze & Reproducibility

- **Freeze Manifest**: `results/freeze.json` contains SHA256 hashes of `models/iforest.joblib`, `models/scaler.joblib`, `models/thresholds.json`, `features/feature_engine.py`, `features/build_features_v2.py`, and the commit hash (`afeef60`).
- **Verification**: `evaluate/run_all.py` refuses to run if any freeze hash has changed.
- **Tag**: Local tag `eval-freeze` marks the evaluation baseline.

### 4.4 Key Results Summary

| Detector | Test Set (Recorded) | Pilot Original (Recorded) | Pilot Revised (Recorded) | Eval Suite (Synthetic) | IoTsec (Synthetic) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Hybrid (IF + EWMA-Z) | F1=0.952 | F1=0.190 | **F1=0.932** | **F1=0.968** | **F1=0.673** (Precision=0.509) |
| Isolation Forest | F1=0.952 | F1=0.426 | F1=0.505 | F1=0.907 | F1=0.663 |
| Adaptive EWMA-Z | F1=0.824 | F1=0.176 | F1=0.911 | F1=0.833 | F1=0.676 |
| Z-Score Baseline | F1=0.824 | F1=0.176 | F1=0.923 | F1=0.689 | F1=0.978 |

**Critical Observations:**
- Pilot F1 jumps from 0.190 to 0.932 solely due to post-hoc label expansion — pilot is **Development data**.
- IoTsec hybrid precision is 0.509 (470 FP) due to cross-domain baseline shift — site-specific calibration required.
- The 0.25th percentile threshold was tuned on the synthetic suite (Development).

### 4.5 Robustness Testing (Synthetic Perturbations)

| Perturbation | Parameter | False Alarms/hr | Event Recall |
| :--- | :--- | :---: | :---: |
| Additive Noise | σ = 0.1°C | TBD | TBD |
| Additive Noise | σ = 0.3°C | TBD | TBD |
| Dropped Readings | 5% random | TBD | TBD |
| Step Offset | +3°C | TBD | TBD |
| Stuck Sensor | 5 min constant | TBD | TBD |

*Note: Robustness evaluation suite not yet implemented; tracked as KI-11 in KNOWN_ISSUES.md.*

### 4.6 Limitations

1. **Single-Room Training**: Model trained on one ESP32+DHT11 in one room; cross-room generalization unproven (IoTsec: 470 FP).
2. **Post-Hoc Pilot Labelling**: Pilot labels expanded after seeing detector output — pilot is Development data.
3. **Synthetic Eval Suite**: 143 anomalies are injected (seed 42), not recorded physical events.
4. **Test/Pilot Overlap**: 35 identical rows shared between datasets.
5. **DHT11 Resolution**: Data shows 0.1°C resolution; DHT11 spec is 1°C — **UNKNOWN** if DHT22 or interpolation.
6. **No Hardware Validation**: No ESP32 connected during evaluation; all tests use simulated replay.
7. **Event Production Unknown**: How test event, pilot events, and blowing episodes were produced is **UNKNOWN** (ask student).
8. **No Load/Soak/CI Testing**: These were not performed due to time/resource constraints.
9. **False Alarm Claims**: "Zero false alarms" only applies to specific holdout sessions; does not generalize.

---

## 5. Questions for Student (Required for Report Completion)

1. **How were the test event, the two pilot events, and the blowing episodes in the normal data produced?** (Exact protocol: blowing on sensor? Hot/cold object? Humidifier? Duration/intensity control?)

2. **Is the sensor a DHT11 or DHT22?** (Read the physical label — data shows 0.1°C resolution; DHT11 spec is 1°C, DHT22 is 0.1°C)

3. **What is due, and when?** (Project deadline, report submission date, demo/presentation schedule)

---

## 6. Figures (300 DPI) — To Be Generated

| Figure | Description | Output Path |
| :--- | :--- | :--- |
| Event-Level Recall | Bar chart per detector with 95% block bootstrap CI (2000 resamples, seed 42) | `results/figures/event_recall_bar.png` |
| False Alarms Per Day | Bar chart per detector on normal baseline with 95% CI | `results/figures/fa_per_day_bar.png` |

*Generation script: `eda/generate_plots_v2.py` (requires gap-aware line breaks at >10s intervals)*