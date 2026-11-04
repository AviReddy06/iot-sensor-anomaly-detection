"""
logger.py - Log DHT11 temperature and humidity from ESP32 via serial port.

Usage:
    python logger.py

Press Ctrl+C to stop logging.

Requirements:
    - pyserial (pip install pyserial)
    - ESP32 connected via USB, printing "temperature,humidity" lines at 115200 baud
    - Arduino Serial Monitor MUST be closed before running this script
"""

import serial
import sys
from datetime import datetime
from pathlib import Path

# ========== CONFIGURATION ==========
# Change this to match your ESP32's COM port (check Device Manager on Windows)
PORT = "COM19"
BAUD = 115200
# Output CSV file
OUTPUT_FILE = Path("data/normal_data.csv")
# ====================================


def main():
    # Create data directory if it doesn't exist
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Check if file exists and is empty to decide whether to write header
    write_header = not OUTPUT_FILE.exists() or OUTPUT_FILE.stat().st_size == 0

    # Open serial port
    try:
        ser = serial.Serial(PORT, BAUD, timeout=1)
        print(f"Connected to {PORT} at {BAUD} baud")
        print(f"Logging to {OUTPUT_FILE}")
        print("Press Ctrl+C to stop\n")
    except serial.SerialException as e:
        print(f"ERROR: Could not open serial port {PORT}")
        print(f"  Reason: {e}")
        print("\nChecklist:")
        print("  1. Is the ESP32 connected via USB?")
        print("  2. Is the COM port correct? (Check Windows Device Manager)")
        print("  3. Is Arduino Serial Monitor CLOSED? (It locks the port)")
        print("  4. Is the ESP32 sketch running and printing data?")
        sys.exit(1)

    # Open CSV file in append mode
    with OUTPUT_FILE.open("a", newline="") as f:
        if write_header:
            f.write("timestamp,temperature,humidity\n")
            f.flush()

        try:
            while True:
                # Read one line from serial port
                line_bytes = ser.readline()
                if not line_bytes:
                    continue  # timeout, no data yet

                # Decode and clean
                line = line_bytes.decode("utf-8", errors="ignore").strip()

                # Skip empty lines
                if not line:
                    continue

                # Skip header line from ESP32 (if it prints one)
                if line.lower().startswith("temperature") or line.lower().startswith("humidity"):
                    continue

                # Split on comma
                parts = line.split(",")
                if len(parts) != 2:
                    continue  # malformed line

                # Convert to float
                try:
                    temperature = float(parts[0])
                    humidity = float(parts[1])
                except ValueError:
                    continue  # not numeric

                # Create timestamp and write row
                timestamp = datetime.now().isoformat(timespec="seconds")
                row = f"{timestamp},{temperature},{humidity}\n"
                f.write(row)
                f.flush()  # ensure data is written immediately

                # Print to terminal
                print(f"Saved: {row.strip()}")

        except KeyboardInterrupt:
            print("\nStopped by user (Ctrl+C)")
        finally:
            ser.close()
            print("Serial port closed")


if __name__ == "__main__":
    main()