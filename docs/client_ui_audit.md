# Client UI Audit: Elements on Current Page vs Customer Requirements

## Purpose
Audit every element currently rendered on the root route (`/`) against the three fundamental customer questions defined in `iot-client-ui`:
1. **Is everything normal?**
2. **What is the temperature and humidity right now?**
3. **Did anything unusual happen?**

Any element that does not directly inform one of these three customer questions does not belong on the customer-facing client page.

---

## Element-by-Element Audit

| # | Current UI Element | Content / Display | Customer Decision Supported | Action | Target Location |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | **Brand Badge** | `AetherSense v2.0 • ESP32 + DHT11 Anomaly Hub` | None (invented brand name causes academic discrepancy) | **DELETE** | Retire; use exact title *"AI-Based IoT Sensor Anomaly Detection"* |
| 2 | **Sidebar Navigation** | 4-item tab menu (`System Cockpit`, `Live Telemetry`, `Dataset Evaluation`, `Tuning & Alerts`) | None (customer needs a focused single-view dashboard without navigation) | **DELETE** (from client) | Admin page only (`/admin`) |
| 3 | **Sidebar Node Status Ticker** | `WS Socket ONLINE`, `Node Port COM10`, `Stream State STANDBY` | None (internal hardware/socket connection details) | **MOVE-TO-ADMIN** | Admin Live Monitor |
| 4 | **Top Bar Title** | `System Cockpit` with `0.5 Hz Cadence` badge | None (technical sensor sampling cadence) | **DELETE** (from client) | Admin Overview |
| 5 | **Top Bar Hardware Actions** | Buttons: `Live ESP32`, `Simulate Replay`, `Halt Stream` | Hardware control; customer does not operate serial ports | **MOVE-TO-ADMIN** | Admin Live Monitor |
| 6 | **Hero Category Pill** | `Unsupervised Environmental Anomaly Intelligence` | None (marketing/AI buzzword) | **DELETE** | Eliminated entirely |
| 7 | **Hero Headline** | `AI-Driven Indoor Climate Telemetry & Anomaly Detection` | Informs room status, but formatted as pitch title | **REPLACE** | Replace with active headline sentence: *"The room is normal."* or *"Unusual reading at HH:MM:..."* |
| 8 | **Hero Subtitle Copy** | Technical text explaining Cauchy EWMA, Isolation Forest, drift resilience | None (algorithmic explanation) | **MOVE-TO-ADMIN** | Admin Overview / Architecture |
| 9 | **Hero CTA Buttons** | `Launch Live Monitor`, `Inspect Evaluation Datasets`, `Calibrate Thresholds` | Technical navigation | **MOVE-TO-ADMIN** | Admin Navigation |
| 10 | **KPI Card 1: Hardware Node** | `COM10`, `DTR/RTS Safe`, `ESP32 @ 115,200 baud` | None (low-level serial hardware configuration) | **MOVE-TO-ADMIN** | Admin Live Monitor |
| 11 | **KPI Card 2: Clean Baseline** | `34,374`, `12 Features`, `9 sessions (< Nov 1, 2026)` | None (training dataset composition) | **MOVE-TO-ADMIN** | Admin Datasets |
| 12 | **KPI Card 3: Pilot F1** | `93.2%`, `0 FP`, `0 false alarms on 2,581 normal rows` | None (model benchmark metrics) | **MOVE-TO-ADMIN** | Admin Evaluation (with 4-label audit notes) |
| 13 | **KPI Card 4: Eval Suite F1** | `96.8%`, `0/57 Live FP`, `6/6 synthetic fault categories` | None (model benchmark metrics) | **MOVE-TO-ADMIN** | Admin Evaluation |
| 14 | **Division of Labor: Isolation Forest** | Details on 200 iTrees, high-frequency transients, persistence filter | None (algorithmic division of labor) | **MOVE-TO-ADMIN** | Admin Architecture / Model Details |
| 15 | **Division of Labor: Cauchy EWMA** | 2,400s half-life baseline, rate gating, 3.5σ cutoff | None (statistical tuning parameters) | **MOVE-TO-ADMIN** | Admin Architecture / Settings |
| 16 | **Logical Union Callout** | "Maintains 0 false alarms on warm ambient baseline drift days..." | Unsubstantiated "zero false alarms" claim | **DELETE / MOVE-TO-ADMIN** | Tone down and move to Admin Evaluation |
| 17 | **Stream Replay Panel** | 3 launcher buttons: `Replay 6-Fault`, `Replay Pilot`, `Replay Test` | Test simulation trigger | **MOVE-TO-ADMIN** | Admin Live Monitor |
| 18 | **Hardware Pinout Specs** | ESP32-WROOM-32, GPIO 4 (DHT11 Data), 115,200 baud | None (electrical engineering wiring spec) | **MOVE-TO-ADMIN** | Admin Overview / Docs |
| 19 | **Dark Mode & Styling** | Pitch-black void (`#08090d`), card borders, glowing tags | Distracting visual kit that reads as "AI template" | **DELETE** (from client) | Client page strictly uses light digital thermohygrograph design |
| 20 | **Student Attribution Footer** | Pinned in sidebar: `Dungu Avinash Reddy Roll: 12509090` | Identifies student work | **KEEP & REFORMAT** | Render once in standard footer: *"Dungu Avinash Reddy \| Roll RK3P25KZA09 \| Reg. 12509090"* |

---

## Approved Customer-Facing Elements to Build on `/`
Per `iot-client-ui`, the client page shall contain **only**:
1. **Title line**: *"AI-Based IoT Sensor Anomaly Detection"* + small status dot (*Live*, *Simulated*, or *Offline*) + timestamp of last reading.
2. **Headline sentence**: e.g., *"The room is normal."* or *"Unusual reading at 22:03: temperature rose 8 °C for about 20 seconds."*
3. **Current readings line**: e.g., *"Current reading: 26.0 °C, 60.7% RH at 22:03:15."*
4. **Digital Strip Chart (`ClientStripChart`)**: Temperature (#9B2C2C) and Humidity (#1D5C8C) dual-ink trace on gridded paper (#EEF1EF / #CBD5D0), unusual periods shaded in straw yellow (#E8B04A at 35%), hover crosshairs, range buttons (`15 min`, `1 h`, `6 h`, `All`).
5. **Room Map (`RoomMap`)**: Phase space ($T$ vs $H$), last 6 hours as faint dots, last 30 minutes as connected trail, now as filled dot. Caption: *"Where the room has been"*.
6. **Log of Unusual Readings (`UnusualLog`)**: Event #, Start, Duration, What changed, Peak Temp, Peak Hum, Severity. Clean toggle *"How severity is decided"*.
7. **Institutional Footer**: *"Dungu Avinash Reddy | Roll RK3P25KZA09 | Reg. 12509090"*.
