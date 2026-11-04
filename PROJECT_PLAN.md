# PROJECT_PLAN.md
## AI-Based IoT Sensor Anomaly Detection System

---

## 1. Project Overview

**Objective:** Build an end-to-end anomaly detection system for IoT sensor data (temperature & humidity from DHT11 on ESP32) with real-time monitoring dashboard.

**Scope:** 
- Hardware: ESP32 + DHT11 sensor (GPIO 4)
- Communication: Serial (USB) at 115200 baud
- Sampling interval: 2000 milliseconds
- ML: Unsupervised anomaly detection (Isolation Forest primary)
- Deployment: Windows PC — Python application handles data processing, ML inference, dashboard
- ESP32 responsibility: Sensor acquisition only

**Current State:** Data collection pipeline working. Three datasets collected. No ML, no dashboard, no ESP32 code in repo.

---

## 2. Existing Project Inventory

| File | Type | Size | Records | Description |
|------|------|------|---------|-------------|
| `logger.py` | Python script | 3.4 KB | N/A | Serial logger, writes to `data/normal_data.csv` |
| `data/normal_data.csv` | CSV dataset | 1.49 MB | 49,728 | Main normal data (Oct 29, 2026, ~27 hours) |
| `data/pilot_data.csv` | CSV dataset | 92.6 KB | 3,087 | Pilot data (Oct 27-28, 2026, contains anomalies) |
| `data/test.csv` | CSV dataset | 1.7 KB | 56 | Labeled test with injected anomaly (Oct 27, 2026) |
| `data/test_labels.csv` | CSV labels | 63 B | 1 | Ground truth for test.csv anomaly window |

**Missing from repository:**
- ESP32 firmware (.ino/.cpp)
- requirements.txt
- Any ML/preprocessing/dashboard code
- Documentation

---

## 3. Hardware Architecture

### ESP32 + DHT11 Configuration (Confirmed)
| Parameter | Value | Notes |
|-----------|-------|-------|
| MCU | ESP32 | Via USB serial |
| Sensor | DHT11 | Temperature + Humidity |
| Data Pin | GPIO 4 | Confirmed |
| Serial Port | COM19 (configurable) | Windows Device Manager |
| Baud Rate | 115200 | Must match logger.py |
| Data Format | `temperature,humidity\n` | CSV, no header from ESP32 |
| Sampling Interval | 2000 ms | Fixed in firmware |
| Deployment Target | Windows PC | Python handles ML + dashboard |

### Serial Communication Protocol
```
ESP32 → PC: "26.2,59.4\n" (temperature,humidity)
```
- Logger skips lines starting with "temperature" or "humidity" (header handling)
- Logger validates: exactly 2 comma-separated floats
- Logger adds ISO timestamp on PC side: `2026-10-29T16:39:00`

### Known Constraints (Firmware Not in Repo)
- ESP32 firmware sketch is **not in this repository** — do not invent configuration
- PC-side timestamp adds clock drift risk; ESP32 has no RTC/NTP in current setup
- No sequence numbers — cannot detect dropped packets
- DHT11 accuracy: ±2°C, ±5% RH — expect sensor noise
- No data validation on ESP32 side — NaN/invalid readings possible

---

## 4. Software Architecture

### Modular Pipeline Components

```
┌─────────────┐     ┌──────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   ESP32     │────▶│  Serial/USB  │────▶│  Python Logger   │────▶│   CSV Files     │
│  Firmware   │     │  (115200)    │     │  (logger.py)     │     │  (data/)        │
└─────────────┘     └──────────────┘     └──────────────────┘     └─────────────────┘
                                                                         │
                                                                         ▼
┌─────────────┐     ┌──────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Dashboard  │◀───│  Live Inference│◀───│  Trained Model   │◀───│  Model Training │
│  (Streamlit)│     │  (detector.py) │     │  (models/)     │     │  (train.py)     │
└─────────────┘     └──────────────┘     └──────────────────┘     └─────────────────┘
                           ▲                                        ▲
                           │                                        │
                    ┌──────┴──────┐                         ┌────────┴────────┐
                    │ Preprocess  │                         │   Evaluate      │
                    │ (preprocess)│                         │  (evaluate.py)  │
                    └─────────────┘                         └─────────────────┘
```

### Component Responsibilities

| Module | Responsibility | Input | Output |
|--------|----------------|-------|--------|
| `firmware/` | ESP32 sketch: read DHT11, send CSV via Serial | - | Serial stream |
| `collect/` | `logger.py` - robust serial logging with rotation | Serial | Raw CSV |
| `data/` | Dataset storage (raw, cleaned, splits) | - | Versioned CSVs |
| `preprocess/` | Validation, cleaning, resampling, feature engineering | Raw CSV | Clean Parquet/CSV |
| `eda/` | Exploratory analysis notebooks/scripts | Clean data | Reports, plots |
| `features/` | Rolling stats, diffs, time features, scaling | Clean data | Feature matrix |
| `train/` | Model training, hyperparameter tuning, MLflow | Features | Trained model |
| `evaluate/` | Metrics on labeled test set, threshold tuning | Model + test | Reports, thresholds |
| `models/` | Serialized models, scalers, metadata | - | `.pkl`/`.joblib` |
| `detect/` | Real-time inference on serial stream | Serial + model | Anomaly scores/alerts |
| `dashboard/` | Streamlit: live charts, history, alerts | Detection + history | Web UI |
| `tests/` | Unit/integration tests for each module | - | CI reports |
| `docs/` | Architecture, API, hardware setup | - | Markdown |

---

## 5. Dataset Inventory

### `data/normal_data.csv` — Candidate Normal Training Set
- **Size:** 1.49 MB, 49,729 lines (49,728 records + header)
- **Columns:** `timestamp`, `temperature`, `humidity`
- **Range:** 2026-10-29T16:39:00 → 2026-10-30T20:36:32 (~27.9 hours)
- **Sampling:** ~2 sec nominal, some gaps (3-4 sec occasionally)
- **Temperature:** 24.2–26.2°C (stable, slowly rising)
- **Humidity:** 46.8–60.7% (stable, slowly falling)
- **Status:** **Normality and data quality MUST be verified before training**
- **Use case:** Candidate training set (normal only) — pending verification

### `data/pilot_data.csv` — Early Collection (Mixed, Preserve)
- **Size:** 92.6 KB, 3,088 lines (3,087 records + header)
- **Columns:** `timestamp`, `temperature`, `humidity`
- **Range:** 2026-10-27T22:02:14 → 2026-10-28T00:19:08 (~2.3 hours)
- **Contains:** Two reported anomaly events requiring verification:
  1. 2026-10-27T22:03:29–22:03:47: Temp 32.5→34.2°C, Hum 75→82%
  2. 2026-10-27T23:09:38–23:10:30: Temp 26.6→31.2°C, Hum 85→45%
- **Status:** **Must be preserved unchanged** — experimental readings with reported labeled anomalies
- **Use case:** Validation / anomaly characterization — NOT for training

### `data/test.csv` — Labeled Test Set
- **Size:** 1.7 KB, 57 lines (56 records + header)
- **Columns:** `timestamp`, `temperature`, `humidity`
- **Range:** 2026-10-27T22:02:14 → 2026-10-27T22:04:05 (~2 min)
- **Anomaly window:** Rows 39–48 (2026-10-27T22:03:29–22:03:47)
- **Status:** **Verify label alignment** — single label record may be event-level, not row-level
- **Use case:** Hold-out test set — NEVER use for training

### `data/test_labels.csv` — Ground Truth
- **Size:** 63 B, 2 lines (1 label + header)
- **Columns:** `start`, `end`, `label`
- **Content:** `2026-10-27T22:03:29,2026-10-27T22:03:47,anomaly`
- **Status:** **Event-level label** — does NOT align with all 56 observations
- **Use case:** Evaluation metric computation

### Dataset Relationships
```
normal_data.csv (49,728 rows)  ──▶ CANDIDATE TRAINING (verify normality first)
pilot_data.csv (3,087 rows)    ──▶ VALIDATION (preserve, verify anomaly boundaries)
test.csv (56 rows)             ──▶ TEST (hold-out, never train)
test_labels.csv                ──▶ EVENT-LEVEL GROUND TRUTH for test.csv
```

**Critical Rules:**
1. **Never train using test.csv or test_labels.csv**
2. **Preserve every original CSV unchanged** — no modifications
3. **Do not automatically remove all repeated timestamps** — investigate first
4. **Do not interpolate across major recording gaps** — create artificial normal observations
5. **Verify the 34,953 vs 49,728 record discrepancy** — investigate actual file contents

---

## 6. Proposed ML Methodology

### Algorithm Selection & Trade-offs

| Algorithm | Type | Pros | Cons | Recommendation |
|-----------|------|------|------|----------------|
| **Z-Score / Modified Z-Score** | Statistical | Simple, interpretable, no training | Assumes Gaussian, fails on multivariate | **Baseline only** |
| **Isolation Forest** | Tree-based ensemble | Handles multivariate, fast, robust to outliers, no density estimation | Random seed variance, needs contamination estimate | **PRIMARY** |
| **One-Class SVM** | Kernel-based | Strong theoretical foundation | Slow O(n²), sensitive to kernel/params, poor on high-dim | Secondary |
| **Local Outlier Factor (LOF)** | Density-based | Good for local anomalies | O(n²) memory, slow, sensitive to k | Tertiary |

### Recommended Strategy: Isolation Forest

**Why Isolation Forest:**
1. **Unsupervised** — learns from normal data only (matches our normal_data.csv)
2. **Multivariate** — captures temp/humidity joint distribution
3. **Fast inference** — suitable for real-time on edge
4. **Robust** — isolates anomalies via random splits, not distance
5. **Scikit-learn native** — no extra dependencies

**Training Protocol:**
```python
# Train ONLY on normal_data.csv (49,728 samples)
# contamination=0.01 (1% expected anomalies in deployment)
# n_estimators=200, max_samples='auto', random_state=42
```

**Evaluation Protocol:**
1. Train on `normal_data.csv`
2. Score `test.csv` (56 samples with known anomaly window)
3. Compute: Precision, Recall, F1, ROC-AUC, PR-AUC
4. Tune decision threshold using `test_labels.csv`
5. Validate on `pilot_data.csv` (known anomalies at different magnitudes)

**Feature Engineering (v1):**
- Raw: `temperature`, `humidity`
- Rolling (window=10 → ~20 sec): mean, std, min, max for each
- Diffs: `temp_diff`, `hum_diff` (1-step)
- Time: `hour`, `minute`, `second` (cyclical encoding)
- Total: ~12 features

**Future Enhancements:**
- Seasonal decomposition (STL) for trend/residual
- Spectral features (FFT) if periodic anomalies expected
- Multivariate Gaussian Mixture for comparison

---

## 7. Complete Development Phases

| Phase | Tasks | Deliverable | Est. Effort |
|-------|-------|-------------|-------------|
| **0. Setup** | Repo structure, requirements.txt, gitignore, venv | Clean repo | 0.5 day |
| **1. Hardware Doc** | Extract ESP32 code, document pins, schema | `firmware/README.md` | 0.5 day |
| **2. Data Pipeline** | Robust logger (rotation, validation, timestamps) | `collect/logger_v2.py` | 1 day |
| **3. Preprocessing** | Validation, cleaning, resampling, Parquet export | `preprocess/clean.py` | 1 day |
| **4. EDA** | Notebooks: distributions, correlations, anomaly viz | `eda/report.html` | 1 day |
| **5. Features** | Rolling stats, diffs, time encodings, scaler | `features/build.py` | 1 day |
| **6. Training** | IsolationForest, MLflow tracking, model registry | `models/iforest_v1.pkl` | 1 day |
| **7. Evaluation** | Metrics on test.csv, threshold tuning, reports | `evaluate/report.json` | 0.5 day |
| **8. Live Detection** | Serial reader + model inference + alert logic | `detect/detector.py` | 1 day |
| **9. Dashboard** | Streamlit: live charts, history, alerts, config | `dashboard/app.py` | 1.5 days |
| **10. Testing** | Unit tests, integration, CI pipeline | `tests/`, GitHub Actions | 1 day |
| **11. Docs** | Architecture, API, hardware setup, runbooks | `docs/` | 0.5 day |

**Total:** ~10 days (part-time compatible)

---

## 8. Proposed Folder Structure

```
iot-anomaly-detection/
├── firmware/                 # ESP32 Arduino/PlatformIO project
│   ├── src/
│   │   └── main.cpp         # DHT11 reading + serial output
│   ├── platformio.ini       # Build config
│   └── README.md            # Pinout, wiring, flash instructions
│
├── collect/                  # Data collection
│   ├── logger.py            # Current logger (v1)
│   ├── logger_v2.py         # Robust: rotation, validation, MQTT option
│   └── requirements.txt     # pyserial, etc.
│
├── data/                     # Datasets (versioned, immutable)
│   ├── raw/                 # Original CSVs (current files)
│   │   ├── normal_data.csv
│   │   ├── pilot_data.csv
│   │   ├── test.csv
│   │   └── test_labels.csv
│   ├── processed/           # Cleaned, resampled Parquet
│   └── splits/              # Train/val/test splits (indices only)
│
├── preprocess/               # Data cleaning & validation
│   ├── validate.py          # Schema, range, gap checks
│   ├── clean.py             # Interpolation, outlier removal
│   ├── resample.py          # Fixed 2s grid
│   └── pipeline.py          # Composable preprocessing
│
├── eda/                      # Exploratory Data Analysis
│   ├── notebooks/
│   │   ├── 01_distributions.ipynb
│   │   ├── 02_correlations.ipynb
│   │   └── 03_anomaly_characterization.ipynb
│   └── reports/             # Exported HTML/PDF
│
├── features/                 # Feature engineering
│   ├── build.py             # Rolling, diffs, time encodings
│   ├── scaler.pkl           # Fitted StandardScaler/RobustScaler
│   └── feature_list.json    # Column names + metadata
│
├── train/                    # Model training
│   ├── train.py             # IsolationForest + MLflow
│   ├── tune.py              # Optuna hyperparameter search
│   ├── config.yaml          # Training hyperparameters
│   └── mlflow/              # Local tracking (optional)
│
├── evaluate/                 # Model evaluation
│   ├── evaluate.py          # Metrics on test.csv
│   ├── threshold_tuning.py  # Optimize decision threshold
│   ├── metrics.json         # Precision, recall, F1, AUC
│   └── plots/               # ROC, PR, confusion matrix
│
├── models/                   # Serialized artifacts
│   ├── iforest_v1.pkl       # Trained IsolationForest
│   ├── scaler.pkl           # Feature scaler
│   ├── metadata.json        # Training info, metrics, versions
│   └── registry/            # Model versioning
│
├── detect/                   # Real-time inference
│   ├── detector.py          # Serial → features → score → alert
│   ├── alert.py             # Alert logic (cooldown, severity)
│   └── config.yaml          # Thresholds, window sizes
│
├── dashboard/                # Monitoring UI
│   ├── app.py               # Streamlit app
│   ├── components/          # Charts, tables, alerts
│   ├── utils.py             # Data loading, formatting
│   └── requirements.txt     # streamlit, plotly, pandas
│
├── tests/                    # Test suite
│   ├── unit/
│   │   ├── test_preprocess.py
│   │   ├── test_features.py
│   │   └── test_model.py
│   ├── integration/
│   │   └── test_pipeline.py
│   └── fixtures/            # Small test datasets
│
├── docs/                     # Documentation
│   ├── architecture.md
│   ├── hardware_setup.md
│   ├── data_pipeline.md
│   ├── model_card.md
│   └── runbooks/
│       ├── collect_data.md
│       ├── train_model.md
│       └── run_dashboard.md
│
├── .github/
│   └── workflows/
│       ├── ci.yml           # Lint, test, type-check
│       └── train.yml        # Scheduled retraining
│
├── requirements.txt          # Root dependencies
├── requirements-dev.txt      # Dev tools (pytest, black, mypy)
├── pyproject.toml           # Build config, tool settings
├── .gitignore
├── README.md
└── PROJECT_PLAN.md          # This file
```

---

## 9. Important Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **No ESP32 code in repo** | High | High | Request firmware from user; document pinout immediately |
| **PC-side timestamp drift** | Medium | Medium | Add sequence numbers; consider ESP32 RTC or NTP |
| **DHT11 accuracy (±2°C, ±5% RH)** | High | Medium | Characterize sensor noise in pilot_data; use robust scaler |
| **Only 1 labeled anomaly type** | High | High | Test on pilot_data anomalies; document detection limits |
| **Concept drift (seasonal)** | Medium | High | Schedule monthly retraining; monitor score distributions |
| **Serial port conflicts** | Medium | Low | Logger v2: auto-detect port, retry logic, exclusive lock |
| **Isolation Forest randomness** | Low | Medium | Fix `random_state`; ensemble multiple seeds |
| **Class imbalance (contamination)** | Medium | Medium | Tune contamination via validation; use PR-AUC not ROC-AUC |
| **No ground truth for pilot anomalies** | Medium | Medium | Manually label pilot_data anomaly windows for validation |

---

## 10. Testing & Evaluation Strategy

### Unit Tests (pytest)
- `preprocess.validate`: schema, dtypes, range checks
- `preprocess.clean`: gap filling, outlier removal idempotency
- `features.build`: column count, no NaN, scaler persistence
- `train.train`: model saves, metadata includes metrics
- `detect.detector`: inference shape, alert logic

### Integration Tests
- Full pipeline: raw CSV → features → model → scores
- Live detection sim: replay test.csv through detector
- Dashboard: smoke test with sample data

### Evaluation Metrics (on test.csv + test_labels.csv)
| Metric | Target | Notes |
|--------|--------|-------|
| **Precision** | > 0.85 | Few false alarms |
| **Recall** | > 0.90 | Catch real anomalies |
| **F1-Score** | > 0.87 | Balanced |
| **PR-AUC** | > 0.90 | Better than ROC-AUC for imbalance |
| **Latency** | < 50 ms | Per inference (features + model) |
| **Throughput** | > 20 Hz | Well above 0.5 Hz data rate |

### Threshold Tuning
- Optimize F1 on `test.csv` using `test_labels.csv`
- Validate threshold on `pilot_data.csv` anomaly windows
- Set production threshold = max(F1_threshold, 99th percentile normal scores)

### Monitoring in Production
- Track anomaly score distribution (drift detection)
- Alert rate (should be ~contamination%)
- Feature distribution shifts (KS test vs training)

---

## Summary: Current State & Next Steps

### What Already Exists ✅
- Working serial logger (`logger.py`)
- 3 datasets collected (normal, pilot, labeled test)
- Clear anomaly examples in pilot/test data

### What Is Incomplete ⚠️
- No ESP32 firmware in repository
- No requirements.txt or environment management
- No preprocessing, features, training, evaluation code
- No model, no live detection, no dashboard
- No tests, no documentation

### What Needs Improvement 🔧
- Logger robustness (rotation, validation, auto-port-detect)
- Timestamp strategy (ESP32-side preferred)
- Data versioning (move raw data to `data/raw/`)

### Recommended Development Order 📋
1. **Setup** — Repo structure, requirements, venv, gitignore
2. **Hardware Doc** — Get ESP32 code, document pins/wiring
3. **Logger v2** — Robust collection with rotation & validation
4. **Preprocessing** — Clean, validate, resample to fixed grid
5. **EDA** — Understand distributions, characterize anomalies
6. **Features** — Rolling stats, diffs, time encodings
7. **Train** — IsolationForest on normal_data.csv only
8. **Evaluate** — Metrics on test.csv, threshold tuning
9. **Detect** — Real-time inference on serial stream
10. **Dashboard** — Streamlit monitoring UI
11. **Tests & Docs** — CI, runbooks, model card

### Problems Needing Your Attention ❗
1. **ESP32 firmware not in repo** — Firmware sketch not provided; document pinout/wiring from confirmed config (GPIO 4)
2. **Dataset verification required** — normal_data.csv normality must be verified before training
3. **Label alignment verification** — test_labels.csv is event-level; verify alignment with test.csv rows
4. **34,953 vs 49,728 discrepancy** — Investigate and document the actual record counts
5. **Power supply stability** — DHT11 sensitive to voltage drops; confirm 3.3V vs 5V wiring
6. **Labeling strategy** — Only one labeled anomaly type; consider collecting more fault types

---

**Phase 0 Approval:** Ready to begin setup. Confirmed items:
- Hardware: ESP32 + DHT11 on GPIO 4, 115200 baud, 2000ms sampling
- Deployment: Windows PC (Python handles ML + dashboard)
- Dataset rules: Preserve originals, verify normality, never train on test set