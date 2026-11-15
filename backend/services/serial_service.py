"""
backend/services/serial_service.py
Manages live USB serial streaming from ESP32, simulated dataset playback,
and real-time WebSocket frame broadcasting.
Resilient reconnect loop with exponential backoff (1s, 2s, 4s, 8s, 16s),
ingest burst loss fix, consecutive identical temp==hum tracking, and 60s stream silence detection.
"""

from __future__ import annotations

import asyncio
from collections import deque
from datetime import datetime, timezone
import json
from pathlib import Path
import queue
import sys
import threading
import time
from typing import Any, Callable, Deque, Dict, List, Optional, Set, Tuple

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
from backend.database import insert_reading
from backend.services.events_service import events_service
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

        # R3 Metrics, Concurrency & Health tracking
        self._state_lock = threading.RLock()
        self.serial_state: str = "disconnected"  # "connected", "disconnected", "reconnecting", "offline", "fault", "simulating"
        self.reconnect_attempts: int = 0
        self.consecutive_identical_count: int = 0
        self.consecutive_identical_flag: bool = False
        self.last_reading_time: Optional[str] = None
        self.last_reading_monotonic: Optional[float] = None
        self.total_readings_count: int = 0
        self.total_lines_read: int = 0
        self.rejected_lines_count: int = 0

    def _reset_stream_state(self) -> None:
        """Clear sliding buffers, reset event tracking, and reset monotonic timestamp tracker."""
        self.data_buffer.clear()
        self.scored_history.clear()
        events_service.reset()
        with self._state_lock:
            self.consecutive_identical_count = 0
            self.consecutive_identical_flag = False
            self.last_error = None
            self.last_reading_time = None
            self.last_reading_monotonic = None
            self.total_readings_count = 0
            self.total_lines_read = 0
            self.rejected_lines_count = 0
            self.reconnect_attempts = 0
        try:
            from backend.routes.ws_routes import ws_manager
            ws_manager.reset_tracker()
        except Exception:
            pass

    def set_broadcast_callback(self, callback: Callable[[Dict[str, Any]], Any], loop: asyncio.AbstractEventLoop):
        self.broadcast_callback = callback
        self.loop = loop

    def get_serial_state(self) -> str:
        """Determine normalized serial connection state."""
        with self._state_lock:
            if not self.is_streaming:
                return "disconnected"
            if self.stream_source == "simulation":
                return "simulating"
            if self.last_reading_monotonic is not None and (time.monotonic() - self.last_reading_monotonic) >= 60.0:
                self.serial_state = "offline"
                return "offline"
            if self.serial_state in ("disconnected", "reconnecting", "connecting", "offline"):
                return self.serial_state
            if self.last_error:
                return "fault"
            return self.serial_state or "connected"

    def get_status(self) -> Dict[str, Any]:
        """Return current streaming and connection status."""
        detected = detect_esp32_port()
        with self._state_lock:
            age_sec = None
            if self.last_reading_monotonic is not None:
                age_sec = round(max(0.0, time.monotonic() - self.last_reading_monotonic), 2)
            state = self.get_serial_state()
            err = self.last_error
            c_count = self.consecutive_identical_count
            c_flag = self.consecutive_identical_flag

        return {
            "is_streaming": self.is_streaming,
            "stream_source": self.stream_source,
            "current_port": self.current_port,
            "current_baud": self.current_baud,
            "detected_esp32_port": detected,
            "buffered_samples": len(self.data_buffer),
            "last_error": err,
            "serial_state": state,
            "last_reading_age_seconds": age_sec,
            "consecutive_identical_count": c_count,
            "sensor_fault_flag": c_flag,
            "alerts_enabled": self.alert_manager.settings.enabled,
            "active_alert_channels": self.alert_manager.settings.active_channels(),
        }

    def get_health_status(self) -> Dict[str, Any]:
        """Provide detailed telemetry health to /api/health."""
        with self._state_lock:
            age_sec = None
            if self.last_reading_monotonic is not None:
                age_sec = round(max(0.0, time.monotonic() - self.last_reading_monotonic), 2)

            state = self.get_serial_state()

            fault_warning = None
            if self.consecutive_identical_flag:
                fault_warning = "humidity identical to temperature for >= 30 readings (suspected sensor fault)"

            return {
                "serial_state": state,
                "last_reading_time": self.last_reading_time,
                "last_reading_age_seconds": age_sec,
                "consecutive_identical_count": self.consecutive_identical_count,
                "sensor_fault_flag": self.consecutive_identical_flag,
                "sensor_fault_warning": fault_warning,
                "reconnect_attempts": self.reconnect_attempts,
                "total_readings_count": self.total_readings_count,
                "total_lines_read": self.total_lines_read,
                "rejected_lines_count": self.rejected_lines_count,
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
        # Add FAKE test port option
        ports.append({
            "port": "FAKE",
            "description": "FakeSerial Test Double (ESP32+DHT11 Telemetry Simulator)",
            "is_esp32": True,
        })
        return ports

    def start_serial_stream(
        self,
        port: str = "COM19",
        baud: int = 115200,
        serial_instance: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Start reading live sensor telemetry from the USB serial port or test double."""
        if self.is_streaming:
            self.stop_stream()
        self._reset_stream_state()

        self.stop_event.clear()
        self.last_error = None
        self.current_port = port
        self.current_baud = baud
        self.stream_source = "serial"
        self.is_streaming = True
        with self._state_lock:
            self.serial_state = "connecting"
            self.reconnect_attempts = 0

        self.worker_thread = threading.Thread(
            target=self._serial_worker,
            args=(port, baud, serial_instance),
            daemon=True,
            name="ESP32-SerialWorker",
        )
        self.worker_thread.start()

        return {"status": "started", "port": port, "baud": baud, "source": "serial"}

    def start_simulation(
        self,
        dataset_name: str = "eval_suite",
        interval_sec: float = 1.0,
        loop: bool = False,
    ) -> Dict[str, Any]:
        """Start streaming simulated data points from a recorded dataset."""
        if self.is_streaming:
            self.stop_stream()
        self._reset_stream_state()

        self.stop_event.clear()
        self.last_error = None
        self.current_port = f"SIMULATED ({dataset_name})"
        self.stream_source = "simulation"
        self.is_streaming = True
        with self._state_lock:
            self.serial_state = "simulating"

        self.worker_thread = threading.Thread(
            target=self._simulation_worker,
            args=(dataset_name, interval_sec, loop),
            daemon=True,
            name="SimulationWorker",
        )
        self.worker_thread.start()

        return {"status": "started", "dataset": dataset_name, "interval_sec": interval_sec, "loop": loop, "source": "simulation"}

    def stop_stream(self) -> Dict[str, Any]:
        """Stop current serial or simulated stream."""
        self.stop_event.set()
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=2.0)
        events_service.flush()
        events_service.reset()
        try:
            from backend.routes.ws_routes import ws_manager
            ws_manager.reset_tracker()
        except Exception:
            pass
        self.is_streaming = False
        self.stream_source = "none"
        with self._state_lock:
            self.serial_state = "disconnected"
        if self.current_port and not self.current_port.startswith("SIMULATED"):
            release_active_serial_port(self.current_port)
        return {"status": "stopped"}

    def _parse_stream_line(self, line_str: str) -> Optional[Tuple[Optional[str], float, float]]:
        """Parse raw stream line supporting both 'temp,hum' and 'timestamp,temp,hum'."""
        clean = line_str.strip()
        if not clean:
            return None
        parts = clean.split(",")
        if len(parts) == 2:
            parsed = parse_sensor_line(clean)
            if parsed is None:
                return None
            return None, parsed[0], parsed[1]
        elif len(parts) == 3:
            ts_candidate = parts[0].strip()
            parsed = parse_sensor_line(f"{parts[1]},{parts[2]}")
            if parsed is None:
                return None
            return ts_candidate, parsed[0], parsed[1]
        return None

    def _evaluate_offline_status(self) -> None:
        """Check if telemetry stream has been silent for 60s."""
        with self._state_lock:
            if self.last_reading_monotonic is not None:
                elapsed = time.monotonic() - self.last_reading_monotonic
                if elapsed >= 60.0:
                    self.serial_state = "offline"

    def _serial_worker(self, port: str, baud: int, serial_double: Optional[Any] = None) -> None:
        """Background worker reading from serial port with automatic backoff reconnection."""
        ser = serial_double
        curr_thread = threading.current_thread()
        backoff = 1.0
        max_backoff = 16.0

        try:
            while not self.stop_event.is_set():
                # Step 1: Connect if port not open
                if ser is None or not getattr(ser, "is_open", False):
                    try:
                        with self._state_lock:
                            self.serial_state = "reconnecting" if self.reconnect_attempts > 0 else "connecting"
                        release_active_serial_port(port)
                        ser = open_serial_port(port, baudrate=baud, timeout=1.0)
                        register_active_serial_port(port, self.stop_event, curr_thread, ser)
                        with self._state_lock:
                            self.serial_state = "connected"
                            self.reconnect_attempts = 0
                            self.last_error = None
                        backoff = 1.0
                    except (serial.SerialException, OSError, Exception) as conn_exc:
                        with self._state_lock:
                            self.reconnect_attempts += 1
                            self.serial_state = "disconnected"
                            self.last_error = str(conn_exc)
                        if self.stop_event.wait(timeout=backoff):
                            break
                        backoff = min(backoff * 2.0, max_backoff)
                        continue

                # Step 2: Read line from serial stream
                try:
                    line_bytes = ser.readline()
                except (serial.SerialException, OSError, Exception) as read_exc:
                    with self._state_lock:
                        self.last_error = str(read_exc)
                        self.serial_state = "disconnected"
                        self.reconnect_attempts += 1
                    if ser is not None:
                        try:
                            ser.close()
                        except Exception:
                            pass
                        ser = None
                    if self.stop_event.wait(timeout=backoff):
                        break
                    backoff = min(backoff * 2.0, max_backoff)
                    continue

                if not line_bytes:
                    # Check offline threshold (60s without reading)
                    self._evaluate_offline_status()
                    if self.stop_event.wait(timeout=0.05):
                        break
                    continue

                with self._state_lock:
                    self.total_lines_read += 1
                line_str = line_bytes.decode("utf-8", errors="ignore")

                # Step 3: Parse line (handles 2-part and 3-part timestamped rows)
                parsed = self._parse_stream_line(line_str)
                if parsed is None:
                    with self._state_lock:
                        self.rejected_lines_count += 1
                    continue

                explicit_ts, temp, hum = parsed
                ts = explicit_ts or datetime.now(timezone.utc).isoformat()

                # Step 4: Track health metrics (consecutive temp == hum)
                with self._state_lock:
                    self.last_reading_time = ts
                    self.last_reading_monotonic = time.monotonic()
                    self.total_readings_count += 1
                    self.serial_state = "connected"

                    if abs(temp - hum) < 1e-4:
                        self.consecutive_identical_count += 1
                        if self.consecutive_identical_count >= 30:
                            self.consecutive_identical_flag = True
                    else:
                        self.consecutive_identical_count = 0
                        self.consecutive_identical_flag = False

                # Step 5: Buffer, persist, score, and broadcast (NO burst-loss second deduplication)
                raw_item = {"timestamp": ts, "temperature": temp, "humidity": hum}
                self.data_buffer.append(raw_item)
                insert_reading(timestamp=ts, temperature=temp, humidity=hum, is_simulated=False)

                scored_frame = inference_service.process_streaming_buffer(list(self.data_buffer))
                if scored_frame:
                    self.scored_history.append(scored_frame)
                    self._handle_alert_evaluation(scored_frame, live_mode=True)
                    events_service.process_sample(
                        timestamp_str=scored_frame["timestamp"],
                        temperature=scored_frame["temperature"],
                        humidity=scored_frame["humidity"],
                        is_flagged=scored_frame["is_anomaly"],
                        peak_z=scored_frame["hybrid_score"],
                    )
                    self._emit_frame(scored_frame)

        except Exception as exc:
            if not self.stop_event.is_set():
                with self._state_lock:
                    self.last_error = str(exc)
        finally:
            events_service.flush()
            with self._state_lock:
                self.is_streaming = False
                self.serial_state = "disconnected"
            unregister_active_serial_port(port, curr_thread)
            if ser is not None and getattr(ser, "is_open", False):
                try:
                    ser.close()
                except Exception:
                    pass

    def _simulation_worker(self, dataset_name: str, interval_sec: float, loop: bool = False) -> None:
        """Background worker replaying historical dataset rows."""
        file_map = {
            "eval_suite": PROJECT_ROOT / "data" / "processed" / "eval_test_suite.csv",
            "pilot": PROJECT_ROOT / "data" / "processed" / "pilot_data_prepared.csv",
            "test": PROJECT_ROOT / "data" / "processed" / "test_data_with_labels.csv",
        }
        if dataset_name in file_map:
            path = file_map[dataset_name]
        elif (PROJECT_ROOT / dataset_name).exists():
            path = PROJECT_ROOT / dataset_name
        elif (PROJECT_ROOT / "data" / "processed" / dataset_name).exists():
            path = PROJECT_ROOT / "data" / "processed" / dataset_name
        elif Path(dataset_name).exists():
            path = Path(dataset_name)
        else:
            path = file_map.get("eval_suite", PROJECT_ROOT / "data" / "raw" / "test.csv")

        df = pd.read_csv(path)
        row_idx = 0
        total_rows = len(df)

        try:
            while not self.stop_event.is_set() and row_idx < total_rows:
                row = df.iloc[row_idx]
                ts = str(row["timestamp"])
                temp = float(row["temperature"])
                hum = float(row["humidity"])
                raw_item = {
                    "timestamp": ts,
                    "temperature": temp,
                    "humidity": hum,
                }
                self.data_buffer.append(raw_item)

                with self._state_lock:
                    self.last_reading_time = ts
                    self.last_reading_monotonic = time.monotonic()
                    self.total_readings_count += 1
                    self.serial_state = "simulating"

                    if abs(temp - hum) < 1e-4:
                        self.consecutive_identical_count += 1
                        if self.consecutive_identical_count >= 30:
                            self.consecutive_identical_flag = True
                    else:
                        self.consecutive_identical_count = 0
                        self.consecutive_identical_flag = False

                # Persist reading to database
                insert_reading(timestamp=ts, temperature=temp, humidity=hum, is_simulated=True)

                scored_frame = inference_service.process_streaming_buffer(list(self.data_buffer))
                if scored_frame:
                    if "label" in row:
                        scored_frame["ground_truth_label"] = int(row["label"])
                    if "fault_type" in row:
                        scored_frame["ground_truth_fault"] = str(row["fault_type"])

                    self.scored_history.append(scored_frame)
                    self._handle_alert_evaluation(scored_frame, live_mode=False)

                    events_service.process_sample(
                        timestamp_str=scored_frame["timestamp"],
                        temperature=scored_frame["temperature"],
                        humidity=scored_frame["humidity"],
                        is_flagged=scored_frame["is_anomaly"],
                        peak_z=scored_frame["hybrid_score"],
                    )

                    self._emit_frame(scored_frame)

                if loop:
                    row_idx = (row_idx + 1) % total_rows
                    if row_idx == 0:
                        self.data_buffer.clear()
                        events_service.flush()
                        events_service.reset()
                        try:
                            from backend.routes.ws_routes import ws_manager
                            ws_manager.reset_tracker()
                        except Exception:
                            pass
                else:
                    row_idx += 1

                if interval_sec > 0:
                    if self.stop_event.wait(interval_sec):
                        break
        except Exception as exc:
            if not self.stop_event.is_set():
                with self._state_lock:
                    self.last_error = str(exc)
        finally:
            events_service.flush()
            self.is_streaming = False
            with self._state_lock:
                self.serial_state = "disconnected"

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
            if not self.incident_log or self.incident_log[-1]["timestamp"] != incident["timestamp"]:
                self.incident_log.append(incident)

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
