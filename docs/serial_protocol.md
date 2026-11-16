# Serial Communication Protocol

## Overview

This document describes the serial communication protocol between the ESP32 firmware and the Python data logger. The protocol is intentionally simple: line-oriented CSV over USB serial (UART).

---

## Physical Layer

| Parameter | Value |
|-----------|-------|
| Interface | USB CDC (Virtual COM Port) |
| Baud Rate | 115200 |
| Data Bits | 8 |
| Parity | None |
| Stop Bits | 1 |
| Flow Control | None |

---

## Data Format

### Transmission Direction
```
ESP32 (TX) ──────────────────▶ PC (RX)
```

### Line Format
Each line contains two comma-separated floating-point values terminated by newline (`\n`):

```
temperature,humidity\n
```

### Example Output
```
temperature,humidity
25.90,60.80
26.00,60.70
26.10,60.60
26.20,60.50
```

### Field Definitions

| Field | Type | Unit | Precision | Notes |
|-------|------|------|-----------|-------|
| temperature | float | °C | 2 decimal places | `%.2f` format |
| humidity | float | % RH | 2 decimal places | `%.2f` format |

### Header Line
The first line after boot is a human-readable header:
```
temperature,humidity
```
- Python logger **skips** lines starting with "temperature" or "humidity"
- This allows Serial Monitor users to identify columns

---

## Timing

| Parameter | Value | Source |
|-----------|-------|--------|
| Sampling interval | 2000 ms | `delay(2000)` in firmware |
| Transmission frequency | 0.5 Hz | 1 line per 2 seconds |
| Sensor measurement frequency | 0.5 Hz | Same as transmission |

**Important:** The DHT11 sensor measurement and serial transmission happen in the same loop iteration. There is no buffering or batching — each measurement is transmitted immediately after reading.

---

## Error Handling (Firmware Side)

The firmware validates readings before transmission:

```cpp
float temperature = dht.readTemperature();
float humidity = dht.readHumidity();

if (!isnan(temperature) && !isnan(humidity)) {
    Serial.printf("%.2f,%.2f\n", temperature, humidity);
}
// Failed readings are silently dropped — no partial line sent
```

### Failure Modes
| Condition | Firmware Behavior | Python Logger Sees |
|-----------|-------------------|---------------------|
| Checksum error | Skip transmission | Gap in sequence (no line) |
| Timeout | Skip transmission | Gap in sequence |
| Sensor disconnected | Skip transmission | Gap in sequence |
| Valid reading | Transmit CSV line | Parses successfully |

**No error codes or diagnostic messages are sent over serial** — only valid data lines (plus the initial header).

---

## Python Logger Parsing

Shared serial utilities live in [`collect/serial_utils.py`](../collect/serial_utils.py) and are used by [`logger.py`](../logger.py), [`collect/collect_session.py`](../collect/collect_session.py), and the live Streamlit dashboards (`user_app.py`, `pages/1_Analyse.py`).

### Opening Serial Safely & Validation Rules
```python
ser = open_serial_port(port, baudrate=baud, timeout=1.0)
# Sets ser.dtr = False and ser.rts = False BEFORE open() so USB-UART bridges
# do not reset the ESP32 into bootloader banner output mid-stream.

parsed = parse_sensor_line(raw_line)
# 1. Strips whitespace and ignores boot/header prefixes ("temperature", "ets ", "rst:", ...)
# 2. Enforces 2 comma-separated finite floats
# 3. Enforces physical DHT11/operating sanity bounds from config.yaml (-10..65 C, 0..100% RH)
```

Live collection also deduplicates identical second-level timestamps (`if timestamp == last_ts: continue`) to guard against OS USB serial buffer bursts.

### Compatibility Requirements
The firmware output **must** match these expectations:

| Requirement | Firmware Implementation |
|-------------|------------------------|
| Two values per line | `Serial.printf("%.2f,%.2f\n", ...)` |
| Comma separator | Hardcoded in format string |
| Newline termination | `\n` in format string |
| Valid floats | `%.2f` produces valid float strings |
| No extra fields | Only two values printed |
| Header skip | Python skips "temperature" prefix |

---

## Data Flow Summary

```
┌─────────────┐     ┌──────────────┐     ┌──────────────────┐     ┌─────────────┐
│   DHT11     │────▶│   ESP32      │────▶│   USB Serial     │────▶│  Python     │
│  Sensor     │     │  Firmware    │     │   (115200)       │     │  logger.py  │
└─────────────┘     └──────────────┘     └──────────────────┘     └─────────────┘
      │                    │                    │                    │
      │ readTemperature()  │                    │                    │
      │ readHumidity()     │                    │                    │
      │                    │ isnan() check      │                    │
      │                    │ Serial.printf()    │                    │
      │                    │                    │ decode UTF-8       │
      │                    │                    │ strip, split(",")  │
      │                    │                    │ float() conversion │
      │                    │                    │ add timestamp      │
      │                    │                    │ write CSV          │
      ▼                    ▼                    ▼                    ▼
  Analog signal       2 CSV floats          Raw bytes           CSV file
  (single-wire)       per 2 sec             (temperature,      (timestamp,
                                              humidity\n)         temp, hum)
```

---

## Verification Checklist

To confirm firmware/logger compatibility:

1. **Upload firmware** to ESP32
2. **Open Serial Monitor** at 115200 baud
3. **Verify output** matches:
   ```
   temperature,humidity
   25.90,60.80
   26.00,60.70
   ...
   ```
4. **Close Serial Monitor** (it locks the port)
5. **Run Python logger**: `python logger.py`
6. **Verify CSV output** in `data/raw/normal_data.csv`:
   ```csv
   timestamp,temperature,humidity
   2026-11-03T10:30:00,25.90,60.80
   2026-11-03T10:30:02,26.00,60.70
   ```

---

## Protocol Versioning

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-11-03 | Initial: temperature,humidity CSV at 115200 baud |
| 1.1 | 2026-11-10 | Hardware-verified on Windows `COM19`; added DTR/RTS safe open, physical bounds check, and burst-timestamp guard in `collect/serial_utils.py` & firmware bounds guard |

**Future changes** (if needed) should:
- Increment version in this document
- Maintain backward compatibility or provide migration path
- Update both firmware and logger simultaneously