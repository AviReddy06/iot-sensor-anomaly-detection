# IoT Sensor Anomaly Detection

End-to-end anomaly detection system for DHT11 temperature/humidity sensor data collected via ESP32 over serial USB.

## Architecture Overview

```
ESP32 (GPIO 4, DHT11) → Serial 115200 → Python Logger → CSV → ML Pipeline → Dashboard
```

- **Hardware**: ESP32 + DHT11 on GPIO 4, 2000ms sampling interval
- **Communication**: USB Serial at 115200 baud
- **Deployment**: Windows PC (Python handles preprocessing, ML inference, dashboard)
- **Primary ML**: Isolation Forest (unsupervised, trained on normal data only)

## Project Structure

```
iot-anomaly-detection/
├── firmware/          # ESP32 sketch (not in repo - document pinout here)
├── collect/           # Data collection scripts
├── data/
│   ├── raw/           # Original CSV datasets (immutable)
│   ├── processed/     # Cleaned, resampled data (generated)
│   └── splits/        # Train/val/test indices (generated)
├── preprocess/        # Validation, cleaning, resampling
├── eda/               # Exploratory analysis notebooks
├── features/          # Feature engineering pipeline
├── train/             # Model training & hyperparameter tuning
├── evaluate/          # Model evaluation & threshold tuning
├── models/            # Serialized model artifacts
├── detect/            # Real-time inference on serial stream
├── dashboard/         # Streamlit monitoring UI
├── tests/             # Unit & integration tests
├── docs/              # Documentation & runbooks
└── .github/workflows/ # CI/CD pipelines
```

## Quick Start

### Prerequisites
- Python 3.10+
- ESP32 with DHT11 on GPIO 4, flashing firmware (see `firmware/README.md`)
- USB connection to Windows PC

### Installation

```bash
# Clone and enter project
cd iot-anomaly-detection

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Verify environment
python verify_env.py
```

### Data Collection

```bash
# Update COM port in config.yaml if needed
python collect/logger.py
```

Press `Ctrl+C` to stop. Data writes to `data/raw/normal_data.csv`.

### Configuration

Edit `config.yaml` for:
- Serial port (default: COM19)
- Baud rate (default: 115200)
- Sampling interval (default: 2000ms)
- Dataset paths
- Model paths

## Datasets

| File | Records | Purpose |
|------|---------|---------|
| `data/raw/normal_data.csv` | 49,728 | Candidate normal training set (verify first) |
| `data/raw/pilot_data.csv` | 3,087 | Validation - contains 2 reported anomalies |
| `data/raw/test.csv` | 56 | Hold-out test set (never train) |
| `data/raw/test_labels.csv` | 1 | Event-level ground truth for test.csv |

**Rules:**
- Never modify original CSVs in `data/raw/`
- Never train on test set
- Verify normality of normal_data.csv before training

## Development Phases

1. **Setup** (complete) — Repo structure, config, dependencies
2. **Hardware Doc** — Document ESP32 pinout, wiring
3. **Data Pipeline** — Robust logger with rotation/validation
4. **Preprocessing** — Validation, cleaning, resampling
5. **EDA** — Distributions, correlations, anomaly characterization
6. **Features** — Rolling stats, diffs, time encodings
7. **Training** — IsolationForest on verified normal data
8. **Evaluation** — Metrics on test set, threshold tuning
9. **Live Detection** — Real-time inference + alerts
10. **Dashboard** — Streamlit monitoring UI
11. **Tests & Docs** — CI, runbooks, model card

## License

Academic/engineering project — internal use.