# dashboard/app.py
# Beginner-friendly Streamlit app for IoT anomaly detection
# Sequential code, heavily commented

import streamlit as st
import pandas as pd
import numpy as np
import joblib
import json
from pathlib import Path
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support

# Import our feature building function
from feature_utils import build_features

# ============================================================
# PAGE CONFIGURATION
# ============================================================
st.set_page_config(
    page_title="AI-Based IoT Sensor Anomaly Detection",
    page_icon="🌡️",
    layout="wide"
)

# ============================================================
# HEADER
# ============================================================
st.title("AI-Based IoT Sensor Anomaly Detection")

st.markdown("""
This application detects anomalies in temperature and humidity sensor data from an ESP32 + DHT11 sensor.
It uses two methods: (1) a Z-score baseline on raw temperature/humidity, and (2) an Isolation Forest trained
on session-aware engineered features (change features and rolling statistics). The model was trained on
normal indoor data only (no anomalies). A change of environment (e.g., different humidity baseline) can
raise alerts. Evaluation used a 55-row test set with one injected event (10 anomaly rows), so metrics
are indicative only and cannot show generalisation.
""")

# Footer
st.markdown("---")
st.caption("Dungu Avinash Reddy | Roll RK3P25KZA09 | Reg. 12509090")

# ============================================================
# SIDEBAR: DATA SOURCE
# ============================================================
st.sidebar.header("Data Source")

use_sample = st.sidebar.checkbox("Use sample test data (test_data_with_labels.csv)", value=True)

uploaded_file = None
if not use_sample:
    uploaded_file = st.sidebar.file_uploader(
        "Upload CSV file",
        type=["csv"],
        help="File must have columns: timestamp, temperature, humidity. "
             "If exactly 3 columns and no header, it will be read with header=None."
    )

# ============================================================
# LOAD MODELS (cached)
# ============================================================
@st.cache_resource
def load_models():
    """Load Isolation Forest, scaler, and thresholds from disk."""
    iso = joblib.load('models/iforest.joblib')
    scaler = joblib.load('models/scaler.joblib')
    with open('models/thresholds.json', 'r') as f:
        thresholds = json.load(f)
    return iso, scaler, thresholds

iso, scaler, thresholds = load_models()

feature_cols = thresholds['feature_cols']
iforest_threshold = thresholds['iforest_threshold']
zscore_threshold = thresholds['zscore_threshold']
normal_temp_mean = thresholds['normal_temp_mean']
normal_temp_std = thresholds['normal_temp_std']
normal_hum_mean = thresholds['normal_hum_mean']
normal_hum_std = thresholds['normal_hum_std']
GAP_THRESHOLD = thresholds['GAP_THRESHOLD']
ROLL_MIN = thresholds['ROLL_MIN']

# ============================================================
# LOAD DATA
# ============================================================
def load_data(use_sample_data, uploaded_file):
    """Load data from sample file or uploaded file."""
    if use_sample_data:
        # Load sample test data
        try:
            df = pd.read_csv('data/processed/test_data_with_labels.csv')
            st.sidebar.success("Loaded sample test data (55 rows after feature building)")
            return df
        except FileNotFoundError:
            st.error("Sample file not found: data/processed/test_data_with_labels.csv")
            return None
    else:
        # Handle uploaded file
        if uploaded_file is None:
            st.sidebar.info("Please upload a CSV file.")
            return None
        
        if uploaded_file.size == 0:
            st.error("Uploaded file is empty.")
            return None
        
        try:
            # Try to read with header first
            df = pd.read_csv(uploaded_file)
        except Exception as e:
            st.error(f"Could not parse CSV: {e}")
            return None
        
        # Check columns
        cols = list(df.columns)
        
        # If exactly 3 columns and they look like data (not header names), 
        # or if first row looks like data, treat as no-header
        if len(cols) == 3:
            # Check if columns are the expected names
            if set(cols) == {'timestamp', 'temperature', 'humidity'}:
                pass  # Has correct header
            elif all(c.replace('.', '').replace('-', '').isdigit() or ':' in c for c in df.iloc[0].astype(str)):
                # First row looks like data - re-read with no header
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, header=None, 
                                 names=['timestamp', 'temperature', 'humidity'])
            else:
                # Maybe user has different column names
                st.warning(f"Columns found: {cols}. Expected: timestamp, temperature, humidity")
        elif len(cols) != 3:
            st.error(f"Expected 3 columns (timestamp, temperature, humidity), got {len(cols)}: {cols}")
            return None
        
        # Verify required columns exist
        required = ['timestamp', 'temperature', 'humidity']
        if not all(c in df.columns for c in required):
            st.error(f"Missing required columns. Need: {required}. Found: {cols}")
            return None
        
        st.sidebar.success(f"Loaded uploaded data: {len(df)} rows")
        return df

data = load_data(use_sample, uploaded_file)

if data is None:
    st.stop()

# ============================================================
# BUILD FEATURES
# ============================================================
with st.spinner("Building features..."):
    try:
        features_df = build_features(data, GAP_THRESHOLD, ROLL_MIN)
    except Exception as e:
        st.error(f"Feature building failed: {e}")
        st.stop()

st.success(f"Built features: {len(features_df)} rows (first row of each session dropped)")

# ============================================================
# SCALE AND SCORE
# ============================================================
# Separate features for scaling
X = features_df[feature_cols].copy()

# Scale
X_scaled = scaler.transform(X)

# Isolation Forest decision function (negative = more anomalous)
scores = iso.decision_function(X_scaled)
iforest_flag = scores < iforest_threshold

# Z-score flag on raw temperature and humidity
z_temp = np.abs((features_df['temperature'] - normal_temp_mean) / normal_temp_std)
z_hum = np.abs((features_df['humidity'] - normal_hum_mean) / normal_hum_std)
zscore_flag = (z_temp > zscore_threshold) | (z_hum > zscore_threshold)

# Add flags to dataframe
features_df['iforest_score'] = scores
features_df['iforest_anomaly'] = iforest_flag
features_df['zscore_anomaly'] = zscore_flag

# ============================================================
# METRIC CARDS
# ============================================================
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Rows Analysed", len(features_df))
with col2:
    st.metric("IF Anomalies", int(iforest_flag.sum()))
with col3:
    st.metric("Z-score Anomalies", int(zscore_flag.sum()))
with col4:
    # If labels exist, show recall
    if 'label' in features_df.columns:
        y_true = features_df['label'].values
        iforest_recall = (iforest_flag & (y_true == 1)).sum() / (y_true == 1).sum() if (y_true == 1).sum() > 0 else 0
        zscore_recall = (zscore_flag & (y_true == 1)).sum() / (y_true == 1).sum() if (y_true == 1).sum() > 0 else 0
        st.metric("IF Recall", f"{iforest_recall:.1%}")
    else:
        st.metric("IF Recall", "N/A (no labels)")

# ============================================================
# CHARTS
# ============================================================
st.subheader("Temperature & Humidity Over Time")

fig, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True)

# Temperature
axes[0].plot(features_df['timestamp'], features_df['temperature'], 'b-', alpha=0.7, label='Temperature')
if iforest_flag.any():
    axes[0].scatter(features_df.loc[iforest_flag, 'timestamp'],
                    features_df.loc[iforest_flag, 'temperature'],
                    color='red', s=30, zorder=5, label='IF Anomaly')
if zscore_flag.any():
    axes[0].scatter(features_df.loc[zscore_flag, 'timestamp'],
                    features_df.loc[zscore_flag, 'temperature'],
                    color='orange', s=20, marker='^', zorder=5, label='Z-score Anomaly')
axes[0].set_ylabel("Temperature (°C)")
axes[0].legend(loc='upper right')
axes[0].grid(True, alpha=0.3)

# Humidity
axes[1].plot(features_df['timestamp'], features_df['humidity'], 'g-', alpha=0.7, label='Humidity')
if iforest_flag.any():
    axes[1].scatter(features_df.loc[iforest_flag, 'timestamp'],
                    features_df.loc[iforest_flag, 'humidity'],
                    color='red', s=30, zorder=5, label='IF Anomaly')
if zscore_flag.any():
    axes[1].scatter(features_df.loc[zscore_flag, 'timestamp'],
                    features_df.loc[zscore_flag, 'humidity'],
                    color='orange', s=20, marker='^', zorder=5, label='Z-score Anomaly')
axes[1].set_ylabel("Humidity (%)")
axes[1].set_xlabel("Timestamp")
axes[1].legend(loc='upper right')
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
st.pyplot(fig)

# Anomaly score chart
st.subheader("Isolation Forest Anomaly Score Over Time")
fig2, ax = plt.subplots(figsize=(10, 3))
ax.plot(features_df['timestamp'], features_df['iforest_score'], 'b-', alpha=0.7)
ax.axhline(y=iforest_threshold, color='red', linestyle='--', label=f'Threshold ({iforest_threshold:.4f})')
if iforest_flag.any():
    ax.scatter(features_df.loc[iforest_flag, 'timestamp'],
               features_df.loc[iforest_flag, 'iforest_score'],
               color='red', s=30, zorder=5, label='Flagged')
ax.set_ylabel("Decision Function Score")
ax.set_xlabel("Timestamp")
ax.legend()
ax.grid(True, alpha=0.3)
st.pyplot(fig2)

# ============================================================
# FLAGGED ROWS TABLE
# ============================================================
st.subheader("Flagged Rows")

# Combine flags
any_flag = iforest_flag | zscore_flag
flagged_df = features_df[any_flag].copy()

if len(flagged_df) > 0:
    display_cols = ['timestamp', 'temperature', 'humidity', 
                    'iforest_score', 'iforest_anomaly', 'zscore_anomaly']
    if 'label' in flagged_df.columns:
        display_cols.append('label')
    st.dataframe(flagged_df[display_cols].sort_values('timestamp'), use_container_width=True)
else:
    st.info("No rows flagged as anomalous.")

# ============================================================
# EVALUATION (if labels exist)
# ============================================================
if 'label' in features_df.columns:
    st.subheader("Evaluation (Test Set Only)")
    
    y_true = features_df['label'].values
    
    # Z-score metrics
    cm_z = confusion_matrix(y_true, zscore_flag)
    prec_z, rec_z, f1_z, _ = precision_recall_fscore_support(y_true, zscore_flag, average='binary', zero_division=0)
    
    # IF metrics
    cm_if = confusion_matrix(y_true, iforest_flag)
    prec_if, rec_if, f1_if, _ = precision_recall_fscore_support(y_true, iforest_flag, average='binary', zero_division=0)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Z-Score Method**")
        st.write(f"Confusion Matrix: TN={cm_z[0,0]}, FP={cm_z[0,1]}, FN={cm_z[1,0]}, TP={cm_z[1,1]}")
        st.write(f"Precision: {prec_z:.3f}")
        st.write(f"Recall: {rec_z:.3f}")
        st.write(f"F1: {f1_z:.3f}")
    
    with col2:
        st.markdown("**Isolation Forest**")
        st.write(f"Confusion Matrix: TN={cm_if[0,0]}, FP={cm_if[0,1]}, FN={cm_if[1,0]}, TP={cm_if[1,1]}")
        st.write(f"Precision: {prec_if:.3f}")
        st.write(f"Recall: {rec_if:.3f}")
        st.write(f"F1: {f1_if:.3f}")
    
    st.caption("Test set: 55 rows, 10 anomalies (one event). Metrics are indicative only.")
else:
    st.info("No label column found in data. Upload data with a 'label' column (0=normal, 1=anomaly) to see evaluation metrics.")

# ============================================================
# NOTES
# ============================================================
st.subheader("Notes")
st.markdown("""
- **First row of each session is skipped**: The feature building drops the first row of each session (no previous value for change features, insufficient history for rolling windows).
- **Trained on normal indoor data only**: The Isolation Forest and Z-score thresholds were computed from normal indoor data (humidity ~61%). A change of environment (e.g., lower humidity ~58%) can raise false alarms.
- **Evaluation limitations**: The test set has only 55 rows with ONE event (10 anomaly rows). Metrics are indicative only and cannot demonstrate generalisation to unseen conditions.
- **False alarms in post-event window**: Isolation Forest may flag up to 14 rows after an anomaly due to rolling window contamination (the window still contains the anomaly values).
""")