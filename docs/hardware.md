# Hardware Documentation

## ESP32 Overview

The ESP32 is a low-cost, low-power System on Chip (SoC) with integrated Wi-Fi and dual-mode Bluetooth. For this project, we use only its USB serial interface and GPIO capabilities.

**Key specifications relevant to this project:**
- Dual-core Xtensa LX6 microprocessor @ 240 MHz
- 520 KB SRAM
- 34 programmable GPIOs
- USB-to-UART bridge (CP2102, CH340, or native USB on ESP32-S3)
- 3.3V logic levels (GPIO are NOT 5V tolerant)

**Board used:** ESP32 DevKit V1 (or compatible — ESP32-WROOM-32, ESP32-DevKitC, etc.)

---

## DHT11 Sensor Overview

The DHT11 is a basic, ultra-low-cost digital temperature and humidity sensor.

| Parameter | Specification |
|-----------|---------------|
| Temperature range | 0–50°C |
| Temperature accuracy | ±2°C |
| Humidity range | 20–90% RH |
| Humidity accuracy | ±5% RH |
| Resolution | 1°C / 1% RH datasheet nominal (`0.1` decimal step observed on module library output) |
| Sampling rate | ≤ 1 Hz (minimum 1–2 sec between reads) |
| Operating voltage | 3.3V – 5.5V |
| Signal | Single-wire digital protocol |
| Pull-up | Required on data line (typically 4.7kΩ–10kΩ) |

> **Hardware Verification Status (2026-11-10):** Verified live on Windows **`COM19`** at **`115200` baud** with `firmware/esp32_dht11/esp32_dht11.ino`. Valid `temperature,humidity\n` lines streamed at ~0.5 Hz (`28.10–29.60°C`, `53.70–59.80% RH`) and passed physical bounds guards (`-10..65°C`, `0..100% RH`).

---

## GPIO 4 Connection

The DHT11 data pin connects to **ESP32 GPIO 4**.

```
ESP32 GPIO 4 ────── DHT11 DATA pin
```

**Why GPIO 4?**
- GPIO 4 is a general-purpose I/O pin (not strapping pin on most ESP32 boards)
- Supports input/output with internal pull-up/down
- No special boot-mode conflicts

---

## VCC and GND Connections

### ⚠️ IMPORTANT: Verify Your Module Type

The DHT11 comes in two common form factors. **Check which one you have before wiring.**

#### Option A: Bare 4-Pin DHT11 Sensor
```
Pin 1 (VCC)  ─── 3.3V or 5V (check datasheet)
Pin 2 (DATA) ─── GPIO 4 (with 4.7kΩ–10kΩ pull-up to VCC)
Pin 3 (NC)    ─── Not connected
Pin 4 (GND)   ─── GND
```
- **Pull-up resistor REQUIRED** on data line (4.7kΩ–10kΩ between DATA and VCC)
- Pin 3 is no-connect

#### Option B: 3-Pin DHT11 Module (PCB with built-in resistor)
```
Pin 1 (VCC)  ─── 3.3V or 5V (check module silkscreen)
Pin 2 (DATA) ─── GPIO 4 (pull-up already on module PCB)
Pin 3 (GND)   ─── GND
```
- **Pull-up typically INCLUDED** on module PCB
- No external resistor needed

**Hardware Confirmed (2026-11-10):** ESP32 + DHT11 module on GPIO 4, live-verified on Windows `COM19` at `115200` baud (`0.1°C` / `0.1% RH` decimal resolution output at 2s intervals).

---

## Wiring Diagram

### Bare 4-Pin Sensor (with external pull-up)
```
                    4.7kΩ–10kΩ
    ESP32 3.3V ──────┬─────┐
                     │     │
    ESP32 GPIO 4 ────┤     │
                     │     │
      DHT11 VCC ─────┤     │
      DHT11 DATA ────┘     │
                           │
      DHT11 GND ───────────┘
    ESP32 GND ──────────────┘
```

### 3-Pin Module (pull-up on board)
```
    ESP32 3.3V ────── DHT11 VCC
    ESP32 GPIO 4 ─── DHT11 DATA
    ESP32 GND ────── DHT11 GND
```

---

## Required Arduino Libraries

Install via **Arduino IDE → Library Manager**:

1. **DHT sensor library** by Adafruit
   - Search: "DHT sensor library"
   - Author: Adafruit
   - Version: Latest (tested with 1.4.x)

2. **Adafruit Unified Sensor** (automatic dependency)
   - Search: "Adafruit Unified Sensor"
   - Author: Adafruit
   - Installed automatically when DHT library is installed

---

## Arduino IDE Setup

1. **Install ESP32 board support:**
   - File → Preferences → Additional Boards Manager URLs:
     ```
     https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
     ```
   - Tools → Board → Boards Manager → Search "esp32" → Install "esp32 by Espressif Systems"

2. **Select board:**
   - Tools → Board → ESP32 Arduino → **ESP32 Dev Module** (or your specific board)

3. **Install libraries:**
   - Tools → Manage Libraries → Search and install the two libraries above

---

## Board and Port Selection

| Setting | Value |
|---------|-------|
| Board | ESP32 Dev Module (or ESP32 DevKit V1) |
| Upload Speed | 921600 (default) |
| CPU Frequency | 240 MHz (WiFi/BT) |
| Flash Frequency | 80 MHz |
| Flash Mode | QIO |
| Flash Size | 4MB (32Mb) |
| Partition Scheme | Default 4MB with spiffs (1.2MB APP/1.5MB SPIFFS) |
| Core Debug Level | None |
| Port | **Your COM port** (e.g., COM19 — check Device Manager) |

**To find COM port:**
- Windows: Device Manager → Ports (COM & LPT) → "Silicon Labs CP210x USB to UART Bridge" or "CH340"
- Note the COM number (e.g., COM19)

---

## Firmware Uploading Instructions

1. Connect ESP32 to PC via USB
2. Open `firmware/esp32_dht11/esp32_dht11.ino` in Arduino IDE
3. Verify board and port settings (see above)
4. Click **Upload** (right arrow icon) or press `Ctrl+U`
5. Wait for "Done uploading" message

**If upload fails:**
- Hold BOOT button on ESP32 while clicking Upload, release when "Connecting..." appears
- Try different USB cable (some are charge-only)
- Ensure no other program (Serial Monitor, Python logger) is using the port

---

## Serial Monitor Verification

1. Open Serial Monitor: Tools → Serial Monitor (or `Ctrl+Shift+M`)
2. Set baud rate to **115200** (bottom-right dropdown)
3. You should see:
   ```
   temperature,humidity
   25.90,60.80
   26.00,60.70
   26.10,60.60
   ...
   ```
4. New line appears every 2 seconds
5. If you see `nan,nan` or no data:
   - Check wiring (especially DATA pin and pull-up)
   - Verify VCC voltage matches module (3.3V vs 5V)
   - Check Serial Monitor baud rate matches firmware (115200)

---

## Troubleshooting Checklist

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| No output in Serial Monitor | Wrong baud rate | Set to 115200 |
| `nan,nan` repeated | Wiring issue | Check DATA pin, pull-up, VCC/GND |
| `nan,nan` intermittent | Timing/power | Ensure stable 3.3V, add capacitor |
| Upload fails | Port busy / boot mode | Close Serial Monitor, hold BOOT during upload |
| Garbled text | Baud mismatch | Verify 115200 in both firmware and monitor |
| Port not appearing | Driver missing | Install CP210x or CH340 driver |

---

## Notes for Python Integration

- Shared utilities in `collect/serial_utils.py` validate `temperature,humidity\n` lines, skip boot/header banners, and enforce physical bounds from `config.yaml` (`-10..65°C`, `0..100% RH`).
- `open_serial_port()` disables `DTR`/`RTS` assertions prior to opening the port so opening Python readers or dashboards does not reboot the ESP32.
- Python adds its own ISO timestamp on receipt (`datetime.now().isoformat(timespec="seconds")`) and collapses duplicate same-second buffer bursts.