"""
e2e_tests/test_tier2_boundaries/test_area09_boundary.py
Area 9 Boundary & Security Abuse Tests (Features 13, 14)
Tier 2 Tests: >5MB upload rejection, non-CSV rejection, binary upload, wrong headers, path traversal, formula injection escaping.
"""

import io
import pytest
from starlette.testclient import TestClient
from backend.database import insert_event


def test_a9_t2_01_upload_file_size_exceeding_5mb_rejected(client: TestClient):
    """
    TEST-A9-T2-01: Files exceeding 5 MB limit (5,242,880 bytes) must be rejected with 413 or 422.
    """
    # 5.2 MB file composed of header + comments padding
    header = b"timestamp,temperature,humidity\n2026-11-15 10:00:00,25.0,60.0\n"
    padding = b"# " + (b"X" * (5250000 - len(header))) + b"\n"
    large_payload = header + padding
    assert len(large_payload) > 5 * 1024 * 1024  # > 5MB
    files = {"file": ("large.csv", io.BytesIO(large_payload), "text/csv")}
    resp = client.post("/api/datasets/upload", files=files)
    if resp.status_code == 404:
        resp = client.post("/datasets/upload", files=files)
    # Expected: 413 (Payload Too Large), 422, or 400
    assert resp.status_code in [400, 413, 422]


def test_a9_t2_02_upload_non_csv_extension_rejected(client: TestClient):
    """
    TEST-A9-T2-02: Non-CSV file extensions (.exe, .py, .sh) are rejected.
    """
    files = {"file": ("script.py", io.BytesIO(b"print('malicious')"), "text/x-python")}
    resp = client.post("/api/datasets/upload", files=files)
    if resp.status_code == 404:
        resp = client.post("/datasets/upload", files=files)
    assert resp.status_code in [400, 422]


def test_a9_t2_03_upload_binary_content_rejected(client: TestClient):
    """
    TEST-A9-T2-03: Binary content disguised as .csv is rejected cleanly without 500 crash.
    """
    binary_data = b"\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    files = {"file": ("fake.csv", io.BytesIO(binary_data), "text/csv")}
    resp = client.post("/api/datasets/upload", files=files)
    if resp.status_code == 404:
        resp = client.post("/datasets/upload", files=files)
    assert resp.status_code in [400, 422]


def test_a9_t2_04_upload_wrong_csv_headers_rejected(client: TestClient):
    """
    TEST-A9-T2-04: CSV with missing required columns (e.g. name,age instead of timestamp,temp,hum) rejected.
    """
    bad_csv = "name,age,email\nalice,30,alice@example.com\n"
    files = {"file": ("bad_headers.csv", io.BytesIO(bad_csv.encode("utf-8")), "text/csv")}
    resp = client.post("/api/datasets/upload", files=files)
    if resp.status_code == 404:
        resp = client.post("/datasets/upload", files=files)
    assert resp.status_code in [400, 422]


def test_a9_t2_05_path_traversal_rejection_dataset_download(client: TestClient, admin_token: str):
    """
    TEST-A9-T2-05: Path traversal sequences (../, ..\\, %2e%2e) rejected on download route.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    traversal_paths = [
        "%2e%2e%2f%2e%2e%2f%2e%2e%2fWindows%2fwin.ini",
        "%2e%2e%2f%2e%2e%2fbackend%2fconfig.py",
        "%2e%2e%2fconfig.py",
    ]
    for p in traversal_paths:
        resp = client.get(f"/api/admin/datasets/download/{p}", headers=headers)
        assert resp.status_code in [400, 403, 404], f"Path traversal not blocked for {p}: {resp.status_code}"
        assert "win.ini" not in resp.text
        assert "ADMIN_PASSWORD" not in resp.text


def test_a9_t2_06_path_traversal_rejection_dataset_analysis(client: TestClient):
    """
    TEST-A9-T2-06: Path traversal attempts on dataset analysis route are rejected.
    """
    resp = client.get("/api/datasets/../../backend/config.py")
    assert resp.status_code in [400, 404]


def test_a9_t2_07_csv_export_formula_injection_escaping(client: TestClient, admin_token: str):
    """
    TEST-A9-T2-07: CSV Formula Injection (CWE-1236) neutralization:
    Values starting with =, +, -, @ must be prefixed with an apostrophe (').
    """
    formula_trigger = "=cmd|' /C calc'!A0"
    insert_event(
        start_time="2026-11-15T12:00:00Z",
        end_time="2026-11-15T12:00:10Z",
        duration_sec=10.0,
        peak_temp=30.0,
        peak_hum=70.0,
        delta_temp=4.0,
        what_changed=formula_trigger,
        severity="Medium",
        sentence=formula_trigger,
    )

    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = client.get("/api/admin/alerts/export", headers=headers)
    assert resp.status_code == 200
    export_text = resp.text

    # Escaping contract: if cell begins with =, +, -, @, must be prepended with '
    for line in export_text.splitlines():
        if "=cmd" in line:
            assert "'=cmd" in line, f"Formula injection not escaped with leading apostrophe in: {line}"
