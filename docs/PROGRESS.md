# Project Progress Tracking

## System: AI-Based IoT Sensor Anomaly Detection (ESP32 + DHT11)
Student: Dungu Avinash Reddy | Roll: RK3P25KZA09 | Reg: 12509090

---

## Phase Checklist & Status

| Phase | Description | Status | Evidence / Notes |
| :--- | :--- | :--- | :--- |
| **Phase 0** | Orient & Audit (read-only) | **PASS** | Git state verified; http://127.0.0.1:8000 inspected; banned tropes audited; server audited. |
| **Phase 1** | Client Page (Digital Thermohygrograph) | **PASS** | `docs/client_ui_audit.md`, `docs/design.md`, thermohygrograph UI built (`ClientStripChart`, `RoomMap`, `UnusualLog`), screenshots at 1440/768/390px captured, visual critique & revision pass completed. |
| **Phase 2** | Admin Page (Behind Login & Technical Pages) | **PASS** | Login guard (503/401/429), Bluetooth filter in port scan, 4-label metrics, pilot original vs revised, IoTsec 470 FP, dataset downloads, sensitivity tuning. |
| **Phase 3** | Verify (Safety, CSS, DOM, Offline, Tests) | **PASS** | 56 pytest tests passed; `scripts/verify_phase3.py` automated static & browser test suite passed (0 forbidden styles, 0 forbidden DOM terms, strictly localhost network, keyboard tab order verified). |
| **Phase 4** | Checkpoint Commit | **PASS** | Committed by explicit names: commit `4dad957` ("Client page rebuilt, admin page organised, tests updated"). |
| **Phase 5** | Evidence & Documents | **PASS** | `evaluate/reconcile_results.py` generated `docs/results_reconciliation.md`; `eda/generate_plots_v2.py` regenerated gap-aware figures; updated honest `README.md`, `docs/architecture.md`, `.env.example`, `requirements-web.txt`, `THIRD_PARTY.md`, `scripts/dev.ps1`. Committed: `d85afd2`. |
| **Phase 6** | Hardware Session | **SKIPPED** | `data/raw/new_baseline.csv` and `data/raw/new_events.csv` not present in workspace. Unmodified detector preserved. |

---

## Summary of Accomplishments
1. **Client Page (`/`)**: Follows the digital thermohygrograph aesthetic on archival paper (`#EEF1EF`) with continuous dual-ink traces (`#9B2C2C` temp, `#1D5C8C` hum), phase-space room map, plain-English unusual event log, and zero ML jargon. Enhanced with ASHRAE 55 thermal comfort target envelopes on both charts, live telemetry pulsing badges, and modular components under 250 lines.
2. **Event Deduplication**: Idempotent insert checks in `backend/database.py` and client-side deduplication in `UnusualLog.jsx` prevent replayed simulations from duplicating identical anomaly event records.
3. **Admin Page (`/admin`)**: Fully protected behind constant-time HMAC login and signed expiring tokens; rate-limited (5 attempts/min); 503 when `ADMIN_PASSWORD` is unset. Contains plain-text navigation with verified 4-label metrics, dataset downloads, and hardware/simulation streaming.
4. **Honest Reporting**: All figures and tables reconcile historical v1 vs current v2 numbers, disclose the post-hoc pilot relabelling, declare synthetic fault injections, report IoTsec 470 false alarms, and detail dataset overlap.
