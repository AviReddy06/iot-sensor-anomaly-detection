"""
backend/services/serial_service.py
Manages live USB serial streaming from ESP32, simulated dataset playback,
and real-time WebSocket frame broadcasting.
"""

from __future__ import annotations

import asyncio
from collections import deque
from datetime import datetime
import json
from pathlib import Path
import queue
import sys
import threading
import time
from typing import Any, Callable, Deque, Dict, List, Optional, Set

import pandas as pd
import serial
from serial.tools import list_ports

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from alerts.notifier import AlertManager, load_alert_settings
from collect.serial_utils import (
    detect_esp32_port,
    open_serial_port,
    parse_sensor_line,
    register_active_serial_port,
    release_active_serial_port,
    unregister_active_serial_port,
)
from config import config
from backend.services.inference_service import inference_service


class SerialService:
    def __init__(self, buffer_maxlen: int = 500):
        self.buffer_maxlen = buffer_maxlen
        self.data_buffer: Deque[Dict[str, Any]] = deque(maxlen=buffer_maxlen)
        self.scored_history: Deque[Dict[str, Any]] = deque(maxlen=buffer_maxlen)
        self.is_streaming: bool = False
        self.stream_source: str = "none"  # "serial", "simulation", "none"
        self.current_port: Optional[str] = None
        self.current_baud: int = 115200
        self.stop_event = threading.Event()
        self.worker_thread: Optional[threading.Thread] = None
        self.last_error: Optional[str] = None
        self.broadcast_callback: Optional[Callable[[Dict[str, Any]], Any]] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.alert_manager = AlertManager(load_alert_settings())
        self.incident_log: Deque[Dict[str, Any]] = deque(maxlen=100)

    def set_broadcast_callback(self, callback: Callable[[Dict[str, Any]], Any], loop: asyncio.AbstractEventLoop):
        self.broadcast_callback = callback
        self.loop = loop

    def get_status(self) -> Dict[str, Any]:
        """Return current streaming and connection status."""
        detected = detect_esp32_port()
        return {
            "is_streaming": self.is_streaming,
            "stream_source": self.stream_source,
            "current_port": self.current_port,
            "current_baud": self.current_baud,
            "detected_esp32_port": detected,
            "buffered_samples": len(self.data_buffer),
            "last_error": self.last_error,
            "alerts_enabled": self.alert_manager.settings.enabled,
            "active_alert_channels": self.alert_manager.settings.active_channels(),
        }

    def list_ports(self) -> List[Dict[str, Any]]:
        """List available COM ports with metadata, excluding Bluetooth."""
        ports = []
        for p in list_ports.comports():
            desc = p.description or ""
            if "bluetooth" in desc.lower():
                continue
            is_esp = any(k in desc.lower() for k in ["ch340", "cp210", "usb serial", "usb-serial", "uart", "esp32"])
            ports.append({
                "port": p.device,
                "description": desc,
                "is_esp32": is_esp,
            })
        return ports

    def start_serial_stream(self, port: str = "COM19", baud: int = 115200) -> Dict[str, Any]:
        """Start reading live sensor telemetry from the USB serial port."""
        if self.is_streaming:
            self.stop_stream()

        self.stop_event.clear()
        self.last_error = None
        self.current_port = port
        self.current_baud = baud
        self.stream_source = "serial"
        self.is_streaming = True

        self.worker_thread = threading.Thread(
            target=self._serial_worker,
            args=(port, baud),
            daemon=True,
            name="ESP32-SerialWorker",
        )
        self.worker_thread.start()

        return {"status": "started", "port": port, "baud": baud, "source": "serial"}

    def start_simulation(self, dataset_name: str = "eval_suite", interval_sec: float = 1.0) -> Dict[str, Any]:
        """Start streaming simulated data points from a recorded dataset."""
        if self.is_streaming:
            self.stop_stream()

        self.stop_event.clear()
        self.last_error = None
        self.current_port = f"SIMULATED ({dataset_name})"
        self.stream_source = "simulation"
        self.is_streaming = True

        self.worker_thread = threading.Thread(
            target=self._simulation_worker,
            args=(dataset_name, interval_sec),
            daemon=True,
            name="SimulationWorker",
        )
        self.worker_thread.start()

        return {"status": "started", "dataset": dataset_name, "interval_sec": interval_sec, "source": "simulation"}

    def stop_stream(self) -> Dict[str, Any]:
        """Stop current serial or simulated stream."""
        self.stop_event.set()
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=2.0)
        self.is_streaming = False
        self.stream_source = "none"
        if self.current_port and not self.current_port.startswith("SIMULATED"):
            release_active_serial_port(self.current_port)
        return {"status": "stopped"}

    def _serial_worker(self, port: str, baud: int) -> None:
        """Background worker reading from serial port."""
        ser = None
        last_ts = None
        curr_thread = threading.current_thread()
        try:
            release_active_serial_port(port)
            ser = open_serial_port(port, baudrate=baud, timeout=1.0)
            register_active_serial_port(port, self.stop_event, curr_thread, ser)

            while not self.stop_event.is_set():
                line_bytes = ser.readline()
                if not line_bytes:
                    continue
                parsed = parse_sensor_line(line_bytes.decode("utf-8", errors="ignore"))
                if parsed is None:
                    continue
                temp, hum = parsed
                ts = datetime.now().isoformat(timespec="seconds")
                if ts == last_ts:
                    continue
                last_ts = ts

                raw_item = {"timestamp": ts, "temperature": temp, "humidity": hum}
                self.data_buffer.append(raw_item)

                # Process through inference engine
                scored_frame = inference_service.process_streaming_buffer(list(self.data_buffer))
                if scored_frame:
                    self.scored_history.append(scored_frame)
                    self._handle_alert_evaluation(scored_frame, live_mode=True)
                    self._emit_frame(scored_frame)

        except Exception as exc:
            if not self.stop_event.is_set():
                self.last_error = str(exc)
        finally:
            self.is_streaming = False
            unregister_active_serial_port(port, curr_thread)
            if ser is not None and ser.is_open:
                try:
                    ser.close()
                except Exception:
                    pass

    def _simulation_worker(self, dataset_name: str, interval_sec: float) -> None:
        """Background worker replaying historical dataset rows."""
        file_map = {
            "eval_suite": PROJECT_ROOT / "data" / "processed" / "eval_test_suite.csv",
            "pilot": PROJECT_ROOT / "data" / "processed" / "pilot_data_prepared.csv",
            "test": PROJECT_ROOT / "data" / "processed" / "test_data_with_labels.csv",
        }
        path = file_map.get(dataset_name, file_map["eval_suite"])
        if not path.exists():
            path = PROJECT_ROOT / "data" / "raw" / "test.csv"

        df = pd.read_csv(path)
        row_idx = 0
        total_rows = len(df)

        while not self.stop_event.is_set() and row_idx < total_rows:
            row = df.iloc[row_idx]
            raw_item = {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "temperature": float(row["temperature"]),
                "humidity": float(row["humidity"]),
            }
            self.data_buffer.append(raw_item)

            scored_frame = inference_service.process_streaming_buffer(list(self.data_buffer))
            if scored_frame:
                # Add ground truth if available in source dataset
                if "label" in row:
                    scored_frame["ground_truth_label"] = int(row["label"])
                if "fault_type" in row:
                    scored_frame["ground_truth_fault"] = str(row["fault_type"])

                self.scored_history.append(scored_frame)
                self._handle_alert_evaluation(scored_frame, live_mode=False)
                self._emit_frame(scored_frame)

            row_idx = (row_idx + 1) % total_rows
            time.sleep(interval_sec)

        self.is_streaming = False

    def _handle_alert_evaluation(self, frame: Dict[str, Any], live_mode: bool) -> None:
        """Log incidents and dispatch alerts if enabled."""
        if frame.get("is_anomaly", False):
            incident = {
                "timestamp": frame["timestamp"],
                "temperature": frame["temperature"],
                "humidity": frame["humidity"],
                "trigger": frame["trigger"],
                "hybrid_score": frame["hybrid_score"],
                "severity": "High" if frame["hybrid_score"] > 8.0 else ("Medium" if frame["hybrid_score"] > 4.5 else "Low"),
            }
            # Add to incident log if not duplicate
            if not self.incident_log or self.incident_log[-1]["timestamp"] != incident["timestamp"]:
                self.incident_log.append(incident)

        # Evaluate through AlertManager
        try:
            self.alert_manager.evaluate_latest_row(
                timestamp=frame["timestamp"],
                temperature=frame["temperature"],
                humidity=frame["humidity"],
                is_anomaly=frame["is_anomaly"],
                severity="Medium" if frame["is_anomaly"] else "Low",
                description=f"Anomaly triggered by {frame['trigger']} (Score: {frame['hybrid_score']:.2f})",
                live_mode=live_mode,
            )
        except Exception:
            pass

    def _emit_frame(self, frame: Dict[str, Any]) -> None:
        """Broadcast frame to active WebSocket connections via asyncio loop."""
        if self.broadcast_callback and self.loop and not self.loop.is_closed():
            try:
                asyncio.run_coroutine_threadsafe(self.broadcast_callback(frame), self.loop)
            except Exception:
                pass


# Singleton instance
serial_service = SerialService()
