# Evaluation Results: All Models, All Datasets

Generated: 2026-11-15T15:43:38.434264+00:00Z
Commit: cfe96e04
Freeze verified: True

| Version | Dataset | Model | Rows | Positives | TP | FP | FN | Precision | Recall | F1 | Event Recall | Delay (s) | FA/Day | CI Low | CI High | CI Note | Provenance | Role | Label Set | Flag |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| v2 | test | Z-Score Baseline | 55 | 10 | 7 | 0 | 3 | 1.000 | 0.700 | 0.824 | 1.000 | 0.0 | 0.0 | 0.700 | 0.700 |  | Recorded | Development |  |  |
| v2 | test | Adaptive EWMA-Z | 55 | 10 | 7 | 0 | 3 | 1.000 | 0.700 | 0.824 | 1.000 | 0.0 | 0.0 | 0.700 | 0.700 |  | Recorded | Development |  |  |
| v2 | test | Isolation Forest | 55 | 10 | 10 | 1 | 0 | 0.909 | 1.000 | 0.952 | 1.000 | 0.0 | 792.7 | 1.000 | 1.000 |  | Recorded | Development |  |  |
| v2 | test | Hybrid (IF + EWMA-Z) | 55 | 10 | 10 | 1 | 0 | 0.909 | 1.000 | 0.952 | 1.000 | 0.0 | 792.7 | 1.000 | 1.000 |  | Recorded | Development |  |  |
| v2 | pilot (original) | Z-Score Baseline | 3084 | 46 | 42 | 389 | 4 | 0.097 | 0.913 | 0.176 | 1.000 | 0.0 | 7.8 | 0.852 | 1.000 |  | Recorded | Development | original |  |
| v2 | pilot (original) | Adaptive EWMA-Z | 3084 | 46 | 41 | 380 | 5 | 0.097 | 0.891 | 0.176 | 1.000 | 0.0 | 15.7 | 0.815 | 1.000 |  | Recorded | Development | original |  |
| v2 | pilot (original) | Isolation Forest | 3084 | 46 | 46 | 124 | 0 | 0.271 | 1.000 | 0.426 | 1.000 | 0.0 | 321.7 | 1.000 | 1.000 |  | Recorded | Development | original |  |
| v2 | pilot (original) | Hybrid (IF + EWMA-Z) | 3084 | 46 | 46 | 393 | 0 | 0.105 | 1.000 | 0.190 | 1.000 | 0.0 | 31.4 | 1.000 | 1.000 |  | Recorded | Development | original |  |
| v2 | pilot (revised) | Z-Score Baseline | 3084 | 503 | 431 | 0 | 72 | 1.000 | 0.857 | 0.923 | 1.000 | 0.0 | 0.0 | 0.500 | 0.886 |  | Recorded | Development | revised | FLAG: Labels expanded post-hoc after inspecting detector output |
| v2 | pilot (revised) | Adaptive EWMA-Z | 3084 | 503 | 421 | 0 | 82 | 1.000 | 0.837 | 0.911 | 1.000 | 0.0 | 0.0 | 0.605 | 0.856 |  | Recorded | Development | revised | FLAG: Labels expanded post-hoc after inspecting detector output |
| v2 | pilot (revised) | Isolation Forest | 3084 | 503 | 170 | 0 | 333 | 1.000 | 0.338 | 0.505 | 1.000 | 0.0 | 0.0 | 0.288 | 0.947 | Wide interval - inconclusive | Recorded | Development | revised | FLAG: Labels expanded post-hoc after inspecting detector output |
| v2 | pilot (revised) | Hybrid (IF + EWMA-Z) | 3084 | 503 | 439 | 0 | 64 | 1.000 | 0.873 | 0.932 | 1.000 | 0.0 | 0.0 | 0.867 | 0.947 |  | Recorded | Development | revised | FLAG: Labels expanded post-hoc after inspecting detector output |
| v2 | eval_suite | Z-Score Baseline | 1947 | 143 | 105 | 57 | 38 | 0.648 | 0.734 | 0.689 | 1.000 | 6.8 | 0.1 | 0.591 | 0.871 |  | Synthetic | Held-out |  |  |
| v2 | eval_suite | Adaptive EWMA-Z | 1947 | 143 | 102 | 0 | 41 | 1.000 | 0.713 | 0.833 | 1.000 | 7.5 | 0.0 | 0.563 | 0.867 |  | Synthetic | Held-out |  |  |
| v2 | eval_suite | Isolation Forest | 1947 | 143 | 122 | 4 | 21 | 0.968 | 0.853 | 0.907 | 1.000 | 1.7 | 0.4 | 0.583 | 0.968 |  | Synthetic | Held-out |  |  |
| v2 | eval_suite | Hybrid (IF + EWMA-Z) | 1947 | 143 | 138 | 4 | 5 | 0.972 | 0.965 | 0.968 | 1.000 | 1.7 | 0.4 | 0.952 | 0.983 |  | Synthetic | Held-out |  |  |
| v2 | UCI #357 | Z-Score Baseline | 1999 | 400 | 288 | 17 | 112 | 0.944 | 0.720 | 0.817 |  |  |  |  |  |  | Synthetic | Held-out |  |  |
| v2 | UCI #357 | Adaptive EWMA-Z | 1999 | 400 | 44 | 0 | 356 | 1.000 | 0.110 | 0.198 |  |  |  |  |  |  | Synthetic | Held-out |  |  |
| v2 | UCI #357 | Isolation Forest | 1999 | 400 | 227 | 13 | 172 | 0.946 | 0.570 | 0.711 |  |  |  |  |  |  | Synthetic | Held-out |  |  |
| v2 | UCI #357 | Hybrid (IF + EWMA-Z) | 1999 | 400 | 238 | 13 | 162 | 0.948 | 0.595 | 0.731 |  |  |  |  |  |  | Synthetic | Held-out |  |  |
| v2 | IoTsec | Z-Score Baseline | 2457 | 490 | 482 | 14 | 8 | 0.972 | 0.984 | 0.978 |  |  |  |  |  |  | Synthetic | Held-out |  |  |
| v2 | IoTsec | Adaptive EWMA-Z | 2457 | 490 | 479 | 449 | 11 | 0.516 | 0.978 | 0.676 |  |  |  |  |  |  | Synthetic | Held-out |  |  |
| v2 | IoTsec | Isolation Forest | 2457 | 490 | 310 | 135 | 180 | 0.697 | 0.633 | 0.663 |  |  |  |  |  |  | Synthetic | Held-out |  |  |
| v2 | IoTsec | Hybrid (IF + EWMA-Z) | 2457 | 490 | 487 | 470 | 3 | 0.509 | 0.994 | 0.673 |  |  |  |  |  |  | Synthetic | Held-out |  | NOTE: 470 false alarms caused by cross-domain baseline distribution shift |
| v1 | test | Baseline (Z-Score) | 55 | 10 | 7 | 0 | 3 | 1.000 | 0.700 | 0.824 |  |  |  |  |  |  | Recorded | Development |  |  |
| v1 | test | Isolation Forest (14-feat) | 55 | 10 | 10 | 5 | 0 | 0.667 | 1.000 | 0.800 |  |  |  |  |  |  | Recorded | Development |  |  |
| v1 | pilot (original 46-row labels) | Baseline (Z-Score) | 3084 | 46 | 41 | 389 | 5 | 0.095 | 0.891 | 0.172 |  |  |  |  |  |  | Recorded | Development | original 46-row |  |
| v1 | pilot (original 46-row labels) | Isolation Forest (14-feat) | 3084 | 46 | 46 | 280 | 0 | 0.141 | 1.000 | 0.247 |  |  |  |  |  |  | Recorded | Development | original 46-row |  |
| v2 | test | Hybrid @ Low (0.5th %ile) | 55 | 10 | 10 | 2 | 0 | 0.833 | 1.000 | 0.909 | 1.000 | 0.0 | 792.7 | 1.000 | 1.000 |  | Recorded | Development | Tuned on synthetic suite (0.25th %ile = -0.21657) |  |
| v2 | test | Hybrid @ Medium (1st %ile) | 55 | 10 | 10 | 3 | 0 | 0.769 | 1.000 | 0.870 | 1.000 | 0.0 | 792.7 | 1.000 | 1.000 |  | Recorded | Development | Tuned on synthetic suite (0.25th %ile = -0.21657) |  |
| v2 | test | Hybrid @ High (5th %ile) | 55 | 10 | 10 | 4 | 0 | 0.714 | 1.000 | 0.833 | 1.000 | 0.0 | 792.7 | 1.000 | 1.000 |  | Recorded | Development | Tuned on synthetic suite (0.25th %ile = -0.21657) |  |

## Key Observations

1. **Pilot is Development Data**: Labels expanded post-hoc (46→504 rows) after seeing detector output.
2. **Synthetic Suite Tuned**: 0.25th percentile threshold (-0.21657) optimized on eval_suite (Development).
3. **IoTsec False Alarms**: Hybrid produces 470 FP (Precision=0.509) due to cross-domain shift.
4. **Test/Pilot Overlap**: 35 identical rows (22:02:14–22:03:23) shared between datasets.
5. **v1 vs v2**: v1 used 14 features; v2 uses 12 features with quarantine cleaning.