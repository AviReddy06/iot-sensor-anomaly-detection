#!/usr/bin/env python3
"""
collect/collect_session.py
Collect sensor data from ESP32 via USB serial and save to CSV.

Usage:
    python collect/collect_session.py <COM_PORT|auto> <OUTPUT_CSV_PATH> [DURATION_SEC]
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import config
from collect.serial_utils import detect_esp32_port, open_serial_port, parse_sensor_line


def collect_session(
    com_port: str,
    output_path: Path,
    baud: int = config.baudrate,
    duration_sec: float | None = None,
    overwrite: bool = False,
) -> int:
    """Read serial readings from ESP32 and write validated CSV rows."""
    if com_port.lower() == "auto":
        com_port = detect_esp32_port(config.serial_port)

    if output_path.exists() and not overwrite:
        raise FileExistsError(
            f"Output file already exists: {output_path}. "
            "Pass --overwrite or remove the existing file first."
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    ser = open_serial_port(com_port, baudrate=baud, timeout=config.serial_timeout)
    print(f"Connected to {com_port} at {baud} baud")
    print(f"Logging to {output_path}")
    if duration_sec is not None:
        print(f"Target duration: {duration_sec:.0f}s")
    else:
        print("Press Ctrl+C to stop")

    row_count = 0
    last_ts: str | None = None
    start_time = time.monotonic()

    try:
        mode = "w" if overwrite else "a"
        with output_path.open(mode, newline="", encoding="utf-8") as f:
            f.write("timestamp,temperature,humidity\n")
            f.flush()

            while True:
                if duration_sec is not None and (time.monotonic() - start_time) >= duration_sec:
                    break

                raw_bytes = ser.readline()
                if not raw_bytes:
                    continue

                raw_line = raw_bytes.decode("utf-8", errors="ignore")
                parsed = parse_sensor_line(raw_line)
                if parsed is None:
                    continue

                temperature, humidity = parsed
                timestamp = datetime.now().isoformat(timespec="seconds")

                # Prevent OS USB-UART buffer bursts from writing multiple rows on the exact same second
                if timestamp == last_ts:
                    continue
                last_ts = timestamp

                row = f"{timestamp},{temperature:.2f},{humidity:.2f}\n"
                f.write(row)
                f.flush()

                row_count += 1
                if row_count == 1 or row_count % 10 == 0:
                    print(f"Rows collected: {row_count} | Latest: {row.strip()}")
    except KeyboardInterrupt:
        print("\nStopped by user (Ctrl+C)")
    finally:
        ser.close()
        print("Serial port closed")
        print(f"Total rows collected: {row_count}")

    return row_count


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect ESP32 + DHT11 serial readings to CSV.")
    parser.add_argument("com_port", help="COM port (e.g. COM19) or 'auto'")
    parser.add_argument("output_csv", type=Path, help="Output CSV path")
    parser.add_argument("duration_sec", nargs="?", type=float, default=None, help="Optional duration in seconds")
    parser.add_argument("--baud", type=int, default=config.baudrate, help="Serial baudrate")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output CSV")
    args = parser.parse_args()

    try:
        collect_session(
            com_port=args.com_port,
            output_path=args.output_csv,
            baud=args.baud,
            duration_sec=args.duration_sec,
            overwrite=args.overwrite,
        )
    except Exception as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
