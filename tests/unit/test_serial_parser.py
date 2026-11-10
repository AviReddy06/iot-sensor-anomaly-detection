"""Unit tests for serial parsing and port helpers (`collect/serial_utils.py`)."""

from __future__ import annotations

import pytest

from collect.serial_utils import detect_esp32_port, list_serial_ports, parse_sensor_line


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
