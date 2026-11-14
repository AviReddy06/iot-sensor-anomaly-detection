# Design Specification & Anti-Generic Audit ("Digital Thermohygrograph")

## 1. Design Direction: The Digital Thermohygrograph

The design eschews standard generic SaaS/AI dashboard tropes in favor of an authentic scientific instrument aesthetic inspired by classic mechanical thermohygrographs (continuous dual-pen drum recorders on gridded chart paper).

### Principles & Purpose
- **Grounding in Subject Matter**: A thermohygrograph records indoor ambient climate via two continuous capillary ink pens on ruled paper. The visual language borrows this physical metaphor directly: paper background, hairline graph ruling, oxblood red temperature trace, navy blue relative humidity trace, and soft straw-yellow highlighting for unusual intervals.
- **Customer Focus**: Designed exclusively for a room manager answering three questions:
  1. *Is everything normal?*
  2. *What is the temperature and humidity now?*
  3. *Did anything unusual happen?*
- **Above-the-Fold at 1440x900**: Header, active status, headline sentence, current readings, and the initial segment of the continuous dual-trace strip chart are immediately visible without scrolling.
- **Spend Boldness in One Place**: The strip chart and room map carry the visual interest. Every other element is quiet, clean, and understated.

---

## 2. Review Against Generic AI Defaults & Avoid-List

| Generic Default / AI Trope (from `frontend-design` & `iot-client-ui`) | Status in Design | What Was Changed and Why |
| :--- | :--- | :--- |
| **Near-black background with neon accent (cyberpunk/hacker look)** | **BANNED** | Replaced with light chart paper (`#EEF1EF`), dark ink text (`#1C2A33`), and scientific grid hairlines (`#CBD5D0`). |
| **Row of four KPI cards with icon tiles and big numbers** | **BANNED** | Replaced by a single Literata headline sentence and a clean reading line. |
| **Identical rounded cards with soft box-shadows** | **BANNED** | Strict square corners (`border-radius: 0px`). Zero drop shadows (only a 2px high-contrast keyboard focus ring). |
| **Gradient fills, glow blurs, glassmorphism (`backdrop-filter`)** | **BANNED** | Solid opaque paper surfaces. Zero blurs, glows, or gradients anywhere in CSS. |
| **Tracked-out ALL-CAPS labels & monospace tags** | **BANNED** | Strict sentence case throughout. Natural letter spacing. Monospace reserved for code; Atkinson Hyperlegible with `tabular-nums` used for data. |
| **`A · B · C` meta strings & spaced em-dash labels** | **BANNED** | Standard punctuation and plain grammatical English. |
| **`→` arrows appended to button text** | **BANNED** | Clean, concise verb buttons (e.g. `15 min`, `1 h`, `6 h`, `All`). |
| **Numbered markers on non-sequential items (01 / 02 / 03)** | **BANNED** | Numbers used strictly for sequential incident indices matching intervals on the strip chart. |
| **Emoji, invented brand names, marketing buzzwords** | **BANNED** | No "AetherSense", no "System Cockpit", no "AI-driven", no "zero false alarms". Title is strictly *"AI-Based IoT Sensor Anomaly Detection"*. |
| **Client DOM ML jargon leakage** | **BANNED** | Zero occurrences in client DOM of: `isolation`, `forest`, `score`, `threshold`, `z-score`, `precision`, `recall`, `f1`, `confusion`, `ewma`, `hardware`, `serial`, `websocket`, `port`, `baud`, `model`, `cockpit`. |

---

## 3. Token Definitions

### Color Palette (Light Theme & Print Media)
All tokens mathematically calculated and verified via ITU-R BT.709 relative luminance against screen paper background (`#EEF1EF`, Luminance = 0.873) and print paper (`#FFFFFF`, Luminance = 1.000):

| Token Name | Hex Value | Purpose / Role | Contrast vs Paper (`#EEF1EF`) | Contrast vs Print (`#FFFFFF`) | WCAG 2.1 Compliance |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `--color-paper` | `#EEF1EF` | Continuous chart paper canvas | 1.00 : 1 | — | Canvas baseline |
| `--color-print-paper` | `#FFFFFF` | Print media paper (A4 vector) | — | 1.00 : 1 | Print baseline |
| `--color-grid` | `#CBD5D0` | Structural chart grid rulings | 1.32 : 1 | 1.50 : 1 | Hairline grid (decorative SC 1.4.11) |
| `--color-ink` | `#1C2A33` | Primary text, titles, borders | **12.93 : 1** | **14.70 : 1** | PASS (AAA text, AAA non-text) |
| `--color-muted` | `#4F5F69` | Secondary captions, axis ticks, time | **5.82 : 1** | **6.62 : 1** | PASS (AA text >= 4.5:1) |
| `--color-temp` | `#9B2C2C` | Temperature ink trace and peak values | **6.62 : 1** | **7.53 : 1** | PASS (AA text, non-text >= 3:1) |
| `--color-hum` | `#1D5C8C` | Relative humidity ink trace | **6.23 : 1** | **7.09 : 1** | PASS (AA text, non-text >= 3:1) |
| `--color-band` | `rgba(232, 176, 74, 0.35)` | Straw yellow highlighting band on strip | 1.21 : 1 (composite) | Hatch vector | Supplemented by top edge line |
| `--color-band-top`| `#7A4B00` | Incident band top edge and hairlines | **6.52 : 1** | **7.41 : 1** | PASS (non-text >= 3:1) |
| `--color-band-text`| `#7A4B00` | Incident band label text (`#1`) | **5.39 : 1** (over band) | **7.41 : 1** | PASS (AA text >= 4.5:1) |
| `--color-normal` | `#28704A` | Normal status dot & comfort target | **5.27 : 1** | **6.00 : 1** | PASS (AA text, non-text >= 3:1) |
| `--pattern-print-hatch` | `url(#unusual-band-hatch)` | Diagonal vector hatching in print mode | High contrast ink | 45° vector lines | Monochrome printable |

### Typography
- **Headline Font**: *Literata* (self-hosted via `@fontsource/literata`, weights 400 and 500).
  - Desktop size: `36px` to `40px`, line-height `1.2`. Mobile size: `26px` to `28px`.
  - Used strictly for the primary headline sentence summarizing room status.
- **Interface & Body Font**: *Atkinson Hyperlegible* (self-hosted via `@fontsource/atkinson-hyperlegible`, weights 400 and 700).
  - Body size: `16px`, line-height `1.5`, maximum line length `< 70ch`.
  - Small labels: `13px` to `14px` (nothing below 13px).
  - Numerical display: `font-variant-numeric: tabular-nums` for rock-solid vertical alignment.

### Geometry & Focus
- Strict square corners (`border-radius: 0px`) across all charts, frames, tables, and buttons.
- Keyboard accessibility: `outline: 2px solid var(--color-ink); outline-offset: 2px;`.
- Spacing scale: `4px`, `8px`, `12px`, `16px`, `24px`, `32px`, `48px`, `64px`.

### Motion
- Exactly one non-interactive moment: the two pen traces draw from left to right over `700ms` on first load (`stroke-dashoffset`).
- All interactive actions (hover crosshairs, range selection) respond in `< 150ms`.
- Respects `@media (prefers-reduced-motion: reduce)` by disabling the intro draw animation.

---

## 4. Layout Wireframes (ASCII)

### Desktop Wireframe (1440px / Max Width 1120px, Left-Aligned)
```
+---------------------------------------------------------------------------------+
| AI-Based IoT Sensor Anomaly Detection                     [• Live] 11:32:04     |
|                                                                                 |
| The room is normal.                                                             |
| Current reading: 24.2 °C, 58.4% RH at 11:32:04.                                 |
|                                                                                 |
| +-----------------------------------------------+ +---------------------------+ |
| | Dual-Trace Strip Chart (62%)                  | | Room Map (34%)            | |
| | [15 min] [1 h] [6 h] [All]                    | |                           | |
| | +-------------------------------------------+ | | +-----------------------+ | |
| | | 30°C ----------------- (Temp trace)       | | | | H                     | | |
| | | 20°C ------------------------------------ | | | | u                     | | |
| | |                                           | | | | m   • (now)           | | |
| | | 80%  ================= (Hum trace)        | | | | i  / (trail)          | | |
| | | 40%  ==================================== | | | | d : : (faint dots)    | | |
| | +-------------------------------------------+ | | +-----------------------+ | |
| |                                               | | Where the room has been   | |
| +-----------------------------------------------+ +---------------------------+ |
|                                                                                 |
| Unusual readings log                                                            |
| +-------+----------+----------+-----------------------+-----------+----------+  |
| | Event | Start    | Duration | What changed          | Peak Temp | Peak Hum |  |
| +-------+----------+----------+-----------------------+-----------+----------+  |
| | 1     | 22:03:29 | 24 s     | Temp rose 8.5 °C      | 34.2 °C   | 82.1%    |  |
| +-------+----------+----------+-----------------------+-----------+----------+  |
|                                                                                 |
| Dungu Avinash Reddy | Roll RK3P25KZA09 | Reg. 12509090                          |
+---------------------------------------------------------------------------------+
```

### Mobile Wireframe (390px)
```
+---------------------------------------+
| AI-Based IoT Sensor Anomaly Detection |
| [• Live] 11:32:04                     |
|                                       |
| The room is normal.                   |
| Current reading: 24.2 °C, 58.4% RH.   |
|                                       |
| Dual-Trace Strip Chart                |
| [15m] [1h] [6h] [All]                 |
| +-----------------------------------+ |
| | Paper grid with traces            | |
| +-----------------------------------+ |
|                                       |
| Room Map                              |
| +-----------------------------------+ |
| | Phase space (Temp vs Hum)         | |
| +-----------------------------------+ |
| Where the room has been               |
|                                       |
| Unusual readings log                  |
| +-----------------------------------+ |
| | Event 1: Temp rose 8.5 °C at 22:03| |
| +-----------------------------------+ |
|                                       |
| Dungu Avinash Reddy                   |
| Roll RK3P25KZA09 | Reg. 12509090     |
+---------------------------------------+
```

---

## 6. Screenshot Critique and Revision Pass

### Visual Inspection Findings (docs/screenshots/client_final_*.png)
1. **The One Memorable Element**:
   The physical thermohygrograph metaphor—continuous dual-pen ink traces (`#9B2C2C` oxblood temperature and `#1D5C8C` navy relative humidity) plotted directly across cream-colored ruling paper (`#EEF1EF`), paired with the 2D temperature-humidity phase-space map ("Where the room has been") and warm straw-yellow event highlights (`rgba(232, 176, 74, 0.35)`). It reads immediately as an authentic environmental laboratory instrument rather than generic software.

2. **What a Customer Might Misunderstand**:
   - *Severity Criteria*: Customers reviewing event logs might wonder how "Low", "Medium", and "High" severity levels are assigned without ML jargon. An accessible disclosure toggle ("How severity is decided") was built directly into the log header to explain excursion magnitude and duration in plain English.
   - *Mobile Column Densities*: On a 390px mobile viewport, rendering seven distinct event columns without horizontal overflow leads to cramped text wrapping. A clean `min-w-[640px]` scrollable container was established to preserve legibility.

3. **What Looked Like a Template & Was Prevented**:
   - Zero rounded card containers (`rounded-none` throughout).
   - Zero drop-shadows or glow halos (replaced with clean 1px `#CBD5D0` grid borders and 2px high-contrast keyboard focus outlines).
   - Zero neon status indicators or dark glassmorphic backgrounds.
   - Zero uppercase tracking on labels.

4. **Revisions Applied (Area A, B, D passes)**:
   - In `RoomMap.jsx`: Increased left chart margin to 50px and repositioned the Y-axis label `Humidity (% RH)` to `y="-36"` to eliminate visual crowding against numerical tick marks; removed `opacity="0.65"` on comfort target text raising contrast to 5.27:1.
   - In `UnusualLog.jsx`: Enforced `min-w-[640px]` on the table layout inside its horizontal scroll frame, ensuring table cells remain spacious across mobile screens; replaced bordered pill badges with pure typographic ink.
   - Rebuilt production bundle and regenerated screenshots at 1440px, 768px, and 390px. All checks pass.

---

## 7. Area C Written Reflection & Accessibility Audit (Requirement R4)

### 7.1 Reflection Questions & Decisions

#### Question 1: What is the one memorable element?
> **Answer**:  
> The single memorable element is the **continuous dual-pen capillary ink recording across cream chart paper**—the oxblood red (`#9B2C2C`) temperature trace and navy blue (`#1D5C8C`) humidity trace drawn over charcoal rulings (`#CBD5D0`), anchored by direct line-end reading labels (`26.2\u2009°C` and `58.6\u2009% RH`) that travel dynamically at the right margin without overlapping. Paired with the square 1:1 phase-space room map ("Where the room has been") tracking a 30-minute ink trajectory, this pairing decisively anchors the digital thermohygrograph metaphor. It does not feel like an abstract SaaS analytics dashboard; it presents as an authentic physical drum recorder. Boldness is concentrated entirely in these continuous ink paths, allowing all surrounding layout and type to remain quiet, austere, and disciplined.

#### Question 2: What would you remove ("remove one accessory")?
> **Answer**:  
> Following Chanel’s advice to "take a look in the mirror and remove one accessory," we removed the **continuous looping CSS `animate-ping` radar pulse on the Live status dot** in `ClientView.jsx`. While intended to signal live telemetry, an infinite pulsing radar ring introduces continuous non-interactive motion that directly violates the core motion covenant: *"Motion: exactly one non-interactive moment, the two traces drawing left to right once on first load (700 ms). Everything else answers a user action in 150 ms."* A physical laboratory instrument does not pulse; it records steadily. Stripping this ping away removes visual chatter and restores calm, dignified instrument stillness. (Additionally, hardcoded pipe separators `|` in the status header and tooltip were stripped in favor of typographic whitespace).

#### Question 3: Is anything still generic, and what is the specific "one last revision"?
> **Answer**:  
> The severity indicator column in `UnusualLog.jsx` still carried the tell of a generic web template: severity ("High", "Medium", "Low") was rendered as an enclosed rectangular chip badge with a 1px border and a tinted pill fill (`border border-[#7A4B00] bg-[rgba(232,176,74,0.25)]`). Enclosed chip badges are a ubiquitous trope of modern dashboard kits.  
> **The One Last Revision**:  
> We stripped away the enclosing border box and pill background on severity values in `UnusualLog.jsx`. Severity is now rendered strictly as **pure typographic ink**: High and Medium in bold amber (`#7A4B00`, Atkinson Hyperlegible 700), and Low in muted ink (`#4F5F69`, Atkinson Hyperlegible 400). This eliminated the final residual SaaS card-kit artifact and transformed the table into an authentic printed instrument logbook.

### 7.2 Print Stylesheet & High-Contrast Mode Specifications
- **Print Stylesheet (`@media print`)**: Enforces pure white paper (`#ffffff`) across all containers, removes interactive controls (`button`, `.print:hidden`, `a[href="/admin"]`), enforces `-webkit-print-color-adjust: exact`, and renders unusual event bands as vector diagonal hatching via SVG `<pattern id="unusual-band-hatch">`. Avoids page fragmentation using `break-inside: avoid`. Verified via Playwright PDF export to `docs/screenshots/client_print.pdf`.
- **Forced-Colors Mode (`@media (forced-colors: active)`)**: SVG presentation text renders as `CanvasText`, temperature trace as `Highlight`, humidity trace as `CanvasText` with dashed pattern (`4, 3`), and unusual bands retain high-contrast vector hatching. Active range button renders with `Highlight` bottom border.
- **Colorblindness & Greyscale Redundancy**: In greyscale (where oxblood and navy have identical luminance ~0.09), temperature and humidity are 100% distinguished by vertical panel segregation, explicit axis units (`°` vs `%`), direct endpoint labels with units (`°C` vs `% RH`), and crosshair tooltips. Status never relies on color alone; dots are always paired with explicit textual state ("Live", "Simulated", "Offline") and a subtle 1px structural outline.
