# Client UI Refinement Log

This log documents the iterative refinement passes for the client-facing page of the AI-Based IoT Sensor Anomaly Detection system, adhering to the physical "Digital Thermohygrograph" instrument metaphor, strict design rules, and verification requirements.

---

## Area A — Charts and Graphics

### Concrete Numbered Critique of Area A Defects (Prior to Changes)

1. **Strip Chart Panel Geometry & Gap Asymmetry (Measurement: 14.16 px difference, 30 px gap vs 8 px spec)**:
   - *Element*: `ClientStripChart.jsx:47-48, 64-72`, `StripChartGrid.jsx:39`.
   - *Defect*: Fixed `height: 360` with `chartSplitY = innerHeight * 0.52 = 158.08 px` creates a temperature panel height of 144.08 px and a humidity panel height of 129.92 px (an asymmetry of 14.16 px). The separation gap is `(chartSplitY + 16) - (chartSplitY - 14) = 30.0 px` instead of the mandated 8 px. No responsive panel height (~150 px desktop, 140 px mobile) is provided, and a single monolithic background rect is drawn.
2. **Trace Stroke Weight (+0.25 px excess)**:
   - *Element*: `StripChartGrid.jsx:99-100`.
   - *Defect*: Trace paths use `strokeWidth="1.75"` instead of the required 1.5 px weight.
3. **Integer Y-Axis Domain Bounds with Rigid Artificial Clamping**:
   - *Element*: `ClientStripChart.jsx:62-72`.
   - *Defect*: Domain bounds are rounded with `Math.floor` / `Math.ceil` to whole integer values (1 °C and 1 %) and artificially clamped to rigid intervals `[18, 30]` and `[25, 70]`. When unconstrained, domains lack 0.5 °C and 5 % rounding and lack a noise guard minimum span, causing quiet steady rooms to autoscale to sensor noise.
4. **Uniform Grid Rulings Lacking 15-Minute Minor Lines and Hierarchy**:
   - *Element*: `StripChartGrid.jsx:40-51`.
   - *Defect*: Grid rulings are generated from generic D3 ticks with identical dashed styling (`strokeDasharray="2,2"`). Thermohygrograph paper rulings require prominent hourly major grid lines and distinct 15-minute minor grid lines at lower opacity.
5. **Omission of Calendar Date on Day Changes / Midnight Crossing**:
   - *Element*: `StripChartGrid.jsx:123-131`.
   - *Defect*: All time ticks are rendered strictly as `HH:MM`. Midnight crossings (00:00) and day changes omit the date string (e.g. "15 Nov"), making multi-hour/multi-day navigation ambiguous.
6. **Missing Direct Line-End Labels with Collision Avoidance**:
   - *Element*: `StripChartGrid.jsx:103-108`.
   - *Defect*: Only static unit symbols (`°C` and `% RH`) are rendered at `innerWidth + 8`. Direct reading value labels showing the latest reading at line ends are absent, and no vertical collision avoidance exists.
7. **Data Gaps > 10 s Rendered as Continuous Joined Lines**:
   - *Element*: `ClientStripChart.jsx:74-75`.
   - *Defect*: D3 paths interpolate uninterrupted monotone curves across missing intervals. Sensor dropouts > 10 s are drawn as continuous lines rather than breaks with light diagonal hatching.
8. **Unusual Event Bands Lack Darker Top Edge and Numbered Format**:
   - *Element*: `ClientStripChart.jsx:128`, `StripChartGrid.jsx:81-96`.
   - *Defect*: Band label renders as `"Event 1"` rather than `"#1"`, clipping on narrow bands. Shaded bands lack a darker top edge line (`#7A4B00`).
9. **Statically Docked Hover Badge Instead of Synchronized Floating Tooltip**:
   - *Element*: `ClientStripChart.jsx:180-186`.
   - *Defect*: Reading badge is statically anchored at `top: 8px; right: 8px`. The tooltip does not accompany the crosshair, forcing users to glance away from the scrubbed position.
10. **Absence of Keyboard Scrubbing and Static ARIA Description**:
    - *Element*: `ClientStripChart.jsx:134-188`, `StripChartGrid.jsx:28-36`.
    - *Defect*: SVG container lacks `tabIndex={0}` and keyboard handlers. Pressing Left/Right arrow keys does not scrub readings. Accessible label is static and omits range, min/max, latest values, and scrubbing instructions.
11. **Absence of Min-Max Downsampling for 6 h and All Ranges**:
    - *Element*: `ClientStripChart.jsx:32-42`.
    - *Defect*: All raw readings are passed directly to D3 path generation, risking visual decimation of narrow 20-second anomaly spikes over wide time windows.
12. **Room Map Non-Square Aspect Ratio (8.1% distortion)**:
    - *Element*: `RoomMap.jsx:8-12, 76`.
    - *Defect*: Inner plot area is 270 px wide by 292 px high ($1 : 1.0815$), and outer SVG is $340 \times 360\text{ px}$. Violates the mandated 1:1 square plot requirement.
13. **Room Map Rigid Domain Clamping vs Noise Guard (16 °C × 55 % RH span)**:
    - *Element*: `RoomMap.jsx:40-41`.
    - *Defect*: Rigid clamping to at least $[18, 34]\text{ °C}$ (16 °C span) and $[25, 80]\text{ % RH}$ (55 % span) crushes steady room dynamics into an indistinguishable dot cluster (3.75% of canvas width). Missing adaptive minimum visible span of 2 °C by 10 % RH with 0.5 °C / 5 % rounding.
14. **Room Map Visual Hierarchy, Labels, and Caption Defects**:
    - *Element*: `RoomMap.jsx:119-161`.
    - *Defect*: History dots are oversized (3 px diameter vs 2 px spec) and too opaque (80% vs 25% spec); trajectory trail is dashed 1.25 px instead of 1.5 px continuous; "Now" dot lacks an adjacent text label; unusual readings lack straw anomaly ring; caption is truncated to `"Where the room has been"` instead of verbatim `"Where the room has been: last 6 hours, last 30 minutes, now"`; font sizes violate the sub-13px rule (e.g. 10 px, 11 px, 12 px).

### Changes Implemented

- **Area**: Area A — Charts and Graphics
- **Screenshots**:
  - Before: `docs/screenshots/refine_before_A_1440.png`, `docs/screenshots/refine_before_A_390.png`
  - After: `docs/screenshots/refine_after_A_1440.png`, `docs/screenshots/refine_after_A_390.png`

| # | Defect Addressed | Concrete Change | File Modified |
|---|------------------|-----------------|---------------|
| 1 | Defect 1 (Asymmetric panels & 30 px gap) | Replaced single monolithic background with two discrete panels of equal height (150 px desktop, 140 px mobile) separated by an exact 8 px gap with shared time axis along bottom. | `frontend/src/components/ClientStripChart.jsx`, `frontend/src/components/StripChartGrid.jsx` |
| 2 | Defect 2 (1.75 px trace stroke weight) | Standardized trace paths to strictly `strokeWidth="1.5"` for temperature (`#9B2C2C`) and humidity (`#1D5C8C`) with zero line markers along paths. | `frontend/src/components/StripChartGrid.jsx` |
| 3 | Defect 3 (Integer Y-axis domain clamping) | Implemented domain calculation rounding to 0.5 °C and 5 % RH with 8% dynamic padding and noise guard minimum spans (3.0 °C and 15 % RH) preventing bit-noise autoscaling. | `frontend/src/components/ClientStripChart.jsx` |
| 4 | Defect 4 (Uniform grid rulings) | Implemented prominent hourly major grid rulings (`opacity 0.8`) and distinct 15-minute minor grid rulings (`opacity 0.35`) recreating thermohygrograph paper rulings. | `frontend/src/components/StripChartGrid.jsx` |
| 5 | Defect 5 (Missing date on day changes) | Time axis formats 24-hour time (`HH:MM`); conditionally displays calendar date (e.g. `15 Nov`) at midnight crossings (`00:00`) or day boundaries. | `frontend/src/components/StripChartGrid.jsx` |
| 6 | Defect 6 (Missing line-end direct labels) | Added direct latest reading labels (`26.2 °C` in oxblood, `59% RH` in navy) at trace right endpoints with guaranteed collision-avoidance coordinate clamping. | `frontend/src/components/StripChartGrid.jsx` |
| 7 | Defect 7 (Continuous paths across data gaps >10s) | Partitioned readings at $\Delta t > 10\text{ s}$ intervals on the raw reading stream into distinct sub-paths; filled true gap regions with light diagonal hatching pattern (`#data-gap-hatch`); immune to false gap artifacts on continuous downsampled streams. | `frontend/src/components/ClientStripChart.jsx`, `frontend/src/components/StripChartGrid.jsx` |
| 8 | Defect 8 (Unusual band formatting) | Formatted unusual event bands with event numbers (`#1`), straw yellow tint (`rgba(232, 176, 74, 0.35)`), and darker top edge ruling (`#7A4B00`, strokeWidth 2). | `frontend/src/components/StripChartGrid.jsx` |
| 9 | Defect 9 (Statically docked hover badge) | Replaced top-right docked badge with synchronized vertical crosshair across both panels, simultaneous trace dots, and floating tooltip moving with hover/keyboard scrub. | `frontend/src/components/StripChartGrid.jsx` |
| 10 | Defect 10 (Keyboard navigation & static ARIA) | Added container `tabIndex={0}`, `role="region"`, arrow key scrubbing (`ArrowLeft`, `ArrowRight`, `Home`, `End`), and dynamic `aria-label` summarizing range, bounds, and latest values. | `frontend/src/components/ClientStripChart.jsx` |
| 11 | Defect 11 (Missing downsampling on wide ranges) | Implemented `downsampleMinMax` bucket algorithm for 6 h and All ranges tracking temperature and humidity extrema independently with deduplication and chronological ordering, unconditionally preserving narrow transient anomaly spikes and trace contours. | `frontend/src/components/ClientStripChart.jsx` |
| 12 | Defect 12 (Room map 8.1% non-square distortion) | Enforced strictly 1:1 square plotting area ($270 \times 270\text{ px}$) within a balanced $340 \times 340\text{ px}$ SVG viewBox and 52/18 px margins. | `frontend/src/components/RoomMap.jsx` |
| 13 | Defect 13 (Room map rigid 16 °C / 55 % clamping) | Replaced static clamps with adaptive noise guard enforcing minimum visible span of 2.0 °C by 10.0 % RH with 0.5 °C / 5 % step rounding. | `frontend/src/components/RoomMap.jsx` |
| 14 | Defect 14 (Room map hierarchy, caption, typography) | Reduced history dots to 2 px diameter at 25% opacity; converted trail to 1.5 px continuous path; added "Now" 6 px filled dot with Atkinson 13px label; added straw unusual rings; restored verbatim caption `"Where the room has been: last 6 hours, last 30 minutes, now"`; upgraded all font sizes to $\ge 13\text{ px}$. | `frontend/src/components/RoomMap.jsx` |

### Visual Comparison Summary (Before vs After)

1. **Dual Panel Layout**: Before, the chart was a single tall box with unequal panels and a wide 30 px gap. After, two cleanly separated 150 px panels with an 8 px gap and a shared time axis create an authentic thermohygrograph instrument look.
2. **Direct Line-End Labels**: Before, only static `°C` and `% RH` headers sat in the margin. After, direct dynamic values (`26.2 °C` and `59% RH`) sit right at the trace endpoints, completely legible in greyscale.
3. **Data Gaps & Bands**: Anomaly bands now display concise `#1` numbering with a crisp dark top edge; missing data intervals are broken and hatched rather than falsely joined.
4. **Room Map**: The room map is now perfectly square (1:1), features faint historical dots with a prominent continuous 30-minute trail, an explicit "Now" label, and the complete required caption.
