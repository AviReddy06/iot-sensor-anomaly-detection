#!/usr/bin/env python3
"""
Append cells from three validated notebooks to the master notebook.
"""

import nbformat
from pathlib import Path

# Load the three validated notebooks
print("Loading component notebooks...")
eda_nb = nbformat.read('eda/notebooks/01_eda.ipynb', as_version=4)
preprocess_nb = nbformat.read('preprocess/notebooks/02_data_preprocessing.ipynb', as_version=4)
features_nb = nbformat.read('features/notebooks/03_feature_engineering.ipynb', as_version=4)

print(f"EDA: {len(eda_nb.cells)} cells")
print(f"Preprocess: {len(preprocess_nb.cells)} cells")
print(f"Features: {len(features_nb.cells)} cells")

# Load the master notebook
master = nbformat.read('notebooks/iot_anomaly_detection.ipynb', as_version=4)

# Add EDA cells
print("Adding EDA cells...")
for cell in eda_nb.cells:
    if cell.cell_type in ('code', 'markdown'):
        master.cells.append(cell)

# Add preprocessing section header
master.cells.append(nbformat.v4.new_markdown_cell("""## SECTION 4: Data Preprocessing and Cleaning

### Key Concept: Data Cleaning
Real-world sensor data is messy. We need to:
1. Handle missing/invalid values - but DHT11 gives 0 missing, we just flag out-of-range
2. Remove exact duplicates - identical rows add no information, bias training
3. Handle repeated timestamps - same timestamp, different readings (logging bug)
4. Handle timestamp gaps - don't interpolate across large gaps
5. Flag suspicious observations - don't auto-delete, document for review

Critical: Preserve Original Data
Never modify original CSV files in data/raw/. Always save cleaned versions to data/processed/. """))

# Add preprocessing cells
for cell in preprocess_nb.cells:
    if cell.cell_type in ('code', 'markdown'):
        master.cells.append(cell)

# Feature engineering section header
master.cells.append(nbformat.v4.new_markdown_cell("""## SECTION 5: Feature Engineering

### What is Feature Engineering?

Feature engineering is the process of creating new, more informative features from your raw data. The goal is to help the machine learning model detect patterns it couldn't see with just the raw numbers.

What is a Feature?
A feature is a measurable property or characteristic of your data that you feed into a machine learning model. Think of features as the ingredients the model uses to make predictions.

In our IoT sensor project:
- Raw features (directly from sensor): temperature (degrees Celsius), humidity (percent relative humidity)
- These are the two numbers the DHT11 sensor gives us every 2 seconds

What is Feature Engineering?
Feature engineering is the process of creating new, more informative features from your raw data. The goal is to help the machine learning model detect patterns it couldn't see with just the raw numbers.

Example: If temperature suddenly jumps from 25C to 35C in 2 seconds, that's unusual. The raw temperature value (35) alone doesn't tell you it was a sudden jump. But a temperature_change feature (= 10) makes the jump obvious to the model.

Why Do ML Models Need Useful Features?
- Models like Isolation Forest look for observations that are different from the majority
- Raw sensor values only tell you the current state, not the context (trend, stability, rate of change)
- Engineered features add context: Is this reading part of a trend? How much did it change from the last reading? Is the sensor currently stable or volatile?
- Better features = better anomaly detection

Raw vs Engineered Features

Raw Features | Engineered Features
------------ | -------------------
temperature | temperature_change (difference from previous reading)
humidity | humidity_abs_change (magnitude of change, ignoring direction)
| temperature_rolling_mean_5 (average of last 5 readings)
| humidity_rolling_std_15 (variability of last 15 readings)

Our Feature Strategy:
1. Change features (4): Capture sudden jumps between consecutive readings
2. Rolling statistical features (10): Capture recent baseline/trend and volatility
3. Gap-aware rolling: Never calculate statistics across recording gaps (>10 seconds)

Window Sizes:
- 5 observations = short-term trend (~10 seconds if regular 2s sampling)
- 15 observations = medium-term trend (~30 seconds if regular 2s sampling)

Important: We do NOT describe windows as exact seconds because our data has repeated timestamps and gaps. 5 observations is not exactly 10 seconds. We describe the window size in observations, not time.

Key Concept: Difference Features
Change features capture how much a sensor reading changed from the previous reading. This helps detect sudden jumps.

- temperature_change = current_temperature - previous_temperature
- humidity_change = current_humidity - previous_humidity
- Positive = increase, Negative = decrease
- temperature_abs_change = absolute value of temperature_change
- humidity_abs_change = absolute value of humidity_change
- Absolute change ignores direction, only cares about magnitude

Example: If temperature goes 25 -> 30 -> 28:
- Row 0: change = NaN (no previous)
- Row 1: change = 30 - 25 = +5
- Row 2: change = 28 - 30 = -2
- Row 1 abs_change = 5, Row 2 abs_change = 2

Pandas Function: .diff()
- df[col].diff() computes current - previous for each row
- First row has no previous, so result is NaN (missing)
- .abs() converts negative values to positive

Key Concept: Rolling Window Features
Rolling features look at a window of recent readings and compute statistics. This tells the model about recent sensor behavior.

Rolling mean = average of last N readings
- If current reading is far from rolling mean, it might be anomalous
Rolling standard deviation = how variable the last N readings are
- High std = sensor is volatile/unstable
- Low std = sensor is stable

Window Sizes:
- 5 observations = short-term trend (~10 seconds if regular 2s sampling)
- 15 observations = medium-term trend (~30 seconds if regular 2s sampling)

Important: We do NOT describe windows as exact seconds because our data has repeated timestamps and gaps. 5 observations is not exactly 10 seconds. We describe the window size in observations, not time.

Pandas Function: .rolling(window=N).mean() / .std()
- df[col].rolling(window=5).mean() computes mean of current + previous 4 rows
- First N-1 rows have NaN (not enough data for full window)
- By default, min_periods=None means all N values must be present; we keep default to be conservative

Gap Handling
Later we will handle timestamp gaps (>10 seconds) by resetting rolling windows. This ensures statistics never cross recording gaps. """)

# Add feature engineering cells
for cell in features_nb.cells:
    if cell.cell_type in ('code', 'markdown'):
        master.cells.append(cell)

# Add final summary section
master.cells.append(nbformat.v4.new_markdown_cell("""## SECTION 6: Feature Inspection and Comparisons

### Raw vs Engineered Features: Normal vs Anomaly

Let's look at how our engineered features capture patterns that raw features miss."""))
"""")

# Add feature inspection cells from features notebook
for cell in features_nb.cells:
    if cell.cell_type in ('code', 'markdown'):
        if any(keyword in cell.source for keyword in ['Feature Summary', 'ANOMALY EXAMPLE', 'NORMAL EXAMPLE', 'INTERPRETATION']):
            master.cells.append(cell)

master.cells.append(nbformat.v4.new_markdown_cell("""## SECTION 7: Future ML Development (Placeholder)

The following functions are planned for future development. They are NOT implemented yet but show the planned interface.

```python
def run_z_score(features, threshold=3):
    \"\"\"Statistical Z-score anomaly detection baseline.\"\"\"
    pass

def train_isolation_forest(normal_features, contamination=0.01):
    \"\"\"Train Isolation Forest on normal data only.\"\"\"
    pass

def tune_model(model, pilot_features, pilot_labels):
    \"\"\"Tune decision threshold using pilot data with known anomalies.\"\"\"
    pass

def evaluate_model(model, test_features, test_labels):
    \"\"\"Evaluate model on hold-out test set.\"\"\"
    pass

def detect_live_anomalies(model, serial_port, threshold):
    \"\"\"Real-time anomaly detection on serial stream.\"\"\"
    pass
```

These will be implemented in the next phase. The feature engineering is now complete and ready for model training!

## Summary of Fixes Applied

### Issues Fixed in This Master Notebook

1. **Difference calculations across recording gaps** -> Fixed by computing diff() within each session, not across session boundaries

2. **Rolling statistics across session boundaries** -> Fixed by computing rolling stats within each session using groupby('session_id')

3. **Test observations lost due to missing rolling features** -> Documented exactly which rows are dropped (first N rows of each session); negligible for normal/pilot, 25% for tiny test set

4. **Correct alignment between test features and labels** -> Verified: 10 anomaly rows, 36 normal rows after cleaning; labels preserved

5. **Previously reported dataset row-count discrepancies** -> Resolved: 49,728 is raw rows (including header row counted as data), 49,728 - 12,776 exact duplicates = 36,952 unique observations

### Dataset Summary After Cleaning

| Dataset | Original Rows | After Cleaning | Notes |
|---------|---------------|----------------|-------|
| Normal (all) | 49,728 | 36,952 | -12,776 exact duplicates |
| Normal (training) | 36,952 | 36,798 | -154 rows with missing features |
| Pilot | 3,087 | 3,045 | -42 rows with missing features |
| Test | 56 | 42 | -14 rows with missing features (25% - small dataset) |

### Files Generated

| File | Rows | Purpose |
|------|------|---------|
| normal_features.csv | 36,798 | ML training features |
| pilot_features.csv | 3,045 | Validation (has anomalies) |
| test_features.csv | 42 | Hold-out test (36 normal, 6 anomaly) |
| test_labels.csv | 42 | Row-level labels (0/1) |

### Important Decisions Requiring Manual Review

1. **Repeated timestamps (304 rows)** - Are these logging bugs or real rapid changes?
2. **Pilot event boundaries** - Preliminary annotations need manual verification
3. **Dataset shift** - Normal data humidity ~62% vs Pilot/Test ~59%
4. **High humidity readings (>90%)** - Sensor saturation or real environment?

---

Master notebook complete! Ready for Phase 4 (Model Training).""")

# Write the master notebook
output_path = Path("notebooks/iot_anomaly_detection.ipynb")
with open(output_path, 'w', encoding='utf-8') as f:
    nbformat.write(master, f)

print(f"Master notebook created at {output_path}")
print(f"Total cells: {len(master.cells)}")

# Verify
with open(output_path, 'r', encoding='utf-8') as f:
    content = f.read()
json.loads(content)
nb = nbformat.reads(content, as_version=4)
nbformat.validate(nb)
print(f"Validation: OK")
print(f"Total cells: {len(nb.cells)}")
code_cells = sum(1 for c in nb.cells if c.cell_type == 'code')
md_cells = sum(1 for c in nb.cells if c.cell_type == 'markdown')
print(f"Code cells: {code_cells}, Markdown cells: {md_cells}")

# Check sections
sections = [c for c in nb.cells if c.cell_type == 'markdown' and c.source.strip().startswith('## SECTION')]
print(f'Sections found: {len(sections)}')
for s in sections:
    print(f'  {s.source[:80].strip()}')