
import json
import math
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

import serial

SERIAL_PORT = "COM19"
BAUD_RATE = 115200
API_URL = "https://iot-anomaly-backend-b2ql.onrender.com/api/telemetry/ingest"

TOKEN = os.environ.get("DEVICE_INGEST_TOKEN")

if not TOKEN:
    raise RuntimeError("DEVICE_INGEST_TOKEN environment variable is missing.")


def send_reading(temperature, humidity):
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperature": temperature,
        "humidity": humidity,
    }

    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Device-Token": TOKEN,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))

            anomaly_state = result.get("is_anomaly")

            if anomaly_state is True:
                print(
                    f"ANOMALY DETECTED | "
                    f"Score: {result.get('hybrid_score')}"
                )
                return True

            if anomaly_state is False:
                print(
                    f"Normal reading | "
                    f"Score: {result.get('hybrid_score')}"
                )
                return False

            print("ML result not ready yet.")
            return None

    except urllib.error.HTTPError as error:
        print(f"API error: HTTP {error.code} - {error.read().decode(errors='replace')}")
    except Exception as error:
        print(f"Connection/API error: {error}")

    return None


def main():
    print(f"Connecting to ESP32 on {SERIAL_PORT}...")

    with serial.Serial(
        SERIAL_PORT,
        BAUD_RATE,
        timeout=3,
        write_timeout=3,
    ) as device:

        time.sleep(2)
        print("Bridge running. Press Ctrl+C to stop.")

        last_buzzer_state = False

        while True:
            line = device.readline().decode(
                "utf-8", errors="replace"
            ).strip()

            if not line:
                continue

            try:
                temperature_text, humidity_text = line.split(",")
                temperature = float(temperature_text)
                humidity = float(humidity_text)

                if not math.isfinite(temperature) or not math.isfinite(humidity):
                    continue

                if not (-10 <= temperature <= 65 and 0 <= humidity <= 100):
                    continue

                buzzer_state = send_reading(temperature, humidity)

                if buzzer_state is None:
                    continue

                if buzzer_state != last_buzzer_state:
                    command = "BUZZER_ON" if buzzer_state else "BUZZER_OFF"

                    device.write((command + "\n").encode("utf-8"))
                    device.flush()

                    last_buzzer_state = buzzer_state
                    print(f"ESP32 command sent: {command}")

            except ValueError:
                continue
            except serial.SerialTimeoutException:
                print("Serial write timed out.")
            except serial.SerialException as error:
                print(f"Serial error: {error}")
                break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nBridge stopped.")
    except Exception as error:
        print(f"Bridge failed: {error}")
