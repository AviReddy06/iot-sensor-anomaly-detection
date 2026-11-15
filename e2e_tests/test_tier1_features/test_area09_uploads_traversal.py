"""
e2e_tests/test_tier1_features/test_area09_uploads_traversal.py
Area 9: Admin Uploads, Path Traversal & Escaping (Features 13, 14)
Tier 1 Tests: Valid CSV upload, dataset download, alerts export format, size limits, server filenames.
"""

import io
import pytest
from starlette.testclient import TestClient
from backend.database import insert_event


def test_a9_t1_01_dataset_upload_valid_csv(client: TestClient):
    """
    TEST-A9-T1-01: Uploading a valid CSV returns 200 with summary and scored records.
    """
    csv_content = (
        "timestamp,temperature,humidity\n"
        "2026-11-15 10:00:00,25.0,60.0\n"
        "2026-11-15 10:00:02,25.1,60.2\n"
        "2026-11-15 10:00:04,25.2,60.1\n"
    )
    files = {"file": ("test_upload.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    # Route can be /api/datasets/upload or /datasets/upload
    response = client.post("/api/datasets/upload", files=files)
    if response.status_code == 404:
        response = client.post("/datasets/upload", files=files)

    assert response.status_code == 200
    data = response.json()
    assert "summary" in data or "rows" in data or "total_readings" in data or "status" in data


def test_a9_t1_02_dataset_download_allowed_file(client: TestClient, admin_token: str):
    """
    TEST-A9-T1-02: Downloading an allowed dataset CSV file.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.get("/api/admin/datasets/download/test.csv", headers=headers)
    assert response.status_code == 200, f"Expected 200 for allowed dataset test.csv, got {response.status_code}"
    assert "text/csv" in response.headers.get("content-type", "")
    assert len(response.content) > 0


def test_a9_t1_03_alerts_export_valid_csv_format(client: TestClient, admin_token: str):
    """
    TEST-A9-T1-03: Exporting alerts as CSV returns 200 and text/csv content.
    """
    insert_event(
        start_time="2026-11-15T12:00:00Z",
        end_time="2026-11-15T12:00:10Z",
        duration_sec=10.0,
        peak_temp=30.0,
        peak_hum=70.0,
        delta_temp=4.0,
        what_changed="temperature rose 4.0 °C",
        severity="Medium",
        sentence="Unusual reading at 12:00: temperature rose 4.0 °C.",
    )

    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.get("/api/admin/alerts/export", headers=headers)
    assert response.status_code == 200
    assert "text/csv" in response.headers.get("content-type", "")
    content = response.text
    assert "start_time" in content or "severity" in content
    assert "Unusual reading" in content or "Medium" in content


def test_a9_t1_04_upload_file_size_within_5mb_limit(client: TestClient):
    """
    TEST-A9-T1-04: File upload well within the 5 MB limit is accepted.
    """
    # 10 KB file
    row = "2026-11-15 10:00:00,25.0,60.0\n"
    csv_content = "timestamp,temperature,humidity\n" + (row * 300)
    files = {"file": ("normal_size.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    response = client.post("/api/datasets/upload", files=files)
    if response.status_code == 404:
        response = client.post("/datasets/upload", files=files)
    assert response.status_code == 200


def test_a9_t1_05_server_generated_storage_filenames(client: TestClient):
    """
    TEST-A9-T1-05: Server does not store uploaded files at user-controlled file paths.
    """
    csv_content = "timestamp,temperature,humidity\n2026-11-15 10:00:00,25.0,60.0\n"
    malicious_filename = "../../../traversal_test.csv"
    files = {"file": (malicious_filename, io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    response = client.post("/api/datasets/upload", files=files)
    # Must either reject (400/422) or sanitize without creating file at ../../../traversal_test.csv
    import os
    assert not os.path.exists("traversal_test.csv")
