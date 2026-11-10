# AI-Based IoT Sensor Anomaly Detection

Dungu Avinash Reddy | Roll RK3P25KZA09 | Reg. 12509090

## What It Does

Real-time and offline anomaly detection for **ESP32 + DHT11** temperature & humidity telemetry streamed over USB serial (`COM19` @ `115200` baud, 0.5 Hz cadence).  
The unified pipeline separates raw immutable captures (`data/raw/`), runs deduplication & anomaly quarantine (`preprocess/clean_datasets.py`), extracts **12 orthogonal time/session-aware features** with a **causal rate-gated Cauchy EWMA baseline** (`features/feature_engine.py`), and scores data using an ensemble of:

1. **Hybrid Ensemble (`Isolation Forest + Gated Persistence | Adaptive EWMA-Z`)** — Production detector combining short-term multivariate dynamics with drift-resilient steady plateau sensitivity (`offset_fault`, sustained heat/cooling).
2. **Isolation Forest + Gated Persistence** — Trained strictly on cleaned normal readings (`34,374` feature rows across `9` continuous sessions) with `StandardScaler` and `3-of-5` / sharp-jump gating to eliminate single-row jitter and post-event false tails.
3. **Adaptive Gated EWMA-Z** — Drift-aware baseline residual score (`halflife = 2400s`, halted automatically during sudden spikes so sustained excursions never poison the room baseline).
4. **Baselines Compared** — Fixed `Z-Score (3.0 sigma)`, `One-Class SVM`, and `Local Outlier Factor (LOF)`.

## Folder Map

```text
.
├── alerts/                    # Non-blocking building-wide alert notifier (ntfy.sh, webhook, SMTP) & Streamlit panel
├── collect/                   # USB serial reader helpers, session logger, interactive event marker
├── dashboard/                 # Streamlit apps (Home.py + 3 pages, user_app.py, admin_app.py)
├── data/
│   ├── raw/                   # Immutable source CSVs (normal_data, pilot_data, test, test_labels) + live_2026-11-10 captures
│   ├── processed/             # Cleaned datasets, quarantined rows, verified pilot annotations, eval_test_suite.csv, features_v2/
│   └── benchmarks/            # Cached external validation benchmarks (UCI #357, IoTsec Room-Climate)
├── docs/                      # Verified hardware wiring & serial protocol documentation
├── eda/                       # Audit scripts, regenerated PNG plots (plots_v2/), and 01_eda.ipynb
├── evaluate/                  # evaluate_pilot.py, evaluate_suite.py, benchmark_external.py
├── features/                  # Shared feature_engine.py, build_features_v2.py, 03_feature_engineering.ipynb
├── firmware/esp32_dht11/      # Verified Arduino sketch for ESP32 + DHT11 (GPIO 4, 115200 baud)
├── models/                    # Trained artifacts (iforest.joblib, scaler.joblib, ocsvm.joblib, thresholds.json, evaluation_summary.json)
├── notebooks/                 # End-to-end master notebook (iot_anomaly_detection.ipynb)
├── preprocess/                # Reproducible cleaning, quarantine, holdout/eval suite builder, 02_data_preprocessing.ipynb
├── tests/                     # Automated pytest unit & integration tests (incl. Streamlit AppTest smoke suite)
├── train/                     # Model training, threshold calibration & full evaluation exporter
├── config.yaml / config.py    # Single source of truth for serial, features, thresholds, alerts, and dashboard settings
├── .env.example               # Template for optional alert secrets (copy to local gitignored .env)
├── logger.py                  # Continuous ESP32 CSV logger + optional headless `--alert` monitor
├── PROJECT_PLAN.md            # Project architecture & milestone record
└── tasks.md                   # Complete project upgrade & verification checklist
```

## Setup and Run (Windows PowerShell)

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 1. Clean raw data, quarantine unlabeled episodes, build unseen eval suite
python preprocess/clean_datasets.py

# 2. Build unified 12-feature session/time-aware feature matrices
python features/build_features_v2.py

# 3. Train models, calibrate percentiles, save models/evaluation_summary.json
python train/train_models.py

# 4. Run internal & isolated external domain benchmarks
python evaluate/evaluate_pilot.py
python evaluate/evaluate_suite.py
python evaluate/benchmark_external.py

# 5. Run automated unit & integration tests (incl. dashboard AppTests)
python -m pytest -v

# 6. Launch Streamlit dashboards
python -m streamlit run dashboard/Home.py --server.port 8501 --server.address localhost
# Or standalone live client / admin dashboards:
python -m streamlit run dashboard/user_app.py --server.port 8502 --server.address localhost
python -m streamlit run dashboard/admin_app.py --server.port 8503 --server.address localhost
```

### Live ESP32 Hardware Collection (`COM19` @ `115200` baud)

```powershell
# Continuous logger to data/raw/live_session_log.csv (auto-detects COM port)
python logger.py --port auto

# Continuous logger WITH building-wide live employee alerts via ntfy.sh
python logger.py --port auto --alert --ntfy-topic your-unique-building-topic --zone "Building A - Floor 1"

# Timed capture + interactive event labeling
python collect/collect_session.py auto data/raw/new_session.csv 120
python collect/mark_events.py
```

### Building-Wide Employee Alerts (`alerts/notifier.py`)

When running live monitoring (`dashboard/user_app.py`, live mode in `dashboard/pages/1_Analyse.py` / `2_Results.py`, or `logger.py --alert`), detected anomalies broadcast automatically without blocking the 2s sampling loop:
- **`ntfy.sh` Push (Default / Zero Keys):** Set `NTFY_TOPIC` in `.env` (see `.env.example`) or enter a topic in the **Employee Alerts** sidebar panel; anyone opening `https://ntfy.sh/<topic>` or subscribing in the `ntfy` mobile app receives alerts immediately.
- **Slack / Discord / MS Teams & Email (Optional via `.env`):** Configure `ALERT_WEBHOOK_URL` and/or `ALERT_EMAIL_*` variables cleanly in `.env` (gitignored).
- **Anti-Spam & Hysteresis:** Fires on episode transition (`Medium` / `High` by default, escalating sustained `Low` events after `15s`), enforces a `180s` cooldown, logs every incident to `logs/alert_history.csv`, sends an **"All Clear"** follow-up after `30s` recovery, and never triggers during offline Demo/CSV replay. Optional hard **AC / Building Comfort Guardrails** (`comfort_guardrails` in `config.yaml`) catch slow HVAC drift too.

## Methodology & Fixes Over v1 Baseline

- **Deduplication & Quarantine (`preprocess/clean_datasets.py`)**: Removed `12,776` exact duplicates + `289` same-second USB buffer bursts (`49,728 -> 36,663`), quarantined `389` unlabeled humidity/breath spikes (`normal_quarantined_anomalies.csv`), and split chronologically (`< 2026-11-01`: `34,383` training rows; `>= 2026-11-01`: `1,891` unseen holdout + `59` live `COM19` baseline rows collected `2026-11-10`).
- **Verified Pilot Event Annotations**: Corrected Event 1 truncation (`23:09:38 -> 23:10:30`) to the full physical recovery boundary (`23:09:38 -> 23:40:28`, `504` raw positive rows across 2 events).
- **Drift-Resilient Feature Engine (`features/feature_engine.py`)**: Removed raw absolute temperature/humidity levels from model inputs (`MODEL_FEATURE_COLS`, `12` features), replaced fixed row-count rolling windows with time-based windows (`10s`, `30s`) bounded inside `session_id` gaps (`> 10s`), added causal rate-gated Cauchy EWMA residuals (`halflife=2400s`), and replaced `RobustScaler` (which exploded on `0.1` quantized sensor steps) with `StandardScaler`.
- **Gated Persistence (`apply_gated_persistence`)**: Requires `3-of-5` flagged rows in a session or an immediate sharp step excursion (`|dT/dt| >= 0.4 C/s`, `|dH/dt| >= 1.5 %/s`, `|dT_ewma| >= 2.5 C`, `|dH_ewma| >= 9.0 %`), preserving rapid spikes while suppressing transient single-row jitter.

## Verified Results (`models/evaluation_summary.json`)

| Dataset / Benchmark |Rows (Positives) | Detector | Precision | Recall | F1 | PR-AUC | ROC-AUC | FP | Events Caught |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| **Test (Legacy)** | 55 (10) | **Hybrid (IF + EWMA-Z)** | 0.909 | **1.000** | **0.952** | 0.991 | 0.998 | 1 | **1 / 1** |
| **Test (Legacy)** | 55 (10) | Adaptive EWMA-Z | **1.000** | 0.700 | 0.824 | **1.000** | **1.000** | **0** | 1 / 1 |
| **Pilot (Verified)** | 3,084 (503) | **Hybrid (IF + EWMA-Z)** | **1.000** | **0.873** | **0.932** | 0.989 | 0.998 | **0** | **2 / 2** |
| **Pilot (Verified)** | 3,084 (503) | Adaptive EWMA-Z | **1.000** | 0.837 | 0.911 | **0.999** | **1.000** | **0** | 2 / 2 |
| **Pilot (Verified)** | 3,084 (503) | Z-Score Baseline | **1.000** | 0.857 | 0.923 | 0.999 | 1.000 | **0** | 2 / 2 |
| **Eval Suite (Unseen + Live)** | 1,947 (143) | **Hybrid (IF + EWMA-Z)** | **0.972** | **0.965** | **0.968** | **0.981** | **0.993** | 4 | **6 / 6** |
| **Eval Suite (Unseen + Live)** | 1,947 (143) | Adaptive EWMA-Z | **1.000** | 0.713 | 0.833 | 0.951 | 0.985 | **0** | 6 / 6 |
| **Eval Suite (Unseen + Live)** | 1,947 (143) | Isolation Forest | 0.968 | 0.853 | 0.907 | 0.936 | 0.988 | 4 | 6 / 6 |
| **Eval Suite (Unseen + Live)** | 1,947 (143) | Z-Score Baseline | 0.648 | 0.734 | 0.689 | 0.807 | 0.959 | 57 | 6 / 6 |

- **Live Hardware Cross-Day Generalization (`COM19`, `2026-11-10`, `~28.1–29.6°C / 53.7–59.8% RH`, `57` feature rows)**:  
  - `Hybrid (IF + EWMA-Z)`: **0 / 57 false alarms** (`IF: 0/57`, `EWMA-Z: 0/57`)  
  - Fixed `Z-Score Baseline`: **57 / 57 false alarms (100% false-positive rate)** due to warm drier room shift.
- **Per-Fault Eval Suite Recall (Hybrid)**: `breath_spike 94.4%`, `heat_source_burst 95.8%`, `cold_draft_drop 95.0%`, `offset_fault 100.0%`, `slow_drift_fault 95.6%`, `chatter_noise_fault 100.0%`.
- **Isolated External Benchmarks (`evaluate/benchmark_external.py`, domain-isolated calibration)**:
  - **UCI Occupancy Detection (#357)** (`3,757` train / `1,999` test / `400` anomalies @ 60s cadence): `Hybrid` P=`0.948`, PR-AUC=`0.939`, ROC-AUC=`0.987`; `Adaptive EWMA-Z` P=`1.000`, PR-AUC=`0.966`, ROC-AUC=`0.983`.
  - **IoTsec Room-Climate-Datasets (Location A Node 1)** (`2,044` train / `2,457` test / `490` anomalies): `Hybrid` R=`0.994`, PR-AUC=`0.997`, ROC-AUC=`0.998`; `Z-Score` F1=`0.978`.

## Hardware Verification & Protocol Notes

- Verified live ESP32 + DHT11 stream on Windows **`COM19`** at **`115200` baud** (`temperature,humidity\n`, `0.5 Hz`).
- Observed live DHT11 output at **`0.1°C` / `0.1% RH` formatted precision** (e.g. `28.10,59.80` -> `29.60,53.70`).
- Serial connections in `collect/serial_utils.py` explicitly set `ser.dtr = False` and `ser.rts = False` prior to `open()` to prevent ESP32 USB-UART bootloader resets mid-stream.
- All Streamlit apps (`Home.py`, `user_app.py`, `admin_app.py`) support Demo replay, CSV upload, and live ESP32 serial monitoring.
