# Datasheet: IoT Sensor Anomaly Detection Datasets

## Dataset Overview

| Dataset | Source | Collection Method | Sampling Rate | Duration | Provenance |
|---------|--------|-------------------|---------------|----------|------------|
| normal_data.csv | ESP32 + DHT11 (GPIO 4) | Continuous logging | 2s | ~27.6h (49,727 rows) | Recorded |
| test_data_with_labels.csv | ESP32 + DHT11 (GPIO 4) | Event recording | 2s | ~1.4min (56 rows) | Recorded |
| pilot_data.csv | ESP32 + DHT11 (GPIO 4) | Session logging | 2s | ~1.7h (3,087 rows) | Recorded |
| eval_test_suite.csv | Synthetic injection | Programmatic | 2s | ~1.1h (1,950 rows) | Synthetic (seed 42) |
| UCI Occupancy #357 | Public repository | Original study | 60s | ~33h | Recorded (occupancy) |
| IoTsec Room-Climate | Public repository | Original study | Sub-minute | Variable | Recorded (ESORICS 2017) |

---

## normal_data.csv (Training Baseline)

- **Rows**: 49,727 (34,374 clean after quarantine)
- **Columns**: timestamp, temperature, humidity
- **Collection**: Continuous logging in student's room over multiple sessions
- **Quarantine**: 389 rows removed as suspected anomalies (spikes, sensor faults)
- **Sensor**: DHT11 on ESP32 GPIO 4, 115,200 baud
- **Resolution**: Data shows 0.1°C resolution (DHT11 spec is 1°C — **UNKNOWN** if DHT22 or interpolation)
- **Environment**: Single room, single sensor, single season
- **Known Issues**: 
  - "Blowing episodes" in normal data (student blowing on sensor) — production method UNKNOWN
  - Temperature/humidity identical for ≥30 consecutive readings flagged as sensor fault

---

## test_data_with_labels.csv (Test Set)

- **Rows**: 56 (46 normal + 10 anomaly)
- **Event**: 1 anomaly event (10 rows at 22:03:29–22:03:47)
- **Labels**: Student-annotated (blowing on sensor) — production method UNKNOWN
- **Overlap**: Shares 35 rows (22:02:14–22:03:23) with pilot_data.csv
- **Gap**: Pilot has no rows for 22:03:25–22:04:05 where test holds the event

---

## pilot_data.csv (Pilot Set)

- **Rows**: 3,087
- **Original Labels**: 2 events, 46 anomaly rows (23:09:38–23:10:30 and 00:34:20–00:34:56)
- **Revised Labels**: 2 events, 504 anomaly rows (event 1 expanded from 27 to 466 rows)
- **Expansion**: Commit 4f8ca08 — labels expanded **after** seeing detector results
- **Production Method**: UNKNOWN — student reports "blowing episodes" but exact protocol not documented
- **Status**: **Development data only** — labels informed threshold selection

---

## eval_test_suite.csv (Synthetic Evaluation Suite)

- **Rows**: 1,950 (1,807 normal + 143 anomaly)
- **Anomaly Types** (6 fault categories, seed 42):
  1. Spike (sudden excursion)
  2. Offset (step change)
  3. Drift (gradual change)
  4. Chatter (rapid oscillation)
  5. Stuck sensor (constant value)
  6. Dropout (missing readings)
- **Injection**: Synthetic faults injected into held-out clean normal data
- **Provenance**: **Synthetic** — not recorded physical events
- **Role**: Held-out — no tuning allowed

---

## UCI Occupancy Detection #357 (Cross-Domain Benchmark)

- **Source**: UCI ML Repository #357 (Candanedo & Feldheim, 2016)
- **Original**: 60s cadence, temperature, humidity, light, CO2, occupancy label
- **Usage**: Longest unoccupied segment used as clean baseline; 4 faults injected (seed 357)
- **Provenance**: **Synthetic injections on recorded occupancy data**
- **Role**: Held-out — cross-domain validation only
- **Note**: Different sensor, different cadence, different environment

---

## IoTsec Room-Climate (Cross-Domain Benchmark)

- **Source**: IoTsec Room-Climate-Datasets (ESORICS 2017)
- **Usage**: Location A, Node 1; training on measurement 01, testing on measurement 06 with injected faults (seed 2017)
- **Provenance**: **Synthetic injections on recorded multi-node data**
- **Role**: Held-out — cross-domain validation only
- **Key Result**: Hybrid produces 470 false positives (Precision = 0.509) due to baseline distribution shift

---

## Data Collection Questions (UNKNOWN — Ask Student)

1. **How were the test event, the two pilot events, and the blowing episodes in normal data produced?**
   - Exact protocol for generating anomalies not documented
   - Was it blowing on sensor? Hot/cold object? Humidifier?
   - Duration and intensity control?

2. **Is the sensor a DHT11 or DHT22 (read the label)?**
   - Data shows 0.1°C resolution
   - DHT11 spec: 1°C resolution
   - DHT22 spec: 0.1°C resolution
   - **UNKNOWN** — need to check physical label

3. **What is due, and when?**
   - Project deadline unknown
   - Report, slides, demo dates unknown

---

## Preprocessing Pipeline

1. **Deduplication**: Remove exact duplicate timestamps
2. **Quarantine**: Remove 389 rows with spikes/suspected faults from normal_data
3. **Session Splitting**: Gap threshold = 10s (config.gap_threshold_sec)
4. **Feature Engineering**: 12 session-aware features (build_features_v2.py)
5. **Scaling**: StandardScaler fitted on 34,374 clean training rows

---

## Known Data Quality Issues

| Issue | Dataset | Impact |
|-------|---------|--------|
| 35-row overlap | test.csv ↔ pilot_data.csv | Potential leakage (Development) |
| Post-hoc label expansion | pilot_data.csv | Pilot is Development, not Held-out |
| Synthetic anomalies | eval_suite, UCI, IoTsec | Not physical events; never mix with recorded results |
| Single-room training | normal_data.csv | No geographic/hardware diversity |
| Sensor resolution mismatch | All recorded | 0.1°C vs DHT11 1°C spec — UNKNOWN sensor type |
| No hardware validation | All | No ESP32 connected during eval |

---

## Data Access

- **Raw data**: `data/raw/` (gitignored *.db, uploaded files)
- **Processed features**: `data/processed/features_v2/` (regenerable)
- **Benchmarks**: `data/benchmarks/` (downloaded on demand, gitignored)
- **Reproducibility**: Run `python preprocess/clean_datasets.py` then `python features/build_features_v2.py`

---

## Licensing

- Student-recorded data: Academic use only
- UCI #357: CC-BY 4.0 (UCI ML Repository)
- IoTsec: Research use (ESORICS 2017 proceedings)