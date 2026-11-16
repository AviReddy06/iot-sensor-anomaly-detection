# AI-Based IoT Sensor Anomaly Detection — Streamlit Dashboard

**Student:** Dungu Avinash Reddy | **Roll:** RK3P25KZA09 | **Reg:** 12509090  
**Hardware Node:** ESP32 + DHT11 indoor climate monitor (GPIO 4, 115,200 baud, 0.5 Hz sampling)

---

## 1. System Overview

This project provides a **Streamlit-based dashboard** for anomaly detection on ESP32 + DHT11 indoor climate telemetry. The dashboard visualizes temperature/humidity data and runs anomaly detection using multiple algorithms:

1. **Z-Score Baseline** — Fixed threshold (3.0σ) on temperature/humidity
2. **Adaptive Gated EWMA-Z** — Causal Cauchy-weighted EWMA baseline with rate-gating
3. **Isolation Forest + Gated Persistence** — Unsupervised detector with 12 time-aware features
4. **Hybrid Ensemble (IF | Adaptive EWMA-Z)** — Ensemble combining spike and drift sensitivity

---

## 2. Launch Commands (Windows PowerShell)

```powershell
# Install dependencies
pip install -r requirements.txt

# Run the main dashboard (Home page with navigation)
streamlit run dashboard/Home.py --server.port 8501 --server.address localhost

# Or run specific apps:
streamlit run dashboard/user_app.py      # Client Live Monitor
streamlit run dashboard/admin_app.py     # Admin & Model Manager
```

**Access:** http://localhost:8501

---

## 3. Dashboard Pages

| Page | File | Description |
|------|------|-------------|
| **Home** | `dashboard/Home.py` | System overview, metrics, navigation |
| **Analyse** | `dashboard/pages/1_Analyse.py` | Load eval suite, pilot, test, upload CSV, live ESP32 |
| **Results** | `dashboard/pages/2_Results.py` | Client View & Technical View with sensitivity tuning |
| **Model & Metrics** | `dashboard/pages/3_Model_Metrics.py` | Live metrics from `models/evaluation_summary.json` |
| **Client Monitor** | `dashboard/user_app.py` | Live monitor for room occupants |
| **Admin Panel** | `dashboard/admin_app.py` | Admin & Model Manager |

---

## 3. Key Audit Findings & Disclosures

1. **Post-Hoc Pilot Relabelling**: Pilot annotations expanded from 46 to 504 rows after seeing detector predictions (commit `4f8ca08`). Pilot is **Development data**, not held-out.

2. **Synthetic Evaluation Suite**: 143 anomalies (seed 42, 6 fault types) injected into held-out normal data. **Never mixed** with recorded-event results.

3. **IoTsec False Alarms**: 470 FP (Precision = 0.509) due to cross-domain baseline shift. Site-specific calibration required.

4. **Test/Pilot Overlap**: 35 identical rows shared between test.csv and pilot_data.csv (22:02:14–22:03:23).

5. **Threshold Tuning**: 0.25th percentile (-0.21657) tuned on synthetic eval_suite (Development data).

---

## 4. System Limitations

- **Sampling**: 0.5 Hz (2s interval) — sub-2s transients undetectable
- **DHT11 Precision**: ±1.0°C, ±5% RH (data shows 0.1°C — sensor type UNKNOWN)
- **Cross-Domain Transfer**: Requires site-specific calibration (IoTsec: 470 FP)
- **No Hardware Validation**: All tests used simulated replay
- **Event Production Unknown**: Test/pilot event generation method UNKNOWN
- **No Load/Soak/CI Testing**: Not performed

---

## 5. Directory Structure

```
.
├── dashboard/                    # Streamlit dashboard app
│   ├── Home.py                   # Main entry point
│   ├── user_app.py               # Client Live Monitor
│   ├── admin_app.py              # Admin & Model Manager
│   ├── feature_utils.py          # Shared utilities
│   └── pages/
│       ├── 1_Analyse.py          # Analyze data
│       ├── 2_Results.py          # View results
│       └── 3_Model_Metrics.py    # Model metrics
├── requirements.txt              # Python dependencies
├── .gitignore
├── .env.example
└── README.md
```

---

## 6. Quick Start

```powershell
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the dashboard
streamlit run dashboard/Home.py --server.port 8501 --server.address localhost

# 3. Open browser
# http://localhost:8501
```

---

## 7. Key Results (from `evaluate/run_all.py`)

| Dataset | Model | Precision | Recall | F1 | Provenance | Role |
|---------|-------|-----------|--------|-----|------------|------|
| Test | Hybrid (IF + EWMA-Z) | 0.909 | 1.000 | 0.952 | Recorded | Development |
| Pilot (Revised) | Hybrid | 1.000 | 0.873 | 0.932 | Recorded | Development* |
| Eval Suite | Hybrid | 0.972 | 0.965 | 0.968 | Synthetic | Held-out |
| IoTsec | Hybrid | 0.509 | 0.994 | 0.673 | Synthetic | Held-out |

* Pilot labels expanded post-hoc (Development data)

---

## 8. Quick Start

```powershell
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run dashboard
streamlit run dashboard/Home.py --server.port 8501 --server.address localhost

# 3. Open browser
# http://localhost:8501
```

---

**Student:** Dungu Avinash Reddy | **Roll:** RK3P25KZA09 | **Reg:** 12509090  
**Hardware:** ESP32 + DHT11 (GPIO 4, 115,200 baud, 0.5 Hz)