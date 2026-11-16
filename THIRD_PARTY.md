# Third-Party Dependencies and Licensing

This document acknowledges third-party open-source software libraries, datasets, and typefaces incorporated into the AI-Based IoT Sensor Anomaly Detection system.

## 1. Typefaces

- **Literata**
  - Creator: TypeTogether (commissioned by Google)
  - License: SIL Open Font License, Version 1.1 (OFL-1.1)
  - Usage: Client UI primary status headline and numerals. Self-hosted via `@fontsource/literata`.

- **Atkinson Hyperlegible**
  - Creator: Braille Institute of America & Applied Design Works
  - License: SIL Open Font License, Version 1.1 (OFL-1.1)
  - Usage: Client UI body copy, data tables, and axis annotations. Optimized for low-vision legibility with distinct character shapes. Self-hosted via `@fontsource/atkinson-hyperlegible`.

---

## 2. Frontend Libraries

- **React & React-DOM** (v19)
  - Creator: Meta Platforms, Inc.
  - License: MIT License
  - Role: Declarative component rendering for SPA.

- **D3 Modular Packages** (`d3-array`, `d3-scale`, `d3-shape`, `d3-axis`)
  - Creator: Mike Bostock and D3 contributors
  - License: ISC License
  - Role: Mathematical scale projections, continuous line curve generation, and tick geometry calculation.

- **Vite & Tailwind CSS**
  - License: MIT License
  - Role: Local development server, asset bundler, and utility styling.

---

## 3. Backend & Machine Learning Libraries

- **FastAPI & Starlette**
  - Creator: Sebastián Ramírez
  - License: MIT License
  - Role: High-performance asynchronous REST API framework and WebSocket routing.

- **Uvicorn**
  - Creator: Encode OSS Ltd
  - License: BSD-3-Clause
  - Role: ASGI web server implementation.

- **Scikit-Learn**
  - Creator: Scikit-learn developers
  - License: BSD-3-Clause
  - Role: Isolation Forest algorithm and StandardScaler implementation.

- **Pandas & NumPy**
  - License: BSD-3-Clause
  - Role: In-memory tabular time-series feature engineering and vector computation.

- **PySerial**
  - Creator: Chris Liechti
  - License: BSD-3-Clause
  - Role: Hardware serial COM port reader for microcontroller telemetry.

- **ItsDangerous**
  - Creator: Pallets
  - License: BSD-3-Clause
  - Role: Cryptographic HMAC token signing for administrator session management.

---

## 4. Benchmark Datasets

- **UCI Occupancy Detection Dataset (#357)**
  - Authors: Luis M. Candanedo, Véronique Feldheim (University of Mons)
  - License: Creative Commons Attribution 4.0 International (CC BY 4.0)
  - Citation: Candanedo, L. M., & Feldheim, V. (2016). Accurate occupancy detection of an office room from light, temperature, humidity and CO2 measurements using statistical learning models. Energy and Buildings, 112, 28-39.

- **IoTsec Environmental Telemetry Benchmark**
  - Role: External room climate baseline shift validation.
