SECTION 5: Feature Engineering

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

| Raw Features | Engineered Features |
|--------------|---------------------|
| temperature | temperature_change (difference from previous reading) |
| humidity | humidity_abs_change (magnitude of change, ignoring direction) |
| | temperature_rolling_mean_5 (average of last 5 readings) |
| humidity_rolling_std_15 (variability of last 15 readings) |

Our Feature Strategy:
1. Change features (4): Capture sudden jumps between consecutive readings
2. Rolling statistical features (10): Capture recent baseline/trend and volatility
3. Gap-aware rolling: Never calculate statistics across recording gaps (>10 seconds)

Window Sizes:
- 5 observations = short-term trend (~10 seconds if regular 2s sampling)
- 15 observations = medium-term trend (~30 seconds if regular 2s sampling)

Important: We do NOT describe windows as exact seconds because our data has repeated timestamps and gaps. "5 observations" is not exactly 10 seconds. We describe the window size in observations, not time.

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
If current reading is far from rolling mean, it might be anomalous
Rolling standard deviation = how variable the last N readings are
High std = sensor is volatile/unstable
Low std = sensor is stable

Window Sizes:
- 5 observations = short-term trend (~10 seconds if regular 2s sampling)
- 15 observations = medium-term trend (~30 seconds if regular 2s sampling)

Important: We do NOT describe windows as exact seconds because our data has repeated timestamps and gaps. "5 observations" is not exactly 10 seconds. We describe the window size in observations, not time.

Pandas Function: .rolling(window=N).mean() / .std()
- df[col].rolling(window=5).mean() computes mean of current + previous 4 rows
- First N-1 rows have NaN (not enough data for full window)
- By default, min_periods=None means all N values must be present; we keep default to be conservative

Gap Handling
Later we will handle timestamp gaps (>10 seconds) by resetting rolling windows. This ensures statistics never cross recording gaps.