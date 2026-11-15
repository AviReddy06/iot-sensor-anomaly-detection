# Project Progress Tracking: AI-Based IoT Sensor Anomaly Detection Hardening

**System:** AI-Based IoT Sensor Anomaly Detection (ESP32 + DHT11)  
**Student:** Dungu Avinash Reddy | **Roll:** RK3P25KZA09 | **Reg:** 12509090  
**Active Branch:** `hardening` | **Baseline Commit:** `6ebc827`  
**Timestamp:** 2026-11-15T05:50:00Z  

---

## Phase Checklist & Status

| Phase | Requirement | Description | Status | Evidence / Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 0** | R1 | Orient, Git Baseline & Environment | **PASS** | Branch `hardening` created; Python 3.14.8, Node v22.23.2, 8 required packages verified; 108/108 pytest tests passed in 86.41s. |
| **Phase 1** | R2 | API Contract & Integration | **PASS** | OpenAPI export to `docs/openapi.json` (34 paths), `docs/API.md` parity verified with running server; client schemas hardened (`extra="forbid"`); non-blocking `/ws/client` & `/ws/admin` separated; deterministic replay verified; 137 unit passed, 21 E2E passed. |
| **Phase 2** | R3 | Reliability & Fault Injection | **PLANNED** | FakeSerial double, SQLite WAL mode, busy timeout, retention purge, graceful shutdown, `/api/health`. |
| **Phase 3** | R4 | Security Hardening & Audits | **PLANNED** | Rate limiting, upload checks, path traversal rejection, CSV formula escaping, CSP headers, pip/npm audits. |
| **Phase 4** | R5 | Load, Stress & Soak Testing | **PLANNED** | `scripts/load_test.py` REST/WS/ingest/reconnect/soak, p95 latencies, breaking points, 300 dpi plots in `results/figures/`. |
| **Phase 5** | R6 | ML Evaluation Protocol & Code Freeze | **PLANNED** | `docs/evaluation_protocol.md`, code freeze SHA256 in `results/freeze.json` (tag `eval-freeze`), `evaluate/run_all.py`. |
| **Phase 6** | R7 | Hardware Check & Simulation | **PLANNED** | `scripts/hardware_check.py` test double, simulation fallback, holdout validation if new logs exist. |
| **Phase 7** | R8 | Frontend E2E, A11y & Visual Testing | **PLANNED** | Playwright test suite, axe-core 0 violations, visual regression, client DOM ban (17 forbidden internal terms). |
| **Phase 8** | R9 | CI Workflow & Preflight Script | **PLANNED** | `.github/workflows/ci.yml`, `scripts/preflight.ps1` GO/NO-GO gate. |
| **Phase 9** | R9 | Demo Readiness & Examiner Q&A | **PLANNED** | `docs/DEMO.md` 5-minute script, 8 examiner questions with verified answers. |
| **Phase 10** | R9 | Examiner Reports & Checkpoints | **PLANNED** | `docs/TEST_REPORT.md`, `docs/REPORT_INPUTS.md`, IEEE tables, limitations, clean checkpoint commits. |

---

## Phase 0 Baseline Summary

### 1. Git State
- **Branch:** `hardening` (created from `main`)
- **Tags present:** `v1-two-method-baseline`, `v2-before-webapp`
- **Recent commits:**
  - `6ebc827` Refine client UI: Area C
  - `a54d546` Refine client UI: Area D
  - `ab07147` Refine client UI: Area B
  - `bc7e10c` Refine client UI: Area A
  - `9f64f5d` Fix rate limiter to only record failed attempts and clear on success
  - `b7d3291` Update docs/PROGRESS.md with client polish and deduplication details
  - `6aefdac` Elevate client thermohygrograph with ASHRAE comfort bands and telemetry badges
  - `95f63eb` Deduplicate unusual events in database and client table log

### 2. Runtime Environment & Package Versions
- **Operating System:** Windows
- **Python Version:** 3.14.8
- **Node.js Version:** v22.23.2

| Package | Extracted Version | Purpose |
| :--- | :--- | :--- |
| `fastapi` | 0.142.2 | Asynchronous backend web framework |
| `uvicorn` | 0.54.0 | ASGI web server |
| `pydantic` | 2.13.5 | Schema declaration and strict input/output validation |
| `pytest` | 9.1.1 | Automated test runner |
| `websockets` | 17.2 | Real-time telemetry streaming protocol |
| `httpx` | 0.28.1 | Asynchronous HTTP client for contract and load testing |
| `scikit-learn` | 1.9.1 | Isolation Forest machine learning detector |
| `pandas` | 3.0.6 | Telemetry feature engineering and evaluation analysis |

### 3. Test Suite Baseline
- **Command:** `python -m pytest -q` (executed against temporary SQLite database)
- **Results:**
  - **Passed:** 108
  - **Failed:** 0
  - **Pass Rate:** 100%
  - **Duration:** 86.41 seconds
  - **Integrity Note:** Zero test code inspected prior to execution.

---

## Phase 1 Implementation & Test Summary

### 1. Test Suite Verification
- **Unit and Integration Suite (`tests/`)**:
  - Command:
    ```powershell
    $tempDb = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), "test_iot_unit_$([System.Guid]::NewGuid().ToString('N')).db")
    $env:DB_PATH = $tempDb
    python -m pytest tests/ -q
    ```
  - Result: 137 passed, 1 warning in 60.36s.
  - Pass Rate: 100% (137/137 passed).
- **Milestone 1 E2E Test Suite (`e2e_tests/test_tier1_features/test_area01_*.py` through `test_area04_*.py`)**:
  - Command:
    ```powershell
    $tempDb = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), "test_iot_e2e_$([System.Guid]::NewGuid().ToString('N')).db")
    $env:DB_PATH = $tempDb
    python -m pytest e2e_tests/test_tier1_features/test_area01_api_contracts.py e2e_tests/test_tier1_features/test_area02_websocket.py e2e_tests/test_tier1_features/test_area03_replay_lifecycle.py e2e_tests/test_tier1_features/test_area04_network_security.py -v
    ```
  - Result: 21 passed in 3.85s.
  - Pass Rate: 100% (21/21 passed).

### 2. Verified Feature Deliverables
- **Feature 1 (Git Baseline & Progress)**: Baseline git state recorded, environment package versions pinned, `docs/PROGRESS.md` maintained.
- **Feature 2 (OpenAPI & API Documentation Parity)**: OpenAPI 3.1 specification exported to `docs/openapi.json` with 34 active paths; `docs/API.md` aligned with real live server response payloads and full REST/WS coverage.
- **Feature 3 (Schema Hardening & Error Uniformity)**: `model_config = ConfigDict(extra="forbid")` enforced across all client models; centralized error handler returns structured JSON `{"detail": ...}` without stack traces or path disclosures.
- **Feature 4 (WebSocket Decoupling)**: Separated `/ws/client` (public, client-safe metrics, monotonic timestamps) and `/ws/admin` (HMAC token protected, code 1008 rejection, diagnostics); non-blocking per-connection queue (`maxsize=100`) with drop-oldest overflow policy.
- **Feature 5 (Deterministic Replay & Persistence)**: Original dataset timestamps preserved during simulation; all samples and detected events persisted to SQLite; sensitivity preset updates synchronized across detector and inference services.
- **Feature 6 (CORS Localhost Confinement)**: Strict regex confinement allowing only localhost/127.0.0.1 origins while rejecting external domains and DNS spoofing attempts.
- **Feature 7 (Frontend Contract Alignment)**: `ClientStatusResponse` incorporates `offline_time`, `is_stale`, and `stale_text`, matching `frontend/src/views/ClientView.jsx`.

---

## Budget Depletion Emergency Fallback
*(Maintained per Hard Rule: If context/budget limit is approached, record current state before halting)*
- **Current Phase:** Phase 1 (API Contract & Integration)
- **Status:** COMPLETED / PASS (Ready for Phase 2: Reliability & Fault Injection)
- **Files Created/Modified:** `backend/schemas/client_schemas.py`, `backend/routes/client_routes.py`, `backend/routes/ws_routes.py`, `backend/routes/admin_routes.py`, `backend/app.py`, `backend/config.py`, `backend/database.py`, `backend/services/events_service.py`, `backend/services/serial_service.py`, `docs/openapi.json`, `docs/API.md`, `docs/PROGRESS.md`.
- **Next Step:** Phase 2 (Reliability & Fault Injection) — Implement FakeSerial test double, verify SQLite WAL mode and busy timeout, retention purge, graceful shutdown, and `/api/health`.

---

## STEP A - Repository Cleanup (COMPLETED)
**Date:** 2026-11-15
- **git status count:** 109 → 106 (after .gitignore update)
- **git ls-files .agents .agent:** 0 (as expected)
- **.gitignore updated with:** .agents/, .agent/, skills-lock.json, auditor_run_report.json, .env, *.db, data/uploads/, logs/, node_modules/, .agents/teamwork/
- **Missing files (not moved to archive/misc):** AGENTS.md, .opencode/skills/iot-client-ui/SKILL.md
- **Untracked files categorized:**
  - Project files: TEST_INFRA.md (also tasks.md, THIRD_PARTY.md, requirements-web.txt, .env.example, run_ui.py are tracked)
  - Stray root files: HANDOFF.md, iot-client-ui_SKILL.md, project-rules.md
  - Tool scratch: archive/, backend/logging_config.py, backend/schemas/health_schemas.py, backend/services/fake_serial.py, backend/services/inference_service.py, backend/shutdown.py, data/*, docs/*, e2e_tests/, frontend/*, scripts/*, tests/*
- **Commit:** 1cf9d37 "Repository cleanup"

## STEP B - Verify and Save (COMPLETED)
**Date:** 2026-11-15
- **Branch:** hardening (switched/created)
- **Test suite results:**
  - Unit tests: 75 passed, 1 warning
  - E2E tests: 140 passed, 29 failed (failures listed in KNOWN_ISSUES.md)
- **Database tracking:** *.db confirmed untracked
- **Web server verification:** "/" serves client page (200 OK), "/admin" serves same SPA index (200 OK), "/api/health" returns status
- **Regression tests added (tests/test_regression.py):**
  1. Two replays of test_data_with_labels.csv create exactly 1 event total (deduplication works)
  2. Missing model -> /api/health says "degraded" with "Missing model artifacts"
  3. Corrupt model -> /api/health says "degraded" with "Corrupt model artifact"
  4. Degraded model -> /api/client/status headline = "Detector unavailable" (never "The room is normal")
  5. InferenceService returns "Detector unavailable" status when degraded
- **Code fixes:**
  - inference_service.py: returns "Detector unavailable" status when degraded
  - client_routes.py: checks is_degraded, returns "Detector unavailable" headline
  - ws_routes.py: broadcasts raw_frame status when not NORMAL/ANOMALY
- **Commit:** 5182305 "Verified state and regression tests"

## STEP C - Evaluation Protocol (COMPLETED)
**Date:** 2026-11-15
- **docs/evaluation_protocol.md**: Complete protocol with dataset table, rules, metrics, robustness tests
- **results/freeze.json**: SHA256 of models/*, feature code, thresholds.json, commit hash (92a4ae6)
- **Local tag**: eval-freeze created
- **evaluate/run_all.py**: Verifies freeze hashes, regenerates all evaluations, outputs JSON/CSV/MD
- **Results generated**: 39 model-dataset combinations across test, pilot (both label sets), eval_suite, UCI, IoTsec, v1 baseline, sensitivity levels
- **Key findings documented**:
  - Pilot is Development data (labels expanded 46→504 post-hoc)
  - Synthetic eval_suite tuned (0.25th %ile = -0.21657)
  - IoTsec: 470 FP, Precision=0.509 due to cross-domain shift
  - Test/pilot overlap: 35 identical rows (22:02:14–22:03:23)
  - v1 vs v2 comparison included
- **docs/MODEL_CARD.md**: Model card with limitations
- **docs/DATASHEET.md**: Dataset card with provenance, UNKNOWN items flagged
- **Commit**: a4939c1 "Evaluation protocol, freeze and run_all"
