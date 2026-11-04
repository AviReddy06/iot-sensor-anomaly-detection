SECTION 4: Data Preprocessing and Cleaning

### Key Concept: Data Cleaning
Real-world sensor data is messy. We need to:
1. Handle missing/invalid values - but DHT11 gives 0 missing, we just flag out-of-range
2. Remove exact duplicates - identical rows add no information, bias training
3. Handle repeated timestamps - same timestamp, different readings (logging bug)
4. Handle timestamp gaps - don't interpolate across large gaps
5. Flag suspicious observations - don't auto-delete, document for review

Critical: Preserve Original Data
Never modify original CSV files in data/raw/. Always save cleaned versions to data/processed/.