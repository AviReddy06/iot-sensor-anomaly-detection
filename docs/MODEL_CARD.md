# Model Card: IoT Sensor Anomaly Detection (v2.0-hybrid)

## Model Details
- **Name**: Hybrid Isolation Forest + Adaptive EWMA-Z
- **Version**: v2.0-hybrid
- **Date**: 2026-11-15
- **Type**: Unsupervised anomaly detection for indoor temperature/humidity telemetry
- **Architecture**: Isolation Forest (200 trees) + Adaptive Cauchy EWMA-Z, logical OR fusion
- **Features**: 12 session-aware features (temperature, humidity, rates, EWMA residuals, session IDs)
- **Training Data**: 34,374 clean rows from ESP32+DHT11 (student's room), 389 rows quarantined as anomalies
- **Framework**: scikit-learn 1.9.1, Python 3.14

## Intended Use
- **Primary**: Real-time anomaly detection on ESP32+DHT11 telemetry stream (2s sampling)
- **Deployment**: FastAPI backend on local machine (Windows), React+Vite frontend
- **Sensitivity Presets**: Low (0.5th %ile), Medium (1st %ile, default), High (5th %ile)
- **Out of Scope**: Cross-room deployment without recalibration, outdoor environments, non-DHT11 sensors

## Training Data
| Dataset | Rows | Provenance | Role |
|---------|------|------------|------|
| normal_data.csv (clean) | 34,374 | Recorded (student's room) | Development |
| normal_data.csv (quarantined) | 389 | Recorded (student's room) | Development (excluded) |

**Note**: Training data comes from a single room with a single DHT11 sensor. No geographic, seasonal, or hardware diversity.

## Evaluation Data

| Dataset | Provenance | Role | Rows | Events | Notes |
|---------|------------|------|------|--------|-------|
| test | Recorded (blowing on sensor) | Development | 56 | 1 (10 rows) | Student-annotated |
| pilot (original labels) | Recorded | Development | 3,084 | 2 (46 rows) | 46-row labels |
| pilot (revised labels) | Recorded | Development | 3,084 | 2 (504 rows) | Labels expanded post-hoc |
| eval_suite | Synthetic (seed 42) | Held-out | 1,947 | 143 (6 faults) | Injected on held-out normal |
| UCI #357 | Synthetic injections | Held-out | ~2,000 | 400 | Cross-domain |
| IoTsec | Synthetic injections | Held-out | ~2,457 | 490 | Cross-domain |

## Metrics Summary (Held-out Synthetic)

| Model | Dataset | Precision | Recall | F1 | False Alarms/Day |
|-------|---------|-----------|--------|-----|------------------|
| Hybrid | eval_suite | 0.972 | 0.965 | 0.968 | 0.4 |
| Hybrid | UCI #357 | 0.948 | 0.595 | 0.731 | N/A |
| Hybrid | IoTsec | 0.509 | 0.994 | 0.673 | N/A |

**Key Finding**: IoTsec precision drops to 0.509 (470 false positives) due to cross-domain baseline shift. Site-specific calibration required.

## Thresholds
| Sensitivity | IF Threshold | EWMA-Z Threshold | Z-Score Threshold |
|-------------|--------------|------------------|-------------------|
| Low (0.5th %ile) | -0.2008 | 3.5 | 3.0 |
| Medium (1st %ile, default) | -0.1768 | 3.5 | 3.0 |
| High (5th %ile) | -0.1136 | 3.5 | 3.0 |
| **Tuned (0.25th %ile)** | **-0.2166** | 3.5 | 3.0 |

The tuned threshold (0.25th percentile, -0.21657) was selected on the synthetic eval_suite (Development data).

## Limitations
1. **Single-room training**: Model trained on one ESP32+DHT11 in one room; cross-room generalization unproven (IoTsec shows 470 FP)
2. **Post-hoc pilot labelling**: Pilot labels expanded from 46 to 504 rows after seeing detector output — pilot is Development data
3. **Synthetic eval_suite**: 143 anomalies are injected (seed 42), not recorded physical events
4. **Test/pilot overlap**: 35 identical rows shared between test.csv and pilot_data.csv
5. **DHT11 resolution**: Sensor reports 1°C/1% RH resolution; 0.1°C resolution in data suggests possible DHT22 or interpolation
6. **No hardware validation**: No ESP32 board connected during evaluation; all tests use simulated data
7. **Threshold tuning on Development data**: The 0.25th percentile was chosen for best F1 on synthetic suite

## Ethical Considerations
- No personal data collected
- Local-only deployment (no cloud)
- Admin authentication required for configuration changes

## Version History
- v1 (tag v1-two-method-baseline): 14 features, Z-score vs IF, threshold = 1st percentile normal scores
- v2 (current): 12 features, hybrid IF + EWMA-Z, 34,374 clean training rows, quarantine cleaning

## Freeze Verification
- **Commit**: 92a4ae6
- **Tag**: eval-freeze
- **Models SHA256**: iforest=6f7de4c5, scaler=e8a1fc15, thresholds=485d6e87
- **Code SHA256**: feature_engine=dcf90523, build_features_v2=9849a5bb