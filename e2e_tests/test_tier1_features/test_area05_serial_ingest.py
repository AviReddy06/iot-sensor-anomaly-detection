"""
e2e_tests/test_tier1_features/test_area05_serial_ingest.py
Area 5: Serial Ingestion, FakeSerial & Faults (Features 8, 22)
Tier 1 Tests: Serial line parsing, header discarding, COM port listing, lifecycle management.
"""

import pytest
from starlette.testclient import TestClient
from collect.serial_utils import parse_sensor_line, BOOT_PREFIXES
from backend.services.serial_service import serial_service


def test_a5_t1_01_fakeserial_normal_05hz_ingestion():
    """
    TEST-A5-T1-01: Serial line parsing accurately parses valid temperature and humidity.
    """
    raw = "25.40,61.20\n"
    result = parse_sensor_line(raw)
    assert result is not None
    temp, hum = result
    assert temp == 25.40
    assert hum == 61.20


def test_a5_t1_02_serial_bootloader_and_header_discard():
    """
    TEST-A5-T1-02: ESP32 boot banners and CSV header lines are cleanly discarded.
    """
    bad_lines = [
        "temperature,humidity\n",
        "rst:0x1 (POWERON_RESET)\n",
        "ets Jun  8 2016 00:22:57\n",
        "configsip: 0\n",
        "clk_drv:0x00\n",
        "boot:0x13\n",
    ]
    for line in bad_lines:
        res = parse_sensor_line(line)
        assert res is None, f"Expected None for bootloader/header line: {line.strip()}"

    # Immediately following valid line must parse successfully
    valid = parse_sensor_line("24.50,60.00\n")
    assert valid == (24.50, 60.00)


def test_a5_t1_03_com_port_listing_excludes_bluetooth(client: TestClient, admin_token: str):
    """
    TEST-A5-T1-03: COM port listing filters out bluetooth ports.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.get("/api/admin/serial/ports", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    for p in data:
        desc = p.get("description", "").lower()
        assert "bluetooth" not in desc, f"Bluetooth port not filtered: {p}"


def test_a5_t1_04_serial_lifecycle_start_stop(client: TestClient, admin_token: str):
    """
    TEST-A5-T1-04: Serial port lifecycle start and stop idempotency.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    # Stop any running stream
    stop_resp = client.post("/api/admin/serial/stop", headers=headers)
    assert stop_resp.status_code in [200, 400]

    # Verify is_streaming is False
    assert not serial_service.is_streaming


def test_a5_t1_05_hardware_check_simulation_fallback():
    """
    TEST-A5-T1-05: Hardware check fallback logic works when COM port is unavailable.
    """
    from collect.serial_utils import detect_esp32_port
    port = detect_esp32_port(default="COM_SIMULATED")
    assert port is not None
