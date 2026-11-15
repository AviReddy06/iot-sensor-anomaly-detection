# E2E Test Infrastructure & Methodology Specification

## 1. Testing Philosophy

The End-to-End (E2E) Test Suite for the "AI-Based IoT Sensor Anomaly Detection" system is designed as an **opaque-box, requirement-driven, and contract-verifying** validation framework.

### Core Principles:
1. **Opaque-Box Boundary**: All assertions evaluate exclusively public HTTP endpoints, WebSocket frame streams, CLI return codes, and filesystem artifacts. No private module attributes, private methods, or internal variables are inspected.
2. **Ephemeral Isolation**: No test ever touches the production database (`data/iot_anomaly.db`) or production model artifacts (`models/`). Each test run provisions an ephemeral temporary SQLite database via `DB_PATH`, isolated upload folders, and temporary logs. Database files are initialized, migrated, and discarded automatically.
3. **Requirement Fidelity**: Every test case traces directly to an explicit requirement in `ORIGINAL_REQUEST.md` (R1 through R9). Expected outcomes are derived from authoritative specifications, mathematical definitions (e.g. Z-score, isolation forest decision functions), and documented interface contracts.
4. **Honest & Non-Destructive Execution**: Facade tests that unconditionally pass without exercising real logic are strictly forbidden. When the backend or frontend implementation exhibits a defect or missing feature, the test fails genuinely and documents the failure honestly.
5. **Multi-Tiered Hierarchy**: Tests are structured into four progressive tiers:
   - **Tier 1 (Feature Coverage)**: Happy-path validation for all 13 core feature areas.
   - **Tier 2 (Boundary & Corner Cases)**: Input constraints, malformed schemas, rate limits, timeouts, and fault injection.
   - **Tier 3 (Cross-Feature Combinations)**: Pairwise interactions between security, concurrency, streaming, and data lifecycles.
   - **Tier 4 (Real-World Scenarios)**: Multi-step holistic workflows simulating operators, hardware failures, security attacks, and long-term soak.

---

## 2. Feature Inventory Matrix (13 Feature Areas)

| Area # | Feature Area | Primary Requirement | Mapped Capabilities | Scope Description |
|---|---|---|---|---|
| **Area 1** | API Contracts & Schema Integrity | R2 | F2, F3 | REST route schemas, status codes (200, 401, 403, 404, 422, 503), `extra="forbid"`, uniform error responses |
| **Area 2** | WebSocket Streaming & Monotonicity | R2 | F4 | `/ws/client` monotonic timestamps, client-safe fields, `/ws/admin` auth, drop-oldest bounded queue, client isolation |
| **Area 3** | Deterministic Simulation Replay & Event Lifecycle | R2 | F5 | `test_data_with_labels.csv` replay (1 High event at 2026-10-27 22:03:29), sensitivity updates, audit log round-trip |
| **Area 4** | Network Security, CORS & CSP Headers | R2, R4 | F6, F15 | Localhost-only CORS rejection, Content-Security-Policy ('self' only), X-Content-Type-Options: nosniff, Referrer-Policy |
| **Area 5** | Serial Ingestion, FakeSerial & Faults | R3, R7 | F8, F22 | 0.5Hz normal, malformed, NaN, temp==humidity 30 readings flag, 100/s burst, 60s offline detection, reconnect backoff |
| **Area 6** | Health & Admin Metrics Endpoints | R3 | F9, F11 | `/api/health` schema, degraded status on missing/corrupt model, startup refusal on feature mismatch, `/api/admin/metrics` |
| **Area 7** | SQLite Concurrency & Data Retention | R3 | F10 | WAL mode, busy timeout 5000ms, timestamp indexes, 50 readers + 1 writer 60s zero lock, 30-day retention purge |
| **Area 8** | Auth Hardening, Brute-Force & Secrecy | R4 | F12 | Token expiry, tampered token rejection, 6th failed login 429, constant time compare, unset password 503, password secrecy |
| **Area 9** | Admin Uploads, Path Traversal & Escaping | R4 | F13, F14 | 5MB upload limit, CSV header/content check, server-generated names, path traversal rejection (`../`), formula injection escape (`=,+,-,@`) |
| **Area 10** | Performance Targets & Soak Verification | R5 | F17, F18 | REST p95 <150ms, WS delivery p95 <1s, ingest burst 0 loss, 7-day history query p95 <200ms, soak stability |
| **Area 11** | ML Evaluation Protocol & Code Freeze | R6 | F19, F20, F21 | `docs/evaluation_protocol.md` compliance, freeze SHA256 hashes, `evaluate/run_all.py` reproducibility, bootstrap 95% CIs |
| **Area 12** | Frontend DOM Hygiene & Offline Font Delivery | R2, R8 | F7, F23, F24 | 17 banned ML terms absence in client DOM, offline font delivery, zero external CDN requests, status banners |
| **Area 13** | Preflight, Operational Readiness & Secrets | R1, R9 | F1, F16, F25, F26 | Preflight verification (`preflight.ps1`), clean git tracking, secret scanning in tracked history, CI checks |

---

## 3. Test Architecture & Directory Layout

The complete E2E testing framework resides within the `e2e_tests/` root package:

```
e2e_tests/
├── __init__.py                     # Package marker
├── conftest.py                     # Ephemeral test fixtures, TestClient, WS harness, temp DB
├── runner.py                       # Standalone CLI test runner and report generator
├── test_tier1_features/            # Tier 1: Feature Coverage (>=65 tests across Areas 1-13)
│   ├── test_area01_api_contracts.py
│   ├── test_area02_websocket.py
│   ├── test_area03_replay_lifecycle.py
│   ├── test_area04_network_security.py
│   ├── test_area05_serial_ingest.py
│   ├── test_area06_health_metrics.py
│   ├── test_area07_sqlite_retention.py
│   ├── test_area08_auth_hardening.py
│   ├── test_area09_uploads_traversal.py
│   ├── test_area10_performance.py
│   ├── test_area11_ml_protocol.py
│   ├── test_area12_dom_hygiene.py
│   └── test_area13_preflight_secrets.py
├── test_tier2_boundaries/          # Tier 2: Boundary & Corner Cases (>=65 tests across Areas 1-13)
│   ├── test_area01_boundary.py
│   ├── test_area02_boundary.py
│   ├── test_area03_boundary.py
│   ├── test_area04_boundary.py
│   ├── test_area05_boundary.py
│   ├── test_area06_boundary.py
│   ├── test_area07_boundary.py
│   ├── test_area08_boundary.py
│   ├── test_area09_boundary.py
│   ├── test_area10_boundary.py
│   ├── test_area11_boundary.py
│   ├── test_area12_boundary.py
│   └── test_area13_boundary.py
├── test_tier3_cross_features/      # Tier 3: Pairwise Cross-Feature Interactions (22 tests)
│   ├── test_cross_security_uploads.py
│   ├── test_cross_streaming_concurrency.py
│   ├── test_cross_faults_lifecycle.py
│   └── test_cross_admin_inference.py
└── test_tier4_scenarios/           # Tier 4: Real-World Scenarios (8 full workflows)
    ├── test_scenario1_baseline_replay.py
    ├── test_scenario2_operator_workflow.py
    ├── test_scenario3_sensor_disconnect.py
    ├── test_scenario4_adversarial_attack.py
    ├── test_scenario5_burst_concurrency.py
    ├── test_scenario6_model_recovery.py
    ├── test_scenario7_preflight_demo.py
    └── test_scenario8_soak_retention.py
```

---

## 4. Ephemeral Test Harness (`conftest.py`)

All tests interface with the FastAPI application using ephemeral fixtures:
- **`ephemeral_env`**: Creates an isolated temporary directory for SQLite (`DB_PATH`), uploaded datasets, and export files. Patches environment variables before backend initialization and restores them on teardown.
- **`test_db`**: Directly verifies SQLite table initialization, WAL mode (`PRAGMA journal_mode = WAL`), and busy timeout (`PRAGMA busy_timeout = 5000`).
- **`client`**: FastAPI `TestClient` initialized with `app`, supporting full HTTP verb routing, cookies, headers, and simulated remote IP addresses.
- **`ws_client`**: Synchronous and asynchronous WebSocket test harness for `/ws/client` and `/ws/admin`, allowing inspection of frames, drop handling, and disconnect behavior.
- **`admin_token`**: Factory fixture issuing signed HMAC-SHA256 tokens configured with custom expiration timestamps for happy and negative path testing.

---

## 5. Coverage and Quality Thresholds

| Metric | Target / Threshold | Authoritative Source | Verification Method |
|---|---|---|---|
| **Tier 1 Feature Coverage** | >= 65 tests (>= 5 per area) | SCOPE.md | `runner.py --tier 1` |
| **Tier 2 Boundary Coverage** | >= 65 tests (>= 5 per area) | SCOPE.md | `runner.py --tier 2` |
| **Tier 3 Cross-Feature Tests** | 22 pairwise tests | Explorer 3 Handoff | `runner.py --tier 3` |
| **Tier 4 Scenario Tests** | 8 complete workflows | Explorer 3 Handoff | `runner.py --tier 4` |
| **REST Latency p95** | < 150 ms (0 errors) | ORIGINAL_REQUEST.md R5 | Async concurrency harness |
| **WS Frame Delivery p95** | < 1.0 s | ORIGINAL_REQUEST.md R5 | WebSocket timestamp diff |
| **Ingest Burst Loss** | 0 lost readings | ORIGINAL_REQUEST.md R5 | Telemetry count comparison |
| **Client DOM Term Ban** | 0 occurrences of 17 terms | ORIGINAL_REQUEST.md R8 | Playwright / HTML DOM audit |
| **Failed Login Lockout** | 429 on 6th attempt / min | ORIGINAL_REQUEST.md R4 | HTTP auth rate limit tests |
| **Upload Size Boundary** | 5 MB max (5,242,880 bytes) | ORIGINAL_REQUEST.md R4 | Multipart payload tests |

---

## 6. How to Run the Tests

### Standalone Runner
```powershell
# Run all tiers with formatted report:
python e2e_tests/runner.py

# Run specific tiers:
python e2e_tests/runner.py --tier 1
python e2e_tests/runner.py --tier 1,2
python e2e_tests/runner.py --tier 3,4

# Run with JSON report output:
python e2e_tests/runner.py --json report.json

# Run including heavy soak / large history tests:
python e2e_tests/runner.py --run-slow
```

### Direct Pytest Invocations
```powershell
# Run full E2E suite:
pytest e2e_tests/

# Run by tier:
pytest e2e_tests/test_tier1_features/
pytest e2e_tests/test_tier2_boundaries/
pytest e2e_tests/test_tier3_cross_features/
pytest e2e_tests/test_tier4_scenarios/

# Run single test module:
pytest e2e_tests/test_tier1_features/test_area01_api_contracts.py -v
```

---

## 7. Master Reconciliation & Failure Honesty Baseline

Under Demo Mode integrity requirements (`ORIGINAL_REQUEST.md`), test outcomes must reflect genuine system behavior. Missing or incomplete features on parallel milestone tracks are tested authentically and reported as honest failures without dummy assertions, tautologies, or `@pytest.mark.xfail` masks.

### Execution Baseline:
- **Total Test Cases**: Exactly **169 tests**
- **Passing Tests**: Exactly **132 tests** (verifying completed M1 contracts, SQLite WAL, replay inference, auth tokens, and DOM purity)
- **Honest Failures**: Exactly **37 tests** mapped to parallel milestone deliverables:
  - **Milestone M2 (Reliability & Faults)**: 15 failures (`/api/admin/metrics`, 60s stream silence timeout, 30-reading temp==hum fault flag, corrupted model degraded mode, access log token redaction, retention purge routine).
  - **Milestone M3 (Security Hardening)**: 9 failures (CSP 'self' header, nosniff, referrer-policy, WebSocket cross-origin rejection, 5MB upload boundary, CSV header 422 rejection, path traversal rejection, formula injection escaping).
  - **Milestone M5 (ML Evaluation & Freeze)**: 7 failures (`results/freeze.json`, `scripts/hardware_check.py`, `evaluate/run_all.py` robustness & random control tables, `docs/MODEL_CARD.md`, `docs/DATASHEET.md`).
  - **Milestone M6 (Preflight & CI)**: 6 failures (`scripts/preflight.ps1` validation, `.github/workflows/ci.yml`).
