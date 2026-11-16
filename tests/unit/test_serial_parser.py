"""Unit tests for serial parsing and port helpers (`collect/serial_utils.py`)."""

from __future__ import annotations

import pytest

from collect.serial_utils import (
    detect_esp32_port,
    list_serial_ports,
    parse_sensor_line,
    register_active_serial_port,
    release_active_serial_port,
    unregister_active_serial_port,
)


@pytest.mark.parametrize(
    "line,expected",
    [
        ("25.90,60.80\n", (25.9, 60.8)),
        ("  29.55 , 53.70 \r\n", (29.55, 53.7)),
        ("0.0,100.0", (0.0, 100.0)),
        ("-10.0,0.0", (-10.0, 0.0)),
        ("65.0,99.9", (65.0, 99.9)),
    ],
)
def test_parse_sensor_line_valid(line, expected):
    assert parse_sensor_line(line) == expected


@pytest.mark.parametrize(
    "bad_line",
    [
        "",
        "   \r\n",
        "temperature,humidity",
        "humidity,temperature",
        "ets Jul 29 2019 12:21:46",
        "rst:0x1 (POWERON_RESET),boot:0x13",
        "nan,nan",
        "26.5,nan",
        "inf,55.0",
        "25.5",
        "25.5,60.0,10.0",
        "abc,def",
        "99.0,55.0",      # out of physical temp upper bound (65.0)
        "-25.0,55.0",     # out of physical temp lower bound (-10.0)
        "25.0,105.0",     # out of physical humidity upper bound (100.0)
        "25.0,-1.0",      # out of physical humidity lower bound (0.0)
    ],
)
def test_parse_sensor_line_rejects_invalid_and_noise(bad_line):
    assert parse_sensor_line(bad_line) is None


def test_list_serial_ports_returns_list():
    ports = list_serial_ports()
    assert isinstance(ports, list)
    for item in ports:
        assert isinstance(item, tuple) and len(item) == 2


def test_detect_esp32_port_returns_string():
    port = detect_esp32_port()
    assert isinstance(port, str) and len(port) > 0


def test_active_serial_port_reclaim_stops_and_closes_previous():
    import threading
    from unittest.mock import MagicMock

    stop_ev = threading.Event()
    mock_ser = MagicMock()
    dummy_thread = threading.Thread(target=lambda: stop_ev.wait(timeout=1.0), daemon=True)
    dummy_thread.start()

    register_active_serial_port("COM99", stop_ev, dummy_thread, mock_ser)
    released = release_active_serial_port("com99")

    assert released is True
    assert stop_ev.is_set()
    mock_ser.close.assert_called_once()
    assert not dummy_thread.is_alive()

    # Releasing again cleanly returns False
    assert release_active_serial_port("COM99") is False
    unregister_active_serial_port("COM99", dummy_thread)


def test_bluetooth_filtering_and_port_preference(monkeypatch):
    import serial.tools.list_ports

    class FakePort:
        def __init__(self, device, description, hwid=""):
            self.device = device
            self.description = description
            self.hwid = hwid

    fake_ports = [
        FakePort("COM1", "Communications Port (COM1)", "ACPI\\PNP0501"),
        FakePort("COM10", "Standard Serial over Bluetooth link (COM10)", "BTHENUM\\{...}"),
        FakePort("COM7", "Silicon Labs CP210x USB to UART Bridge (COM7)", "USB VID:PID=10C4:EA60"),
        FakePort("COM3", "USB-SERIAL CH340 (COM3)", "USB VID:PID=1A86:7523"),
        FakePort("COM11", "Bluetooth Device (COM11)", "BTHENUM\\{...}"),
    ]
    monkeypatch.setattr(serial.tools.list_ports, "comports", lambda: fake_ports)

    available = list_serial_ports()
    port_names = [p[0] for p in available]

    # Bluetooth devices must be completely filtered out
    assert "COM10" not in port_names
    assert "COM11" not in port_names

    # USB-UART adapters must be prioritized before generic communications ports
    assert port_names == ["COM3", "COM7", "COM1"]
