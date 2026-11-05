#!/usr/bin/env python3
"""
Build the master notebook from the three validated component notebooks.
"""

import json
import nbformat
from pathlib import Path

# Load the three validated notebooks
notebooks = [
    ("eda", "eda/notebooks/01_eda.ipynb"),
    ("preprocess", "preprocess/notebooks/02_data_preprocessing.ipynb"),
    ("features", "features/notebooks/03_feature_engineering.ipynb"),
]

all_cells = []

for name, path in notebooks:
    print(f"Loading {name} from {path}...")
    with open(path, 'r', encoding='utf-8') as f:
        nb = nbformat.read(f, as_version=4)
    print(f"  {len(nb.cells)} cells loaded")
    
    # Add a section header
    if name == "eda":
        all_cells.append(nbformat.v4.new_markdown_cell("## SECTION 3: Exploratory Data Analysis (EDA)\n\n### What is EDA and Why Do We Need It?\n\n**EDA (Exploratory Data Analysis)** is the process of understanding your data before modeling. It answers:\n- What does \"normal\" look like? (central tendency, spread, range)\n- Are there obvious problems? (missing values, duplicates, impossible values)\n- What do anomalies look like? (sudden spikes, impossible combinations)\n- Are there data quality issues? (gaps, duplicates, sensor errors)\n\n### Key Python Functions We'll Use\n- `df.describe()` - computes count, mean, std, min, quartiles, max\n- `df.quantile([0.25, 0.5, 0.75])` - explicit quartile calculation\n- `df.var()` - variance\n- `df.isnull().sum()` - missing values per column\n- `df.duplicated().sum()` - exact duplicate rows\n- `df['timestamp'].diff().dt.total_seconds()` - time difference between consecutive rows\n- `value_counts()` - frequency of each unique value\n\n### Statistical Concepts\n- **Mean** - average value\n- **Median** - middle value (robust to outliers)\n- **Standard Deviation (Std)** - how spread out the data is\n- **IQR (Interquartile Range)** = Q3 - Q1, middle 50% spread\n- **IQR Fences** - outliers are below Q1-1.5×IQR or above Q3+1.5×IQR\n- **Z-Score** = (value - mean) / std, measures how many standard deviations from mean\n  - |z| > 3 typically considered outlier (assumes Gaussian)"))
    all_cells.extend(nb.cells)
    
    elif name == "preprocess":
        # Add section header before preprocessing cells
        all_cells.append(nbformat.v4.new_markdown_cell("## SECTION 4: Data Preprocessing and Cleaning\n\n### Key Concept: Data Cleaning\nReal-world sensor data is messy. We need to:\n1. **Handle missing/invalid values** - but DHT11 gives 0 missing, we just flag out-of-range\n2. **Remove exact duplicates** - identical rows add no information, bias training\n3. **Handle repeated timestamps** - same timestamp, different readings (logging bug)\n4. **Handle timestamp gaps** - don't interpolate across large gaps\n5. **Flag suspicious observations** - don't auto-delete, document for review\n\n### Critical: Preserve Original Data\n**Never modify original CSV files in `data/raw/`.** Always save cleaned versions to `data/processed/`."))
    all_cells.extend(nb.cells)
    
    elif name == "features":
        all_cells.append(nbformat.v4.new_markdown_cell("## SECTION 5: Feature Engineering\n\n### What is Feature Engineering?\n\n**Feature engineering** is the process of creating new, more informative features from your raw data. The goal is to help the machine learning model detect patterns it couldn't see with just the raw numbers.\n\n### What is a Feature?\nA **feature** is a measurable property or characteristic of your data that you feed into a machine learning model. Think of features as the \"ingredients\" the model uses to make predictions.\n\nIn our IoT sensor project:\n- **Raw features** (directly from sensor): `temperature` (°C), `humidity` (% RH)\n- These are the two numbers the DHT11 sensor gives us every 2 seconds\n\n### What is Feature Engineering?\n**Feature engineering** is the process of creating new, more informative features from your raw data. The goal is to help the machine learning model detect patterns it couldn't see with just the raw numbers.\n\nExample: If temperature suddenly jumps from 25°C to 35°C in 2 seconds, that's unusual. The raw `temperature` value (35) alone doesn't tell you it was a sudden jump. But a `temperature_change` feature (= 10) makes the jump obvious to the model.\n\n### Why Do ML Models Need Useful Features?\n- Models like Isolation Forest look for observations that are \"different\" from the majority\n- Raw sensor values only tell you the current state, not the **context** (trend, stability, rate of change)\n- Engineered features add context: \"Is this reading part of a trend?\", \"How much did it change from the last reading?\", \"Is the sensor currently stable or volatile?\"\n- Better features = better anomaly detection\n\n### Raw vs Engineered Features\n\n| Raw Features | Engineered Features |\n|--------------|---------------------|\n| `temperature` | `temperature_change` (difference from previous reading) |\n| `humidity` | `humidity_abs_change` (magnitude of change, ignoring direction) |\n| | `temperature_rolling_mean_5` (average of last 5 readings) |\n| | `humidity_rolling_std_15` (variability of last 15 readings) |\n\n### Our Feature Strategy\n1. **Change features** (4): Capture sudden jumps between consecutive readings\n2. **Rolling statistical features** (10): Capture recent baseline/trend and volatility\n3. **Gap-aware rolling**: Never calculate statistics across recording gaps (>10 seconds)\n\n### Window Sizes\n- **5 observations** = short-term trend (~10 seconds if regular 2s sampling)\n- **15 observations** = medium-term trend (~30 seconds if regular 2s sampling)\n\n⚠️ **Important:** We do NOT describe windows as exact seconds because our data has repeated timestamps and gaps. \"5 observations\" is not exactly 10 seconds. We describe the window size in **observations**, not time.\n\n### Key Concept: Difference Features\nChange features capture **how much a sensor reading changed from the previous reading**. This helps detect sudden jumps.\n- `temperature_change` = current_temperature - previous_temperature\n- `humidity_change` = current_humidity - previous_humidity\n- **Positive** = increase, **Negative** = decrease\n- `temperature_abs_change` = absolute value of temperature_change\n- `humidity_abs_change` = absolute value of humidity_change\n- **Absolute change** ignores direction, only cares about magnitude\n\n**Example:** If temperature goes 25 → 30 → 28:\n- Row 0: change = NaN (no previous)\n- Row 1: change = 30 - 25 = +5\n- Row 2: change = 28 - 30 = -2\n- Row 1 abs_change = 5, Row 2 abs_change = 2\n\n**Pandas Function: `.diff()`**\n- `df['col'].diff()` computes current - previous for each row\n- First row has no previous, so result is `NaN` (missing)\n- `.abs()` converts negative values to positive\n\n### Key Concept: Rolling Window Features\nRolling features look at a **window of recent readings** and compute statistics. This tells the model about recent sensor behavior.\n- **Rolling mean** = average of last N readings\n  - If current reading is far from rolling mean, it might be anomalous\n- **Rolling standard deviation** = how variable the last N readings are\n  - High std = sensor is volatile/unstable\n  - Low std = sensor is stable\n\n### Window Sizes\n- **5 observations** = short-term trend (~10 seconds if regular 2s sampling)\n- **15 observations** = medium-term trend (~30 seconds if regular 2s sampling)\n\n⚠️ **Important:** We do NOT describe windows as exact seconds because our data has repeated timestamps and gaps. \"5 observations\" is not exactly 10 seconds. We describe the window size in **observations**, not time.\n\n### Pandas Function: `.rolling(window=N).mean()` / `.std()`\n- `df['col'].rolling(window=5).mean()` computes mean of current + previous 4 rows\n- First N-1 rows have NaN (not enough data for full window)\n- By default, `min_periods=None` means all N values must be present; we keep default to be conservative\n\n### Gap Handling\nLater we will handle timestamp gaps (>10 seconds) by resetting rolling windows. This ensures statistics never cross recording gaps."))
    all_cells.extend(nb.cells)

# Add section 0, 1, 2 headers and utility functions
header_cells = [
    nbformat.v4.new_markdown_cell("""# IoT Sensor Anomaly Detection - Master Notebook

**Project:** AI-Based IoT Sensor Anomaly Detection  
**Sensor:** ESP32 + DHT11 (GPIO 4)  
**Sampling:** 2000 ms interval  
**Communication:** USB Serial @ 115200 baud  
**Deployment:** Windows PC - Python handles ML inference & dashboard  

---

## SECTION 0: Project Overview & Learning Objectives

### Project Goal
Build an end-to-end anomaly detection system for temperature and humidity sensor data. The system will:
1. Collect data from ESP32 + DHT11 via serial communication
2. Clean and preprocess the sensor data
3. Engineer meaningful features for anomaly detection
4. Train an Isolation Forest model on normal data only
5. Detect anomalies in real-time with a monitoring dashboard

### What You'll Learn
- **Data loading & validation** - Handle real-world sensor data with missing headers, duplicates, and gaps
- **Exploratory Data Analysis (EDA)** - Understand distributions, detect outliers, visualize time series
- **Data cleaning** - Remove exact duplicates, handle timestamp gaps, flag suspicious readings
- **Feature engineering** - Create change features, rolling statistics, session-aware rolling windows
- **Anomaly detection** - Isolation Forest (unsupervised, trains on normal data only)
- **Model evaluation** - Precision, Recall, F1 on labeled test set

### Dataset Summary
| Dataset | Rows | Purpose |
|---------|------|---------|
| `normal_data.csv` | 36,798 | Candidate training data (normal only, after cleaning) |
| `pilot_data.csv` | 3,087 | Validation data with 2 real anomaly events |
| `test.csv` + `test_labels.csv` | 42 (36 normal, 6 anomaly) | Hold-out test set (never used for training) |

**Important:** The `normal_data.csv` has a higher humidity baseline (~62%) than pilot/test (~59-60%). This **dataset shift** means a model trained on normal_data may not generalize to deployment conditions matching pilot/test. We'll document this clearly.

---

## SECTION 1: Imports and Configuration
"""),
    nbformat.v4.new_code_cell("""# Standard libraries
import json
import warnings
from pathlib import Path
from datetime import datetime

# Data science stack
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# ML
from sklearn.ensemble import IsolationForest
from sklearn.metrics import classification_report, confusion_matrix

# Configuration
import yaml

# Plot styling
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette('husl')

# Suppress harmless warnings
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning, module='nbformat')

print("Imports successful!")
print(f"pandas: {pd.__version__}")
print(f"numpy: {np.__version__}")
print(f"matplotlib: {plt.matplotlib.__version__}")
print(f"seaborn: {sns.__version__}")
print(f"scikit-learn: {__import__('sklearn').__version__}")"""),
    nbformat.v4.new_code_cell("""# Load configuration from YAML
config_path = Path("config.yaml")
if config_path.exists():
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    print("Configuration loaded from config.yaml")
else:
    # Fallback defaults
    config = {
        "serial": {"port": "COM19", "baudrate": 115200, "timeout": 1.0, "sampling_interval_ms": 2000},
        "data": {"raw_dir": "data/raw", "processed_dir": "data/processed", "features_dir": "data/processed/features"},
        "features": {"rolling_windows": [5, 15], "gap_threshold_seconds": 10},
        "model": {"type": "isolation_forest", "n_estimators": 200, "contamination": 0.01, "random_state": 42}
    }
    print("Using default configuration")

# Convenience variables
RAW_DIR = Path(config["data"]["raw_dir"])
PROCESSED_DIR = Path(config["data"]["processed_dir"])
FEATURES_DIR = Path(config["data"]["features_dir"])
GAP_THRESHOLD = config["features"]["gap_threshold_seconds"]
ROLLING_WINDOWS = config["features"]["rolling_windows"]

print(f"Raw data directory: {RAW_DIR}")
print(f"Processed data directory: {PROCESSED_DIR}")
print(f"Features directory: {FEATURES_DIR}")
print(f"Gap threshold: {GAP_THRESHOLD} seconds")
print(f"Rolling windows: {ROLLING_WINDOWS} observations")"""),
    nbformat.v4.new_markdown_cell("""## SECTION 2: Load Original Datasets

### Key Concept: Reading CSV Files
- **`pd.read_csv()`** reads a CSV file into a DataFrame
- By default, it assumes the **first row is the header** (column names)
- If your file has **no header**, use `header=None` and provide names with `names=[...]`
- The **original files in `data/raw/` are never modified** — we only read them

### Our Files:
- `normal_data.csv` — **NO header** (first row is data)
- `pilot_data.csv` — HAS header
- `test.csv` — HAS header
- `test_labels.csv` — HAS header (event-level label, not row-level)
"""),
    nbformat.v4.new_code_cell("""def load_datasets():
    \"\"\"
    Load all four raw datasets from data/raw/.
    Returns a dictionary with DataFrames for each dataset.
    \"\"\"
    print("=== Loading Raw Datasets ===")

    # normal_data.csv has NO header - first row is data
    normal = pd.read_csv(
        RAW_DIR / "normal_data.csv",
        header=None,                    # No header in file
        names=["timestamp", "temperature", "humidity"]  # Provide column names
    )

    # The other files HAVE headers
    pilot = pd.read_csv(RAW_DIR / "pilot_data.csv")
    test = pd.read_csv(RAW_DIR / "test.csv")
    test_labels = pd.read_csv(RAW_DIR / "test_labels.csv")

    # Convert timestamps to datetime
    for df in [normal, pilot, test]:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    test_labels["start"] = pd.to_datetime(test_labels["start"])
    test_labels["end"] = pd.to_datetime(test_labels["end"])

    # Sort chronologically (stable sort preserves original order for equal timestamps)
    normal = normal.sort_values("timestamp", kind="stable").reset_index(drop=True)
    pilot = pilot.sort_values("timestamp", kind="stable").reset_index(drop=True)
    test = test.sort_values("timestamp", kind="stable").reset_index(drop=True)

    # Quick verification
    print(f"Normal: {len(normal)} rows, {normal['timestamp'].min()} to {normal['timestamp'].max()}")
    print(f"Pilot:  {len(pilot)} rows, {pilot['timestamp'].min()} to {pilot['timestamp'].max()}")
    print(f"Test:   {len(test)} rows, {test['timestamp'].min()} to {test['timestamp'].max()}")
    print(f"Labels: {len(test_labels)} rows")
    print(test_labels)

    return {"normal": normal, "pilot": pilot, "test": test, "test_labels": test_labels}

# Load all datasets
datasets = load_datasets()
normal = datasets["normal"]
pilot = datasets["pilot"]
test = datasets["test"]
test_labels = datasets["test_labels"]"""),
]

# Add all cells from the three notebooks
for cell in all_cells:
    # Only include code and markdown cells
    if cell.cell_type in ('code', 'markdown'):
        header_cells.append(cell)

# Create the master notebook
master_nb = nbformat.v4.new_notebook()
master_nb.cells = header_cells

# Write the master notebook
output_path = Path("notebooks/iot_anomaly_detection.ipynb")
with open(output_path, 'w', encoding='utf-8') as f:
    nbformat.write(master_nb, f)

print(f"Master notebook created at {output_path}")
print(f"Total cells: {len(master_nb.cells)}")

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
""")