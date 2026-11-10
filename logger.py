"""
logger.py - Continuous serial logger for ESP32 + DHT11 temperature & humidity.

Usage:
    python logger.py [--port COM19] [--baud 115200] [--output data/raw/live_log.csv]
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys

from config import config
from collect.serial_utils import detect_esp32_port, open_serial_port, parse_sensor_line


def run_logger(port: str, baud: int, output_file: Path) -> None:
    """Append validated ESP32 readings with CSV headers into output_file."""
    if port.lower() == "auto":
        port = detect_esp32_port(config.serial_port)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    write_header = not output_file.exists() or output_file.stat().st_size == 0

    try:
        ser = open_serial_port(port, baudrate=baud, timeout=config.serial_timeout)
        print(f"Connected to {port} at {baud} baud")
        print(f"Logging to {output_file}")
        print("Press Ctrl+C to stop\n")
    except Exception as exc:
        print(f"ERROR: Could not open serial port {port}: {exc}")
        print("\nChecklist:")
        print("  1. ESP32 connected via USB")
        print("  2. Correct COM port (check Device Manager)")
        print("  3. Arduino Serial Monitor CLOSED")
        sys.exit(1)

    last_ts: str | None = None
    with output_file.open("a", newline="", encoding="utf-8") as f:
        if write_header:
            f.write("timestamp,temperature,humidity\n")
            f.flush()

        try:
            while True:
                line_bytes = ser.readline()
                if not line_bytes:
                    continue

                raw_line = line_bytes.decode("utf-8", errors="ignore")
                parsed = parse_sensor_line(raw_line)
                if parsed is None:
                    continue

                temperature, humidity = parsed
                timestamp = datetime.now().isoformat(timespec="seconds")
                if timestamp == last_ts:
                    continue
                last_ts = timestamp

                row = f"{timestamp},{temperature:.2f},{humidity:.2f}\n"
                f.write(row)
                f.flush()
                print(f"Saved: {row.strip()}")
        except KeyboardInterrupt:
            print("\nStopped by user (Ctrl+C)")
        finally:
            ser.close()
            print("Serial port closed")


def main() -> None:
    parser = argparse.ArgumentParser(description="Continuous ESP32 + DHT11 CSV logger.")
    parser.add_argument("--port", default="auto", help="COM port or 'auto'")
    parser.add_argument("--baud", type=int, default=config.baudrate, help="Serial baudrate")
    parser.add_argument(
        "--output",
        type=Path,
        default=config.raw_dir / "live_session_log.csv",
        help="Destination CSV path (default: data/raw/live_session_log.csv)",
    )
    args = parser.parse_args()
    run_logger(args.port, args.baud, args.output)


if __name__ == "__main__":
    main()
