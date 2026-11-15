#!/usr/bin/env python3
"""
scripts/hardware_check.py
Hardware validation script for new calibration datasets.
Checks stopping rules:
- Under 100 rows
- Under 5 events
- >50% rows have temp == hum
Returns exit code 0 if all checks pass, non-zero otherwise.
Writes results/hardware_check.json with "simulated": true/false field.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import config


def check_dataset(filepath: Path) -> Dict[str, Any]:
    """Check a dataset against stopping rules."""
    import pandas as pd
    
    df = pd.read_csv(filepath)
    rows = len(df)
    
    # Check 1: Under 100 rows
    under_100_rows = rows < 100
    
    # Check 2: Under 5 events (if label column exists)
    under_5_events = False
    if "label" in df.columns:
        events = df["label"].sum()
        under_5_events = events < 5
    
    # Check 3: >50% rows have temp == hum
    temp_equals_hum = False
    if "temperature" in df.columns and "humidity" in df.columns:
        temp_hum_equal = (df["temperature"] == df["humidity"]).sum()
        temp_equals_hum = (temp_hum_equal / rows) > 0.5 if rows > 0 else False
    
    # Overall pass/fail
    all_checks_pass = not (under_100_rows or under_5_events or temp_equals_hum)
    
    return {
        "rows": int(rows),
        "under_100_rows": under_100_rows,
        "under_5_events": under_5_events,
        "temp_equals_hum_over_50pct": temp_equals_hum,
        "all_checks_pass": all_checks_pass,
    }


def run_with_fakeserial() -> Dict[str, Any]:
    """Run checks against FakeSerial simulated data."""
    from backend.services.serial_service import serial_service
    from backend.services.fake_serial import FakeSerial
    
    # Create a FakeSerial instance and get some readings
    fake = FakeSerial()
    fake.open()
    
    readings = []
    for _ in range(200):  # Get enough readings to check
        line = fake.readline()
        if line:
            parsed = fake.parse_line(line.decode() if isinstance(line, bytes) else line)
            if parsed:
                readings.append({"temperature": parsed[0], "humidity": parsed[1]})
    
    fake.close()
    
    rows = len(readings)
    temp_equals_hum = sum(1 for r in readings if abs(r["temperature"] - r["humidity"]) < 1e-4)
    temp_equals_hum_pct = (temp_equals_hum / rows * 100) if rows > 0 else 0
    
    return {
        "rows": rows,
        "under_100_rows": rows < 100,
        "under_5_events": True,  # No event labels in fake serial
        "temp_equals_hum_over_50pct": temp_equals_hum_pct > 50,
        "all_checks_pass": not (rows < 100 or temp_equals_hum_pct > 50),
        "simulated": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Hardware check for calibration datasets")
    parser.add_argument("--file", type=str, help="Path to CSV dataset to check")
    parser.add_argument("--fake-serial", action="store_true", help="Run against FakeSerial simulated data")
    parser.add_argument("--output", type=str, default="results/hardware_check.json", help="Output JSON file")
    args = parser.parse_args()
    
    results_dir = PROJECT_ROOT / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    output_path = results_dir / "hardware_check.json"
    
    if args.fake_serial:
        result = run_with_fakeserial()
    elif args.file:
        result = check_dataset(Path(args.file))
        result["simulated"] = False
    else:
        print("Error: Must specify --file or --fake-serial", file=sys.stderr)
        return 1
    
    result["timestamp"] = datetime.now().isoformat()
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    
    print(f"Hardware check result: {json.dumps(result, indent=2)}")
    print(f"Written to {output_path}")
    
    return 0 if result["all_checks_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())