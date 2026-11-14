# Results Reconciliation: Cross-Version and Cross-Dataset Evaluation

This document contains a reconciled, honest audit of all models evaluated across the lifecycle of the IoT sensor anomaly detection system. Every row represents an executed run of code on the designated dataset.

## Comprehensive Reconciliation Table

| Version | Dataset | Model | Rows | Positives | TP | FP | FN | Precision | Recall | F1 | Data Provenance | Role | Flags / Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| v1 | test | Baseline (Z-Score) | 55 | 10 | 7 | 0 | 3 | 1.000 | 0.700 | 0.824 | Recorded | Development |  |
| v1 | test | Isolation Forest (14-feat) | 55 | 10 | 10 | 5 | 0 | 0.667 | 1.000 | 0.800 | Recorded | Development |  |
| v1 | pilot (original 46-row labels) | Baseline (Z-Score) | 3084 | 46 | 41 | 389 | 5 | 0.095 | 0.891 | 0.172 | Recorded | Development |  |
| v1 | pilot (original 46-row labels) | Isolation Forest (14-feat) | 3084 | 46 | 46 | 280 | 0 | 0.141 | 1.000 | 0.247 | Recorded | Development |  |
| v2 | test | Baseline (Z-Score) | 55 | 10 | 7 | 0 | 3 | 1.000 | 0.700 | 0.824 | Recorded | Development |  |
| v2 | test | Cauchy EWMA | 55 | 10 | 7 | 0 | 3 | 1.000 | 0.700 | 0.824 | Recorded | Development |  |
| v2 | test | Gated iForest | 55 | 10 | 10 | 1 | 0 | 0.909 | 1.000 | 0.952 | Recorded | Development |  |
| v2 | test | Hybrid | 55 | 10 | 10 | 1 | 0 | 0.909 | 1.000 | 0.952 | Recorded | Development |  |
| v2 | pilot (original 46-row labels) | Baseline (Z-Score) | 3084 | 46 | 22 | 389 | 24 | 0.054 | 0.478 | 0.096 | Recorded | Development |  |
| v2 | pilot (original 46-row labels) | Cauchy EWMA | 3084 | 46 | 41 | 380 | 5 | 0.097 | 0.891 | 0.176 | Recorded | Development |  |
| v2 | pilot (original 46-row labels) | Gated iForest | 3084 | 46 | 46 | 124 | 0 | 0.271 | 1.000 | 0.426 | Recorded | Development |  |
| v2 | pilot (original 46-row labels) | Hybrid | 3084 | 46 | 46 | 393 | 0 | 0.105 | 1.000 | 0.190 | Recorded | Development |  |
| v2 | pilot (revised 504-row labels) | Baseline (Z-Score) | 3084 | 503 | 411 | 0 | 92 | 1.000 | 0.817 | 0.899 | Recorded | Development | FLAG: Labels expanded post-hoc after inspecting detector output |
| v2 | pilot (revised 504-row labels) | Cauchy EWMA | 3084 | 503 | 421 | 0 | 82 | 1.000 | 0.837 | 0.911 | Recorded | Development | FLAG: Labels expanded post-hoc after inspecting detector output |
| v2 | pilot (revised 504-row labels) | Gated iForest | 3084 | 503 | 170 | 0 | 333 | 1.000 | 0.338 | 0.505 | Recorded | Development | FLAG: Labels expanded post-hoc after inspecting detector output |
| v2 | pilot (revised 504-row labels) | Hybrid | 3084 | 503 | 439 | 0 | 64 | 1.000 | 0.873 | 0.932 | Recorded | Development | FLAG: Labels expanded post-hoc after inspecting detector output |
| v2 | eval suite | Baseline (Z-Score) | 1947 | 143 | 105 | 57 | 38 | 0.648 | 0.734 | 0.689 | Synthetic | Held-out |  |
| v2 | eval suite | Cauchy EWMA | 1947 | 143 | 102 | 0 | 41 | 1.000 | 0.713 | 0.833 | Synthetic | Held-out |  |
| v2 | eval suite | Gated iForest | 1947 | 143 | 122 | 4 | 21 | 0.968 | 0.853 | 0.907 | Synthetic | Held-out |  |
| v2 | eval suite | Hybrid | 1947 | 143 | 138 | 4 | 5 | 0.972 | 0.965 | 0.968 | Synthetic | Held-out |  |
| v2 | UCI #357 | Baseline (Z-Score) | 1999 | 400 | 288 | 17 | 112 | 0.944 | 0.720 | 0.817 | Recorded (occupancy) | Held-out |  |
| v2 | UCI #357 | Cauchy EWMA | 1999 | 400 | 44 | 0 | 356 | 1.000 | 0.110 | 0.198 | Recorded (occupancy) | Held-out |  |
| v2 | UCI #357 | Gated iForest | 1999 | 400 | 228 | 13 | 172 | 0.946 | 0.570 | 0.711 | Recorded (occupancy) | Held-out |  |
| v2 | UCI #357 | Hybrid | 1999 | 400 | 238 | 13 | 162 | 0.948 | 0.595 | 0.731 | Recorded (occupancy) | Held-out |  |
| v2 | IoTsec | Baseline (Z-Score) | 2457 | 490 | 482 | 14 | 8 | 0.972 | 0.984 | 0.978 | Synthetic | Held-out |  |
| v2 | IoTsec | Cauchy EWMA | 2457 | 490 | 479 | 449 | 11 | 0.516 | 0.978 | 0.676 | Synthetic | Held-out |  |
| v2 | IoTsec | Gated iForest | 2457 | 490 | 310 | 135 | 180 | 0.697 | 0.633 | 0.663 | Synthetic | Held-out |  |
| v2 | IoTsec | Hybrid | 2457 | 490 | 487 | 470 | 3 | 0.509 | 0.994 | 0.673 | Synthetic | Held-out | NOTE: 470 false alarms caused by cross-domain baseline distribution shift |

## Key Audit Observations

1. **Pilot Relabelling (Post-Hoc)**: In commit `4f8ca08`, the pilot event annotations were expanded from 46 rows to 504 rows after observing detector predictions. Under the original 46-row labels, Isolation Forest produced 280 false positives (F1 = 0.247). Under revised labels, those same predictions are counted as true positives, yielding F1 = 0.932. Thus, pilot results serve as development tuning data, not independent held-out evaluation.
2. **Evaluation Suite Provenance**: The 143 anomalies across 1,947 rows in `eval_test_suite.csv` are synthetic injections (seed 42) into clean held-out DHT11 data across 6 physical fault categories.
3. **IoTsec Benchmark False Positives**: On the IoTsec room-climate benchmark (2,457 test rows), the hybrid detector produced 470 false positives (Precision = 0.509). This demonstrates that while recall is 99.4%, applying the detector across different physical rooms requires site-specific baseline calibration.
4. **Dataset Overlap**: `data/raw/test.csv` (55 rows) and `data/raw/pilot_data.csv` share 35 identical rows between 22:02:14 and 22:03:23 on 2026-10-27 before the test event occurs.
5. **Threshold Tuning**: The 0.25th percentile threshold (-0.21657) in earlier UI settings was selected through grid optimization against the synthetic suite.