# Project Completion & Repair Tasks (`tasks.md`)

**Project:** AI-Based IoT Sensor Anomaly Detection (ESP32 + DHT11)  
**Status:** Completed & Verified (2026-11-10)

---

## Dataset Plan (Strictly Separated by Role)
1. **Training (Production Hardware Model):** Cleaned `data/raw/normal_data.csv` (exact dupes, buffer bursts, and 389 unlabeled anomaly rows quarantined; chronological `< 2026-11-01` -> `34,383` raw / `34,374` feature rows). *(Raw source CSVs in `data/raw/` remain immutable.)*
2. **Validation & Local Testing:**
   - Re-annotated `data/raw/pilot_data.csv` (`data/processed/pilot_event_annotations.csv` fixed to include Event 1's full `23:09:38–23:40:28` window and Event 2 `00:34:20–00:35:35`, `504` raw / `503` feature positives).
   - Live ESP32 + DHT11 baselines collected on `2026-11-10` via `COM19` (`data/raw/live_baseline_2026-11-10.csv` & `data/raw/live_steady_2026-11-10.csv`, `59` raw / `57` feature rows, kept strictly unseen during training).
   - Controlled fault-injection suite on held-out clean Nov 1 baseline + live `COM19` baseline (`data/processed/eval_test_suite.csv`: `1,950` rows, `143` anomaly rows across `breath_spike`, `heat_source_burst`, `cold_draft_drop`, `offset_fault`, `slow_drift_fault`, `chatter_noise_fault`).
3. **External Benchmarking (Strictly Separate — Never Mixed Into Live Training):**
   - `IoTsec/Room-Climate-Datasets` (`data/benchmarks/room_climate_A_01.csv`, `A_06.csv`, isolated calibration).
   - `UCI Occupancy Detection (#357)` (`data/benchmarks/occupancy_detection_357.zip`, isolated 60s calibration).

---

## Phase 0 — Environment & Live Hardware Verification
- [x] Verify Python environment (`3.14.8`) & installed libraries against updated `requirements.txt`.
- [x] Probe connected Windows COM ports (`COM19`) to confirm the live ESP32 + DHT11 `temperature,humidity` stream at `115200` baud.
- [x] Update `firmware/esp32_dht11/esp32_dht11.ino` with physical range guards (`-10..65°C`, `0..100% RH`) while preserving `temperature,humidity\n` compatibility.
- [x] Verify real sensor resolution (`0.1°C / 0.1% RH` formatted precision) and update hardware verification notes across `docs/hardware.md`, `docs/serial_protocol.md`, `README.md`, and dashboards.

## Phase 1 — Repository Cleanup, Config Unification & Dependencies
- [x] Delete temporary root scripts (`fix_*.py`, `phase1_check.py`) and obsolete archive/empty clutter (`archive/repair_scripts/`, `archive/old_dashboard/app_v1.py`, `eda/generate_plots.py`, `data/processed/features/`, empty folders).
- [x] Update `requirements.txt` with all required runtime & test dependencies (`pyserial`, `pandas`, `numpy`, `scikit-learn`, `scipy`, `joblib`, `pyyaml`, `streamlit>=1.66`, `matplotlib`, `seaborn`, `plotly`, `pytest>=8.0`).
- [x] Unify `config.yaml` and `config.py` as the single source of truth (`models/*.joblib`, `models/thresholds.json`, `GAP_THRESHOLD=10`, `ROLL_MIN=2`, `ewma_halflife_sec=2400`, `scaler_type="standard"`, persistence/cooldown settings, `COM19`/`115200`).
- [x] Review repository file tracking and keep derived outputs clean.

## Phase 2 — Serial Collection & Data Preprocessing Pipeline (`collect/`, `preprocess/`, `data/`)
- [x] Fix `logger.py` to write safely under `data/raw/` and pull defaults from `config.py` + `collect/serial_utils.py`.
- [x] Harden serial ingestion (`collect/serial_utils.py`, `logger.py`, `collect/collect_session.py`, `dashboard/`): safe DTR/RTS open, physical bounds filtering, `NaN`/Inf/boot-banner guards, same-second burst guard, and COM port auto-detection (`serial.tools.list_ports`).
- [x] Create and execute `preprocess/clean_datasets.py` (preserving original CSVs immutable):
  - [x] Handle missing header / blank line 1, remove `12,776` exact dupes and collapse `289` same-second burst rows (`49,728 -> 36,663`).
  - [x] Quarantine `389` unlabeled anomaly rows (`normal_quarantined_anomalies.csv`) leaving `34,383` clean training rows (`< 2026-11-01`).
  - [x] Fix `data/processed/pilot_event_annotations.csv` so Event 1 covers full `2026-10-27 23:09:38` -> `23:40:28` recovery window (`504` raw rows across 2 events).
- [x] Record fresh live hardware baseline sessions from `COM19` (`live_baseline_2026-11-10.csv` & `live_steady_2026-11-10.csv`, 59 rows) and keep `collect/mark_events.py` aligned under `data/raw/new_events_log.csv`.
- [x] Build clean unseen evaluation suite (`data/processed/eval_test_suite.csv`: `1,950` rows combining Nov 1 holdout + 6 controlled fault scenarios + unseen live `COM19` telemetry).

## Phase 3 — Time-Aware Feature Engineering (`features/`, `dashboard/feature_utils.py`)
- [x] Unify feature generation into a single shared module (`features/feature_engine.py`, thin wrapper in `dashboard/feature_utils.py`).
- [x] Upgrade engineered features (`12` orthogonal `MODEL_FEATURE_COLS`, dropping drift-prone raw absolute temperature/humidity):
  - [x] Elapsed-time normalized rates (`temp_rate`, `hum_rate`, `rate_joint_norm`) inside `session_id` boundaries (`GAP_THRESHOLD = 10s`).
  - [x] Time-based rolling windows (`10s` dispersion/jitter, `30s` local deviation) instead of fragile row-index windows.
  - [x] Causal rate-gated Cauchy-weighted EWMA baseline (`ewma_halflife_sec = 2400s`, halted on spikes so excursions do not poison baseline).
- [x] Regenerate `data/processed/features_v2/` cleanly (`normal: 34,374`, `pilot: 3,084`, `test: 55`, `eval_suite: 1,947`).

## Phase 4 — Model Upgrades, Persistence & External Benchmarks (`train/`, `evaluate/`, `models/`)
- [x] Upgrade `train/train_models.py`:
  - [x] Fit `StandardScaler` + `IsolationForest` (selected over `RobustScaler` to avoid `0.1`-step quantization IQR collapse) strictly on `34,374` clean normal feature rows.
  - [x] Train & benchmark `Z-Score`, `Adaptive EWMA-Z`, `Isolation Forest (Raw & Persistence)`, `Hybrid (IF + EWMA-Z)`, `One-Class SVM`, and `LOF (Novelty)`.
  - [x] Implement `apply_gated_persistence()` (`3-of-5` flagged windows or sharp instantaneous excursion) + cooldown suppression (`30s`).
  - [x] Save aligned `models/iforest.joblib`, `models/scaler.joblib`, `models/ocsvm.joblib`, `models/thresholds.json`, and `models/evaluation_summary.json`.
- [x] Upgrade `evaluate/evaluate_pilot.py` and create `evaluate/evaluate_suite.py` reporting Precision, Recall, F1, PR-AUC, ROC-AUC, FP/FN, event recall, and per-fault breakdowns.
- [x] Create and run `evaluate/benchmark_external.py` (domain-isolated calibration) on `UCI Occupancy (#357)` and `IoTsec Room-Climate`.

## Phase 5 — Fix All Streamlit Dashboards (`dashboard/`)
- [x] Fix `dashboard/Home.py` & `README.md` run instructions (`streamlit run dashboard/Home.py`).
- [x] Fix `dashboard/pages/1_Analyse.py` (removed ~700-line duplications, added COM port auto-detect, baud forwarding, `serial_error` surfacing, Hybrid + Demo/Upload/Live modes).
- [x] Fix `dashboard/pages/2_Results.py` (added `import time`, fixed sensitivity labels/thresholds, bidirectional drop descriptions, dynamic controls, live queue drain).
- [x] Fix `dashboard/pages/3_Model_Metrics.py` to dynamically read `models/evaluation_summary.json` (internal + external benchmarks).
- [x] Fix `dashboard/user_app.py` (removed 3x nested `main()` & duplicate page configs, fixed `col4` alignment, fixed index slicing, fixed baud/error handling).
- [x] Fix `dashboard/admin_app.py` (fixed `GAP_THRESHOLD` save key, `roc_curve` length mismatch, nested `download_button`, live dataset telemetry & executable retraining triggers).

## Phase 6 — EDA Scripts, Notebooks, Docs & Automated Tests
- [x] Fix `eda/audit_normal_episodes.py` (`MAD` noise floor guard, index alignment, `eda/plots_v2/` output).
- [x] Fix `eda/generate_plots_v2.py` (`break_at_gaps()` off-by-one `NaN` fix, Matplotlib 3.11 `orientation='vertical'`) and regenerate all 10 PNG plots in `eda/plots_v2/`.
- [x] Repair, validate, and execute all 4 Jupyter notebooks cleanly (`eda/notebooks/01_eda.ipynb`, `preprocess/notebooks/02_data_preprocessing.ipynb`, `features/notebooks/03_feature_engineering.ipynb`, `notebooks/iot_anomaly_detection.ipynb`).
- [x] Add automated `pytest` suite (`tests/unit/` + `tests/integration/` covering serial parsing, preprocessing, features, model contracts, end-to-end eval bounds, and all 6 Streamlit apps via `AppTest`).
- [x] Update `README.md`, `PROJECT_PLAN.md`, `docs/hardware.md`, and `docs/serial_protocol.md`.

## Phase 7 — Final End-to-End Verification
- [x] Run full `pytest` suite (`42 passed, 0 failed`).
- [x] Run clean end-to-end pipeline verification (`preprocess/clean_datasets.py` -> `features/build_features_v2.py` -> `train/train_models.py` -> `evaluate/evaluate_pilot.py` -> `evaluate/evaluate_suite.py` -> `eda/generate_plots_v2.py`).
- [x] Verify all Streamlit apps (`Home.py`, `1_Analyse.py`, `2_Results.py`, `3_Model_Metrics.py`, `user_app.py`, `admin_app.py`) render cleanly with zero exceptions.
