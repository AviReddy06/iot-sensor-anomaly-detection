# Project Progress Tracking

## System: AI-Based IoT Sensor Anomaly Detection (ESP32 + DHT11)
Student: Dungu Avinash Reddy | Roll: RK3P25KZA09 | Reg: 12509090

---

## Phase Checklist & Status

| Phase | Description | Status | Evidence / Notes |
| :--- | :--- | :--- | :--- |
| **Phase 0** | Orient & Audit (read-only) | **PASS** | Git state verified; http://127.0.0.1:8000 inspected; banned tropes found; dev servers audited. |
| **Phase 1** | Client Page (Digital Thermohygrograph) | **IN PROGRESS** | `docs/client_ui_audit.md`, `docs/design.md`, thermohygrograph UI build (`ClientStripChart`, `RoomMap`, `UnusualLog`), screenshots at 1440/768/390px, critique & revision pass. |
| **Phase 2** | Admin Page (Behind Login & Technical Pages) | **PENDING** | Login guard (503/401/429), Bluetooth filter in port scan, 4-label metrics, pilot original vs revised, IoTsec 470 FP, sensitivity tuning. |
| **Phase 3** | Verify (Safety, CSS, DOM, Offline, Tests) | **PENDING** | Pytest passes, no banned CSS/JS properties, clean client DOM, localhost-only network, axe-core contrast check. |
| **Phase 4** | Checkpoint Commit | **PENDING** | Explicit git add and commit. |
| **Phase 5** | Evidence & Documents | **PENDING** | `reconcile_results.py`, `results_reconciliation.md`, `generate_plots_v2.py`, honest `README.md`, `architecture.md`. |
| **Phase 6** | Hardware Session | **PENDING** | Check for raw hardware files; evaluate if present. |

---

## Current Step
- Starting Phase 1: Creating `docs/client_ui_audit.md` and revising `docs/design.md`.
