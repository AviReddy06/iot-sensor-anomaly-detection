"""Shared serial communication utilities for ESP32 + DHT11."""

from __future__ import annotations

import math
from pathlib import Path
import sys
import threading
import time
from typing import Dict, List, Optional, Tuple

import serial
import serial.tools.list_ports

_PORT_LOCK = threading.Lock()
_ACTIVE_SERIAL_PORTS: Dict[str, Tuple[threading.Event, threading.Thread, object]] = {}

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import config


BOOT_PREFIXES = (
    "temperature",
    "humidity",
    "ets ",
    "rst:",
    "configsip:",
    "clk_drv:",
    "mode:",
    "load:",
    "entry ",
    "boot:",
)


def list_serial_ports() -> List[Tuple[str, str]]:
    """Return available COM ports sorted with USB-UART adapters first."""
    ports = []
    for p in serial.tools.list_ports.comports():
        desc = (p.description or "").strip()
        hwid = (p.hwid or "").upper()
        is_usb_uart = (
            "USB" in hwid
            or "CP210" in desc.upper()
            or "CH340" in desc.upper()
            or "UART" in desc.upper()
            or "FTDI" in desc.upper()
        )
        ports.append((0 if is_usb_uart else 1, p.device, desc or p.device))

    ports.sort(key=lambda item: (item[0], item[1]))
    return [(device, desc) for _, device, desc in ports]


def detect_esp32_port(default: Optional[str] = None) -> str:
    """Return the most likely ESP32 USB-UART port, or default fallback."""
    fallback = default or config.serial_port
    for device, desc in list_serial_ports():
        upper = desc.upper()
        if any(tag in upper for tag in ("CP210", "CH340", "UART", "FTDI", "USB")):
            return device
    available = [device for device, _ in list_serial_ports()]
    if fallback in available:
        return fallback
    return available[0] if available else fallback


def open_serial_port(
    port: str,
    baudrate: int = 115200,
    timeout: float = 1.0,
    reset_board: bool = False,
    flush_stale: bool = True,
) -> serial.Serial:
    """Open a serial port without toggling DTR/RTS and discard stale/partial RX frames."""
    ser = serial.Serial()
    ser.port = port
    ser.baudrate = int(baudrate)
    ser.timeout = float(timeout)
    if not reset_board:
        ser.dtr = False
        ser.rts = False
    ser.open()
    if flush_stale and not reset_board:
        ser.reset_input_buffer()
        time.sleep(0.05)
        if ser.in_waiting > 0:
            ser.readline()
    return ser


def release_active_serial_port(port: str, join_timeout: float = 2.0) -> bool:
    """
    Close and stop any existing serial reader thread held by this Python process on `port`.
    Prevents `PermissionError (Access is denied)` after browser refreshes or multi-page switches.
    """
    key = port.strip().upper()
    with _PORT_LOCK:
        entry = _ACTIVE_SERIAL_PORTS.pop(key, None)

    if entry is None:
        return False

    old_stop, old_thread, old_ser = entry
    old_stop.set()
    if old_ser is not None:
        try:
            old_ser.close()
        except Exception:
            pass
    if old_thread is not None and old_thread.is_alive() and old_thread is not threading.current_thread():
        old_thread.join(timeout=join_timeout)
    return True


def register_active_serial_port(
    port: str,
    stop_event: threading.Event,
    thread: threading.Thread,
    ser: object,
) -> None:
    """Record active serial stream ownership for clean cross-page / refresh reclamation."""
    key = port.strip().upper()
    with _PORT_LOCK:
        _ACTIVE_SERIAL_PORTS[key] = (stop_event, thread, ser)


def unregister_active_serial_port(port: str, thread: threading.Thread) -> None:
    """Release port ownership entry only if owned by `thread`."""
    key = port.strip().upper()
    with _PORT_LOCK:
        entry = _ACTIVE_SERIAL_PORTS.get(key)
        if entry is not None and entry[1] is thread:
            _ACTIVE_SERIAL_PORTS.pop(key, None)


def parse_sensor_line(
    raw_line: str,
    temp_bounds: Optional[Tuple[float, float]] = None,
    hum_bounds: Optional[Tuple[float, float]] = None,
) -> Optional[Tuple[float, float]]:
    """Parse one `temperature,humidity` line and validate physical bounds."""
    if not raw_line:
        return None
    line = raw_line.strip()
    if not line:
        return None

    lower = line.lower()
    if lower.startswith(BOOT_PREFIXES):
        return None

    parts = line.split(",")
    if len(parts) != 2:
        return None

    try:
        temperature = float(parts[0].strip())
        humidity = float(parts[1].strip())
    except ValueError:
        return None

    if not (math.isfinite(temperature) and math.isfinite(humidity)):
        return None

    t_min, t_max = temp_bounds or config.temp_bounds
    h_min, h_max = hum_bounds or config.hum_bounds
    if not (t_min <= temperature <= t_max):
        return None
    if not (h_min <= humidity <= h_max):
        return None

    return round(temperature, 2), round(humidity, 2)
