# Handoff: where the project stands

Project: AI-Based IoT Sensor Anomaly Detection. Student: Dungu Avinash Reddy, Roll RK3P25KZA09, Reg. 12509090.
Repository (public): https://github.com/AviReddy06/iot-sensor-anomaly-detection
Environment: Windows, Python 3.14, Node 22, ESP32 + DHT11 on GPIO 4, 2 s sampling, 115,200 baud.
Read project-rules.md first. Facts marked (audit) were reported by the previous coding agent and have not been independently re-checked.

## Two versions of the system
- v1 (tag v1-two-method-baseline, commit 04e6139): Z-score baseline vs Isolation Forest, 14 session-aware features, threshold = 1st percentile of normal scores (-0.16307), trained on 36,941 rows.
  - Test set (55 rows, one event of 10 rows): Isolation Forest caught 10/10 with 5 false alarms; Z-score 7/10 with 0.
  - Pilot set with the ORIGINAL labels (3,084 rows, 46 event rows): Isolation Forest 46/46 with 280 false alarms; Z-score 41/46 with 389.
- v2 (current main; tag v2-before-webapp at 10347c2): hybrid Isolation Forest + adaptive EWMA-Z, 12 features, 34,374 clean training rows (389 rows quarantined).

## Audit findings (audit)
- The pilot annotations were expanded after results were seen (commit 4f8ca08): event 1 from 27 rows to 466, positives 46 to 504. Pilot results for v2 are development data.
- The 143 anomalies in the evaluation suite are synthetic injections (seed 42, six fault types) on held-out normal rows. The UCI #357 and IoTsec benchmark anomalies are synthetic injections too.
- IoTsec: the hybrid produces 470 false positives (precision 0.509); the README quoted only recall.
- Medium sensitivity in the old UI (0.25th percentile, -0.21657) was chosen for best F1 on the synthetic suite. The web backend uses Low 0.5th, Medium 1st, High 5th percentile; Medium is the default.
- test.csv and pilot_data.csv share 35 identical rows (22:02:14 to 22:03:23). The pilot has no rows for 22:03:25 to 22:04:05, where test.csv holds the 10-row event. The reason is unknown; ask the student.
- No credentials found in tracked files.

## What exists
- backend/ (FastAPI, SQLite, signed admin tokens, client-safe schemas), tests/ (55 passing), committed as 2ccb80d.
- frontend/ (React + Vite) with a thermohygrograph client page and an admin page, started by `python run_ui.py` on port 8000. This work was NOT committed when the previous agent stopped.
- Phases not run: plots_v2, README honesty edit, results reconciliation, docs, final commit.
- Outside the repo, the student holds: an IEEE-format report, a 12-slide deck, and an older report. All describe v1 numbers and must be updated after the reconciliation.

## Known problem
The browser still shows an old dark "AetherSense / IoT Anomaly Hub" interface with KPI cards, Hardware Node, F1 hero numbers, "zero false alarms" and webhook settings. The client page must be rebuilt per the iot-client-ui skill, and `/` must serve the client page while `/admin` shows the login.

## Open items
1. Rebuild and verify the client page; move technical content to admin; screenshot at three widths.
2. Commit the frontend by explicit file names after checks pass.
3. evaluate/reconcile_results.py and docs/results_reconciliation.md: one row per version, detector, dataset and label set, with provenance and role.
4. README honesty edit: add provenance and role, state the relabelled pilot, the synthetic suites, the IoTsec false positives, and the test/pilot overlap.
5. eda/generate_plots_v2.py: break lines at gaps over 10 s; title the test figures "Test Set: Anomaly Window" and "Test Set: Anomaly Detail" (never "Injected").
6. Auto-detect of the serial port must skip anything described as Bluetooth.
7. New hardware recording (baseline and logged events), evaluated without tuning.

## Questions only the student can answer
- How were the test event, the two pilot events and the blowing episodes in the normal data produced?
- Is the sensor a DHT11 or a DHT22 (read the label)? The data shows 0.1 resolution.
- What is due, and when?
