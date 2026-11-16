"""
backend/services/serial_parser.py
Strict parser for incoming ESP32 DHT11 serial telemetry lines.
Extracts temperature from parts[0] and humidity from parts[1].
Rejects headers, malformed lines, NaNs, and infinite numbers.
"""

from __future__ import annotations
import math
from typing import Optional, Tuple


def parse_serial_line(line_str: str) -> Optional[Tuple[float, float]]:
    # Step 1: Strip whitespace and non-printable control characters
    clean = line_str.strip()
    if not clean:
        return None

    # Step 2: Skip header lines or diagnostic text
    lower = clean.lower()
    if "temp" in lower or "humidity" in lower or "ready" in lower or "boot" in lower:
        return None

    # Step 3: Split line by comma
    parts = clean.split(",")
    if len(parts) < 2:
        return None

    # Step 4: Extract temperature from parts[0] and humidity from parts[1]
    try:
        temp_val = float(parts[0].strip())
        hum_val = float(parts[1].strip())
    except (ValueError, TypeError):
        return None

    # Step 5: Check for NaN or infinite values
    if math.isnan(temp_val) or math.isnan(hum_val) or math.isinf(temp_val) or math.isinf(hum_val):
        return None

    # Step 6: Validate physically plausible indoor boundaries (-20 to 80 C, 0 to 100% RH)
    if not (-20.0 <= temp_val <= 80.0 and 0.0 <= hum_val <= 100.0):
        return None

    return (round(temp_val, 1), round(hum_val, 1))
