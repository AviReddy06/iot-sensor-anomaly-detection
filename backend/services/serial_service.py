"""
backend/services/serial_service.py
Serial communication background service.
Exactly one thread owns the port. Suppresses bootloader resets via dtr=False, rts=False.
Supports auto-detection, reconnection backoff, and CSV simulation mode.
"""

from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from pathlib import Path
import threading
import time
from typing import Any, Callable, Dict, List, Optional
import pandas as pd
import serial
import serial.tools.list_ports
from backend.config import PROJECT_ROOT, SERIAL_PORT
from backend.database import insert_reading
from backend.services.detector_service import detector_service
from backend.services.events_service import events_service
from backend.services.serial_parser import parse_serial_line


class SerialService:
    def __init__(self):
        # Step 1: Initialize threading and state variables
        self._thread: Optional[threading.Thread] = None
        self._running: bool = False
        self._port: str = SERIAL_PORT
        self._baudrate: int = 115200
        self._is_streaming: bool = False
        self._stream_source: str = "none"  # "hardware", "simulation", or "none"
        self._last_error: Optional[str] = None
        self._recent_buffer: List[Dict[str, Any]] = []
        self._listeners: List[Callable[[Dict[str, Any]], None]] = []

    def add_listener(self, cb: Callable[[Dict[str, Any]], None]) -> None:
        self._listeners.append(cb)

    def detect_esp32_port(self) -> Optional[str]:
        # Step 1: Scan ports for known USB-UART bridge identifiers
        for p in serial.tools.list_ports.comports():
            desc = (p.description or "").lower()
            hwid = (p.hwid or "").lower()
            if any(k in desc or k in hwid for k in ["cp210", "ch340", "ch341", "ftdi", "usb serial"]):
                return p.device
        return None

    def start_hardware(self, port: Optional[str] = None, baud: int = 115200) -> Dict[str, Any]:
        # Step 1: Stop existing stream if active
        self.stop()
        target_port = port or (None if self._port == "auto" else self._port) or self.detect_esp32_port()
        if not target_port:
            raise ValueError("No ESP32 serial port detected or specified.")
        self._port = target_port
        self._baudrate = baud
        self._stream_source = "hardware"
        self._running = True
        # Step 2: Spawn single background thread
        self._thread = threading.Thread(target=self._hardware_loop, daemon=True)
        self._thread.start()
        return {"status": "started", "source": "hardware", "port": self._port}

    def start_simulation(self, csv_name: str = "test", interval_sec: float = 1.0) -> Dict[str, Any]:
        # Step 1: Stop existing stream
        self.stop()
        self._stream_source = "simulation"
        self._running = True
        # Step 2: Spawn simulation thread
        self._thread = threading.Thread(target=self._simulation_loop, args=(csv_name, interval_sec), daemon=True)
        self._thread.start()
        return {"status": "started", "source": "simulation", "dataset": csv_name}

    def stop(self) -> Dict[str, Any]:
        # Step 1: Signal thread to terminate and join
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.5)
        self._thread = None
        self._is_streaming = False
        self._stream_source = "none"
        return {"status": "stopped"}

    def _hardware_loop(self) -> None:
        backoff = 1.0
        while self._running:
            ser = None
            try:
                # Step 1: Open port with dtr=False and rts=False to prevent bootloader reset
                ser = serial.Serial()
                ser.port = self._port
                ser.baudrate = self._baudrate
                ser.timeout = 1.0
                ser.dtr = False
                ser.rts = False
                ser.open()
                self._is_streaming = True
                self._last_error = None
                backoff = 1.0

                while self._running and ser.is_open:
                    line_raw = ser.readline().decode("utf-8", errors="replace")
                    parsed = parse_serial_line(line_raw)
                    if parsed is not None:
                        temp, hum = parsed
                        self._process_reading(temp, hum, is_simulated=False)
            except Exception as e:
                self._last_error = str(e)
                self._is_streaming = False
                time.sleep(backoff)
                backoff = min(backoff * 1.5, 10.0)
            finally:
                if ser and ser.is_open:
                    ser.close()

    def _simulation_loop(self, csv_name: str, interval: float) -> None:
        # Step 1: Load CSV file
        p = PROJECT_ROOT / "data" / "processed" / f"{csv_name}_data_with_labels.csv"
        if not p.exists():
            p = PROJECT_ROOT / "data" / "raw" / f"{csv_name}.csv"
        df = pd.read_csv(p) if p.exists() else pd.DataFrame({"temperature": [25.5], "humidity": [60.0]})
        self._is_streaming = True
        idx = 0
        while self._running:
            row = df.iloc[idx % len(df)]
            temp = float(row.get("temperature", 25.0))
            hum = float(row.get("humidity", 60.0))
            self._process_reading(temp, hum, is_simulated=True)
            idx += 1
            time.sleep(interval)

    def _process_reading(self, temp: float, hum: float, is_simulated: bool) -> None:
        # Step 1: Generate PC-clock timestamp in ISO format
        now_iso = datetime.now(timezone.utc).isoformat()
        # Step 2: Persist reading in SQLite
        insert_reading(now_iso, temp, hum, is_simulated=is_simulated)

        # Step 3: Rolling buffer for inference (keep last 15 samples)
        self._recent_buffer.append({"timestamp": now_iso, "temperature": temp, "humidity": hum})
        if len(self._recent_buffer) > 15:
            self._recent_buffer.pop(0)

        # Step 4: Run model detection on buffer
        buf_df = pd.DataFrame(self._recent_buffer)
        eval_res = detector_service.evaluate_streaming_sample(buf_df)
        is_flagged = eval_res["flag"]
        peak_z = eval_res["peak_z"]

        # Step 5: Events aggregation service
        closed_event = events_service.process_sample(now_iso, temp, hum, is_flagged, peak_z)

        # Step 6: Package payload (with simulation tag if simulated)
        payload = {
            "timestamp": now_iso,
            "temperature": temp,
            "humidity": hum,
            "is_simulated": is_simulated,
            "source_label": "Simulated" if is_simulated else "Live",
            "is_anomalous": is_flagged,
            "score": eval_res["score"],
            "ewma_z": eval_res["ewma_z"],
            "peak_z": peak_z,
            "closed_event": closed_event,
        }

        # Step 7: Broadcast to listeners (WebSockets)
        for cb in self._listeners:
            try:
                cb(payload)
            except Exception:
                pass

    def get_status(self) -> Dict[str, Any]:
        return {
            "is_streaming": self._is_streaming,
            "stream_source": self._stream_source,
            "current_port": self._port,
            "current_baud": self._baudrate,
            "detected_esp32_port": self.detect_esp32_port(),
            "last_error": self._last_error,
        }


serial_service = SerialService()
