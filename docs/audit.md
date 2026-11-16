# Project Audit Report

Audit conducted in Phase 0 on local repository state at commit `10347c2` (detached HEAD verification performed in isolated temporary worktrees).

---

## 1. Environment and Repository Status

- **Git Status (`git status --short`)**:
  ```text
  ?? backend/
  ?? docs/IoT_Anomaly_Detection_IEEE_Report_Final.docx
  ?? docs/IoT_Anomaly_Detection_IEEE_Report_v2.docx
  ?? docs/REPORT_REVIEW_NOTES.md
  ?? docs/figures/
  ?? docs/figures_final/
  ?? docs/ieee_report.md
  ?? frontend/
  ?? run_ui.py
  ```
- **Git History (`git log --format="%h %ad %s" --date=iso`)**:
  ```text
  10347c2 2026-11-10 18:41:41 +0530 Auto-reclaim stale/other-tab COM port leases across Streamlit pages and browser refreshes
  b14f4cf 2026-11-10 18:31:30 +0530 Add building-wide employee alert system (ntfy push, webhooks, SMTP) with cooldowns and AC guardrails
  27796c4 2026-11-10 18:08:00 +0530 Fix fresh-clone Pilot demo fallback, rotate narrow score plot x-ticks, and test all demo modes
  4f8ca08 2026-11-10 18:00:09 +0530 Complete ESP32 DHT11 IoT anomaly detection system, dashboards, notebooks, and tests
  f22ce24 2026-11-05 11:18:36 +0530 Archive notebook build and repair scripts
  a5342ce 2026-11-05 11:15:46 +0530 Add contamination audit and pilot evaluation
  86e8fd2 2026-11-05 10:46:07 +0530 Add Streamlit dashboard
  04e6139 2026-11-05 10:23:45 +0530 Add trained models, training script and features v2 data
  ed78f40 2026-11-04 16:46:29 +0530 Track data/processed including features v2
  04d8254 2026-11-04 16:39:43 +0530 Add session-aware features v2 script
  9b5416e 2026-11-04 11:26:04 +0530 Snapshot before feature-engineering fix
  ```
- **Runtimes & Installed Package Versions**:
  - `node`: `v22.23.2`
  - `python`: `3.14.8`
  - `fastapi`: `0.142.2`
  - `uvicorn`: `0.54.0`
  - `websockets`: `17.2`
  - `scikit-learn`: `1.9.1`
  - `pandas`: `3.0.6`
  - `pydantic`: `2.13.5`
  - `pyserial`: `3.5`
  - `pytest`: `9.1.1`

---

## 2. Existing Web Application Architecture ("IoT Anomaly Hub")

1. **Streamlit Monolith**:
   - **Stack**: Streamlit multi-page app (`streamlit>=1.39.0`, `plotly`, `seaborn`, `matplotlib`).
   - **Entry Points**: `dashboard/Home.py`, `dashboard/user_app.py`, `dashboard/admin_app.py`.
   - **Pages**: `dashboard/pages/1_Analyse.py`, `dashboard/pages/2_Results.py`, `dashboard/pages/3_Model_Metrics.py`.
   - **Serial Handling**: `dashboard/serial_reader.py` using `SafeSerialReader` and `dashboard/port_lease.py`. Suppresses bootloader reset via `dtr=False`, `rts=False`.
   - **Authentication**: None.
   - **Storage**: In-memory session state, `logs/alert_history.csv`.
   - **Tests**: `tests/integration/test_streamlit_smoke.py`.
2. **FastAPI + React Prototype** (Untracked worktree upgrade):
   - **Stack**: FastAPI backend with WebSockets + React 19 / Vite SPA.
   - **Entry Point**: `run_ui.py` -> `backend.app:app`.
   - **Routes**: REST at `/api/*`, WebSocket at `/ws/telemetry`.
   - **Serial Handling**: `backend/services/serial_service.py` background thread.
   - **Authentication**: None currently implemented.

---

## 3. Verification of v1 Model Commit (14 Features, Threshold -0.16307)

- **Identified Commit**: `04e6139` (*"Add trained models, training script and features v2 data"*).
- **Verification Method**: Checked out into an isolated temporary worktree (`$env:TEMP\v1_verify`). Executed `python train/train_models.py`.
- **Output Results**:
  - `Feature columns (14)`: `['temperature', 'humidity', 'temperature_change', 'humidity_change', 'temperature_abs_change', 'humidity_abs_change', 'temp_rolling_mean_5', 'temp_rolling_std_5', 'hum_rolling_mean_5', 'hum_rolling_std_5', 'temp_rolling_mean_15', 'temp_rolling_std_15', 'hum_rolling_mean_15', 'hum_rolling_std_15']`
  - `Normal shape`: `(36941, 14)`
  - `Isolation Forest threshold (1st percentile of normal scores)`: `-0.16307013076608584`
  - Exact match verified.

---

## 4. Pilot Labels Audit (`data/processed/pilot_event_annotations.csv`)

- **Commit Changing Annotations**: `4f8ca08` (*"Complete ESP32 DHT11 IoT anomaly detection system, dashboards, notebooks, and tests"*).
- **Comparison**:
  - **Prior Commit (`ed78f40` / `a5342ce`)**:
    - Event 1: `2026-10-27 23:09:38` to `23:10:30` (52.0s duration, 27 rows), status `"preliminary - needs manual verification"`.
    - Event 2: `2026-10-28 00:34:20` to `00:34:56` (36.0s duration, 19 rows), status `"preliminary - needs manual verification"`.
    - Total positive raw rows: `46`.
  - **Revised Commit (`4f8ca08`)**:
    - Event 1: `2026-10-27 23:09:38` to `23:40:28` (1850.0s duration, 466 rows), status `"verified against full pilot trace"`. Description noted breath humidity spike followed by prolonged heat/dry recovery tail across session resume.
    - Event 2: `2026-10-28 00:34:20` to `00:35:35` (75.0s duration, 38 rows), status `"verified against full pilot trace"`.
    - Total positive raw rows: `504` (503 feature rows).
- **Timing and Justification**:
  - In `a5342ce`, pilot evaluation flagged 430 z-score rows and 326 Isolation Forest rows as anomalous (10.6%–13.9% of pilot data). Because Event 1's ground truth was truncated to 52 seconds, hundreds of physically disturbed recovery readings were classified as false alarms.
  - The revision in commit `4f8ca08` occurred *after* these results were observed. The ground truth window was extended post-hoc to include the entire physical thermal and moisture stabilization tail (until 23:40:28), transforming those previously unlabelled flags into true positives.

---

## 5. Evaluation Sets and Fault Generators

- **Script**: `preprocess/clean_datasets.py` (`build_evaluation_suite()`).
- **Base**: 1,891 unseen clean normal baseline rows from held-out dates (`timestamp >= 2026-11-01`), plus 59 live DHT11 baseline readings.
- **Random Seed**: `seed=42` (`np.random.default_rng(42)`).
- **Fault Injections**:
  1. `breath_spike`: 18 rows, synthetic mathematical injection (rapid breath jump + exponential recovery).
  2. `heat_source_burst`: 24 rows, synthetic mathematical injection (sinusoidal heating burst).
  3. `cold_draft_drop`: 20 rows, synthetic mathematical injection (temperature drop envelope).
  4. `offset_fault`: 20 rows, synthetic step calibration jump (+4.8°C / -10.5% RH).
  5. `slow_drift_fault`: 45 rows, synthetic linear ramp (+0.6°C to +5.5°C, +2% to +18% RH).
  6. `chatter_noise_fault`: 16 rows, synthetic discrete jitter choice.
  - **Total Synthetic Anomaly Rows**: `143` rows across 6 fault scenarios.
  - **Clean Baseline Rows**: `1,804` (1,747 normal holdout + 57 live DHT11 normal feature rows).
- **External Benchmarks (`evaluate/benchmark_external.py`)**:
  - UCI Occupancy Detection (#357): 3,757 train / 1,999 test rows. Anomalies were synthetically injected (4 episodes, 400 anomaly rows, `seed=101`) onto unoccupied clean baseline telemetry.
  - IoTsec Room-Climate: 2,044 train / 2,457 test rows. Injected 4 anomaly episodes (490 anomaly rows, `seed=101`) onto clean baseline.

---

## 6. Training Data Quarantine Rule

- **Implementation**: `preprocess/clean_datasets.py` (`quarantine_unlabeled_anomalies()`).
- **Rows Removed**: Exactly `389` rows quarantined into `data/processed/normal_quarantined_anomalies.csv`.
- **Columns & Conditions**:
  - `dH.abs() >= 1.5`
  - `dT.abs() >= 0.4`
  - `rate_H >= 0.7` (% / s)
  - `humidity > 72.0%`
  - Temporal padding: `±30` seconds around every flagged seed inside the same session.
  - Forward recovery extension: contiguous rows inside the session while `humidity > 70.0%` or `|dH| >= 0.5%`.
- **Derivation**: The constants were formulated after inspecting moisture/breath anomalies present in session 9 of `normal_data.csv`. The threshold values align with the physical breath-spike signatures observed in pilot data.

---

## 7. Tuning and Calibration Order of Operations

- **Order of Operations in `train/train_models.py`**:
  1. Load `data/features/normal_features_full.csv` (34,374 clean normal rows, 12 features).
  2. Fit `StandardScaler` on normal training data.
  3. Fit `IsolationForest(n_estimators=200, contamination=0.01, random_state=42)`.
  4. Compute `normal_scores = iso.decision_function(X_normal_scaled)`.
  5. Calibrate threshold percentiles from `normal_scores`:
     - Low (0.1th percentile): `-0.22858`
     - Medium (0.25th percentile, default): `-0.21657`
     - High (1.0th percentile): `-0.17681`
  6. Compute baseline statistics on normal training features (`normal_temp_mean=25.67`, `normal_temp_std=0.83`, `normal_hum_mean=61.42`, `normal_hum_std=4.40`, `ewma_temp_std=0.665`, `ewma_hum_std=3.056`).
  7. Fit comparison baselines (`OneClassSVM`, `LocalOutlierFactor`) on 6,000-row normal subsample.
  8. Save artifacts (`models/iforest.joblib`, `models/scaler.joblib`, `models/thresholds.json`).
  9. Evaluate on test, pilot, and eval suite datasets; serialize `models/evaluation_summary.json`.
- **Calibration Provenance of Hybrid Constants**:
  - `iforest_threshold`: Calibrated directly on normal training scores (0.25th percentile).
  - `ewma_zscore_threshold` (3.5): Engineering heuristic threshold to minimize false alarms on steady diurnal variance.
  - `ewma_halflife_sec` (2400s): Domain heuristic chosen to track thermal inertia of residential/office buildings.
  - `persistence_window` (5) and `persistence_min_hits` (3): 3-of-5 majority voting filter to prevent single-sample DHT11 sensor bit-flip glitches.

---

## 8. Data Leakage and Dataset Comparison

### Time Ranges and Overlaps

| Dataset File | Rows | Start Timestamp | End Timestamp | Overlap with Training |
| :--- | :--- | :--- | :--- | :--- |
| `data/raw/normal_data.csv` | 49,728 | 2026-10-29 16:39:00 | 2026-11-01 17:52:32 | N/A (raw source) |
| `data/processed/normal_data_clean.csv` | 34,383 | 2026-10-29 16:39:00 | 2026-10-31 01:18:35 | **0** overlap with held-out eval suite |
| `data/processed/eval_test_suite.csv` | 1,950 | 2026-11-01 16:48:45 | 2026-11-10 17:20:32 | **0** overlap with training set |
| `data/raw/pilot_data.csv` | 3,087 | 2026-10-27 22:02:14 | 2026-10-28 01:05:47 | **0** overlap with training set |
| `data/raw/test.csv` | 56 | 2026-10-27 22:02:14 | 2026-10-27 22:04:05 | **0** overlap with training set |

### Comparison: `data/raw/test.csv` vs `data/raw/pilot_data.csv` (22:02:14 to 22:04:05)

- **Total Unique Timestamps in Window**: 56
- **Identical Rows**: 35 rows (from `2026-10-27 22:02:14` through `22:03:23`). Both files record identical `(temperature, humidity)` values.
- **Differing Rows (21 rows)**: Between `22:03:25` and `22:04:05`, `pilot_data.csv` is completely missing data (dropped sensor readings/connection gap), whereas `test.csv` contains the entire breath/heat anomaly spike (10 anomaly rows) and recovery (11 normal rows).

#### Differing Rows Table
```text
Timestamp           | test.csv (Temp, Hum)           | pilot_data.csv
--------------------+--------------------------------+-------------------
2026-10-27 22:03:25 | test: (26.2 C, 59.7% RH)       | pilot: MISSING
2026-10-27 22:03:27 | test: (26.2 C, 59.7% RH)       | pilot: MISSING
2026-10-27 22:03:29 | test: (32.5 C, 75.0% RH) [ANOM]| pilot: MISSING
2026-10-27 22:03:31 | test: (33.1 C, 78.2% RH) [ANOM]| pilot: MISSING
2026-10-27 22:03:33 | test: (33.8 C, 80.5% RH) [ANOM]| pilot: MISSING
2026-10-27 22:03:35 | test: (34.2 C, 82.1% RH) [ANOM]| pilot: MISSING
2026-10-27 22:03:37 | test: (33.9 C, 81.8% RH) [ANOM]| pilot: MISSING
2026-10-27 22:03:39 | test: (33.2 C, 79.5% RH) [ANOM]| pilot: MISSING
2026-10-27 22:03:41 | test: (32.0 C, 75.3% RH) [ANOM]| pilot: MISSING
2026-10-27 22:03:43 | test: (27.5 C, 68.0% RH) [ANOM]| pilot: MISSING
2026-10-27 22:03:45 | test: (26.5 C, 62.0% RH) [ANOM]| pilot: MISSING
2026-10-27 22:03:47 | test: (26.3 C, 60.2% RH) [ANOM]| pilot: MISSING
2026-10-27 22:03:49 | test: (26.2 C, 59.8% RH)       | pilot: MISSING
2026-10-27 22:03:51 | test: (26.2 C, 59.6% RH)       | pilot: MISSING
2026-10-27 22:03:53 | test: (26.2 C, 59.5% RH)       | pilot: MISSING
2026-10-27 22:03:55 | test: (26.2 C, 59.5% RH)       | pilot: MISSING
2026-10-27 22:03:57 | test: (26.2 C, 59.5% RH)       | pilot: MISSING
2026-10-27 22:03:59 | test: (26.2 C, 59.4% RH)       | pilot: MISSING
2026-10-27 22:04:01 | test: (26.2 C, 59.4% RH)       | pilot: MISSING
2026-10-27 22:04:03 | test: (26.2 C, 59.4% RH)       | pilot: MISSING
2026-10-27 22:04:05 | test: (26.2 C, 59.4% RH)       | pilot: MISSING
```

---

## 9. Reproduction in Clean Isolated Copy

- Executed in clean worktree outside the repository (`$env:TEMP\head_verify`):
  - `python -m pytest -q`: **49 passed in 15.50s**.
  - Pipeline execution: `clean_datasets.py` -> `build_features_v2.py` -> `train_models.py` -> `evaluate_suite.py` -> `evaluate_pilot.py`.
- **Results vs `README.md`**:
  - Test set, Pilot set, and Eval Suite metrics matched `README.md` to 3 decimal places.
  - **README Presentation Discrepancy Found**: For the external `IoTsec Room-Climate` benchmark, `README.md` highlighted `Recall=0.994`, `PR-AUC=0.997`, and `ROC-AUC=0.998`, but omitted reporting that the model generated **470 false positives**, resulting in a precision of only **0.509**.

---

## 10. Secrets Audit

- Executed `git grep -I -i -E "password|passwd|secret|token|ADMIN"` across all tracked files.
- **Findings**:
  - No active tokens, passwords, or secrets are stored in Git.
  - `.env.example` contains only blank template fields.
  - `alerts/notifier.py` accesses passwords strictly from environment variables (`ALERT_EMAIL_PASSWORD`).
  - Unit tests use mock dummy credentials (`"app-password"`).
- **Result**: PASS (No credentials leaked; no rotation required).

---

## 11. Serial Port Usage

Tracked files importing `serial` or calling `serial.Serial`:
1. `collect/serial_utils.py` (`open_serial_connection` with `dtr=False`, `rts=False`).
2. `dashboard/pages/1_Analyse.py` (`serial.SerialException` exception handling).
3. `dashboard/user_app.py` (`serial.SerialException` exception handling).
Untracked / Backend files:
4. `backend/services/serial_service.py` (`open_serial_connection` with `dtr=False`, `rts=False`, background thread).

---

## 12. Claims Verification Matrix

| Claim / Component | Status | Evidence |
| :--- | :--- | :--- |
| v1 model has 14 features and -0.16307 threshold | **VERIFIED** | Reproduced in isolated worktree at commit `04e6139` (`train_models.py`). |
| 49 pytest unit/integration tests pass | **VERIFIED** | `49 passed in 15.50s` on clean worktree run. |
| Pilot annotations changed post-hoc | **VERIFIED** | Commit `4f8ca08` expanded Event 1 from 52s (27 rows) to 1850s (466 rows) after pilot false alarms were observed. |
| Evaluation suite contains synthetic faults | **VERIFIED** | `clean_datasets.py` injects 143 mathematical anomaly rows (`seed=42`) across 6 fault types onto held-out clean baseline. |
| External benchmarks contain synthetic injections | **VERIFIED** | `benchmark_external.py` injects 4 fault episodes (`seed=101`) onto clean UCI #357 and IoTsec traces. |
| Training set quarantine removed 389 rows | **VERIFIED** | `quarantine_unlabeled_anomalies()` removed 389 breath/moisture rows via rate and humidity thresholds. |
| No timestamp leakage between clean train and eval suite | **VERIFIED** | 0 timestamp overlaps between `normal_data_clean.csv` and `eval_test_suite.csv`. |
| `test.csv` shares 35 rows with `pilot_data.csv` | **VERIFIED** | Timestamps `22:02:14` to `22:03:23` match identically; anomaly window `22:03:25` to `22:04:05` missing from pilot. |
| Repository contains no tracked secrets | **VERIFIED** | Full regex audit confirmed zero secrets tracked in Git. |
