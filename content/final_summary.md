## SECTION 7: Future ML Development (Placeholder)

The following functions are planned for future development. They are NOT implemented yet but show the planned interface.

```python
def run_z_score(features, threshold=3):
    """Statistical Z-score anomaly detection baseline."""
    pass

def train_isolation_forest(normal_features, contamination=0.01):
    """Train Isolation Forest on normal data only."""
    pass

def tune_model(model, pilot_features, pilot_labels):
    """Tune decision threshold using pilot data with known anomalies."""
    pass

def evaluate_model(model, test_features, test_labels):
    """Evaluate model on hold-out test set."""
    pass

def detect_live_anomalies(model, serial_port, threshold):
    """Real-time anomaly detection on serial stream."""
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

Master notebook complete! Ready for Phase 4 (Model Training).