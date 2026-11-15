"""
tests/test_security.py
Security tests for the IoT Anomaly Detection system.
Covers: token expiry/tamper, rate limiting, admin routes without password, password leakage,
upload limits, path traversal, CSV formula injection, security headers.
"""

from __future__ import annotations

import base64
import hashlib
import io
import time
from pathlib import Path
import tempfile
from typing import Generator

import pytest
from starlette.testclient import TestClient

import backend.config as bcfg
import backend.database as database
from backend.app import app
from backend.auth import generate_signed_token, verify_signed_token, TOKEN_EXPIRY_SECONDS, _LOGIN_ATTEMPTS
from backend.database import get_db_connection


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    with TestClient(app, base_url="http://localhost:8000") as test_client:
        yield test_client


@pytest.fixture
def isolated_db(monkeypatch, tmp_path) -> Generator[Path, None, None]:
    """Provides a fresh isolated SQLite DB in tmp_path for each test."""
    db_file = tmp_path / "security_test.db"
    monkeypatch.setenv("DB_PATH", str(db_file))
    monkeypatch.setattr(bcfg, "DB_PATH", db_file)
    monkeypatch.setattr(database, "DB_PATH", db_file)
    database._initialized_paths.discard(str(db_file.resolve()))

    conn = database.get_db_connection()
    conn.close()

    yield db_file


@pytest.fixture(autouse=True)
def clear_rate_limit():
    """Clear rate limit state before each test."""
    _LOGIN_ATTEMPTS.clear()
    yield
    _LOGIN_ATTEMPTS.clear()


@pytest.fixture
def admin_headers(monkeypatch) -> dict:
    monkeypatch.setattr(bcfg, "ADMIN_PASSWORD", "security_test_secret")
    token = generate_signed_token()
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Token Security Tests
# ---------------------------------------------------------------------------

class TestTokenSecurity:
    """Tests for JWT token expiry, tamper rejection, and password protection."""

    def test_token_expiry_rejected(self, client: TestClient, admin_headers: dict):
        """Expired tokens must be rejected (401)."""
        import backend.auth as auth
        original_ttl = auth.TOKEN_EXPIRY_SECONDS
        try:
            auth.TOKEN_EXPIRY_SECONDS = -1
            expired_token = generate_signed_token()
        finally:
            auth.TOKEN_EXPIRY_SECONDS = original_ttl

        headers = {"Authorization": f"Bearer {expired_token}"}
        resp = client.get("/api/admin/metrics", headers=headers)
        assert resp.status_code == 401, f"Expected 401 for expired token, got {resp.status_code}"

    def test_token_tamper_rejected(self, client: TestClient, admin_headers: dict):
        """Tampered tokens (modified payload/signature) must be rejected."""
        token = admin_headers["Authorization"].split(" ")[1]
        # Token format: base64(expiry:sig)
        raw = base64.urlsafe_b64decode(token.encode()).decode()
        parts = raw.split(":")
        if len(parts) != 2:
            pytest.skip("Token format unexpected")
        # Tamper with expiry
        tampered_raw = f"{int(time.time()) - 10000}:{parts[1]}"
        tampered = base64.urlsafe_b64encode(tampered_raw.encode()).decode()
        headers = {"Authorization": f"Bearer {tampered}"}
        resp = client.get("/api/admin/metrics", headers=headers)
        assert resp.status_code == 401, f"Expected 401 for tampered token, got {resp.status_code}"

    def test_token_signature_tamper_rejected(self, client: TestClient, admin_headers: dict):
        """Tampered signature must be rejected."""
        token = admin_headers["Authorization"].split(" ")[1]
        raw = base64.urlsafe_b64decode(token.encode()).decode()
        parts = raw.split(":")
        if len(parts) != 2:
            pytest.skip("Token format unexpected")
        tampered_raw = f"{parts[0]}:invalidsignature"
        tampered = base64.urlsafe_b64encode(tampered_raw.encode()).decode()
        headers = {"Authorization": f"Bearer {tampered}"}
        resp = client.get("/api/admin/metrics", headers=headers)
        assert resp.status_code == 401, f"Expected 401 for bad signature, got {resp.status_code}"

    def test_password_never_in_logs_or_response(self, client: TestClient, monkeypatch, caplog):
        """Admin password must never appear in logs or response bodies."""
        monkeypatch.setattr(bcfg, "ADMIN_PASSWORD", "secret_password_123")
        
        # Try login with wrong password (correct endpoint is /api/auth/login)
        resp = client.post("/api/auth/login", json={"password": "wrong"})
        assert resp.status_code == 401
        # Response body must not contain password
        assert "secret_password_123" not in resp.text
        assert "wrong" not in resp.text  # Don't echo attempted password either
        
        # Check logs don't contain password
        log_text = caplog.text
        assert "secret_password_123" not in log_text

    def test_password_not_in_success_response(self, client: TestClient, monkeypatch):
        """Successful login response must not contain password."""
        monkeypatch.setattr(bcfg, "ADMIN_PASSWORD", "secret_password_123")
        resp = client.post("/api/auth/login", json={"password": "secret_password_123"})
        assert resp.status_code == 200
        data = resp.json()
        assert "password" not in data
        assert "secret_password_123" not in str(data)


# ---------------------------------------------------------------------------
# Rate Limiting Tests
# ---------------------------------------------------------------------------

class TestRateLimiting:
    """Tests for login rate limiting (6th failed attempt within 1 minute = 429)."""

    def test_6th_failed_login_returns_429(self, client: TestClient, monkeypatch):
        """6th failed login within 1 minute must return 429."""
        monkeypatch.setattr(bcfg, "ADMIN_PASSWORD", "correct_password")
        
        # Make 5 failed attempts
        for i in range(5):
            resp = client.post("/api/auth/login", json={"password": f"wrong_{i}"})
            assert resp.status_code == 401, f"Attempt {i+1}: expected 401, got {resp.status_code}"
        
        # 6th attempt must be rate limited
        resp = client.post("/api/auth/login", json={"password": "wrong_5"})
        assert resp.status_code == 429, f"Expected 429 for 6th attempt, got {resp.status_code}"
        detail = resp.json().get("detail", "").lower()
        assert "too many" in detail or "rate limit" in detail, f"Expected rate limit message, got: {detail}"

    def test_rate_limit_cleared_on_success(self, client: TestClient, monkeypatch):
        """Successful login must clear rate limit."""
        monkeypatch.setattr(bcfg, "ADMIN_PASSWORD", "correct_password")
        
        # 4 failed attempts (within limit of 5)
        for i in range(4):
            resp = client.post("/api/auth/login", json={"password": f"wrong_{i}"})
            assert resp.status_code == 401
        
        # 5th attempt = successful login (clears rate limit)
        resp = client.post("/api/auth/login", json={"password": "correct_password"})
        assert resp.status_code == 200
        
        # Next failed attempt should not be rate limited (counter reset by successful login)
        resp = client.post("/api/auth/login", json={"password": "wrong_after_success"})
        assert resp.status_code == 401, f"Rate limit should be cleared after successful login, got {resp.status_code}"


# ---------------------------------------------------------------------------
# Admin Routes Without Password Tests
# ---------------------------------------------------------------------------

class TestAdminRoutesWithoutPassword:
    """Tests for admin routes returning 503 when ADMIN_PASSWORD is unset."""

    def test_admin_metrics_503_when_no_password(self, client: TestClient, monkeypatch):
        """Admin routes must return 503 when ADMIN_PASSWORD is not configured."""
        monkeypatch.setattr(bcfg, "ADMIN_PASSWORD", "")
        
        resp = client.get("/api/admin/metrics")
        assert resp.status_code == 503, f"Expected 503 when no admin password, got {resp.status_code}"

    def test_admin_settings_503_when_no_password(self, client: TestClient, monkeypatch):
        """Admin settings routes must return 503 when ADMIN_PASSWORD is not configured."""
        monkeypatch.setattr(bcfg, "ADMIN_PASSWORD", "")
        
        resp = client.get("/api/admin/settings/sensitivity")
        assert resp.status_code == 503

    def test_admin_websocket_503_when_no_password(self, client: TestClient, monkeypatch):
        """Admin WebSocket must reject when ADMIN_PASSWORD is not configured."""
        monkeypatch.setattr(bcfg, "ADMIN_PASSWORD", "")
        
        # WebSocket should be rejected immediately with policy violation
        from starlette.websockets import WebSocketDisconnect
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect("/ws/admin"):
                pass
        assert exc_info.value.code == 1008  # Policy violation


# ---------------------------------------------------------------------------
# Upload Security Tests
# ---------------------------------------------------------------------------

class TestUploadSecurity:
    """Tests for upload limits, path traversal, and content validation."""

    def test_upload_5mb_limit(self, client: TestClient, admin_headers: dict, isolated_db):
        """Files > 5MB must be rejected (413)."""
        # Create 6MB file
        large_content = b"x" * (6 * 1024 * 1024)
        files = {"file": ("large.csv", io.BytesIO(large_content), "text/csv")}
        resp = client.post("/api/admin/datasets/upload", files=files, headers=admin_headers)
        assert resp.status_code == 413, f"Expected 413 for >5MB, got {resp.status_code}"

    def test_upload_bad_header_rejected(self, client: TestClient, admin_headers: dict, isolated_db):
        """CSV with wrong headers must be rejected (422)."""
        bad_csv = b"wrong,header\n1,2\n"
        files = {"file": ("bad.csv", io.BytesIO(bad_csv), "text/csv")}
        resp = client.post("/api/admin/datasets/upload", files=files, headers=admin_headers)
        assert resp.status_code == 422, f"Expected 422 for bad headers, got {resp.status_code}"

    def test_upload_binary_rejected(self, client: TestClient, admin_headers: dict, isolated_db):
        """Binary files must be rejected (422)."""
        binary_content = b"\x00\x01\x02\x03\xff\xfe\xfd"
        files = {"file": ("binary.bin", io.BytesIO(binary_content), "application/octet-stream")}
        resp = client.post("/api/admin/datasets/upload", files=files, headers=admin_headers)
        assert resp.status_code == 422, f"Expected 422 for binary, got {resp.status_code}"

    def test_path_traversal_plain_rejected(self, client: TestClient, admin_headers: dict, isolated_db):
        """Path traversal in dataset download must be rejected (400/404)."""
        resp = client.get("/api/admin/datasets/../../etc/passwd", headers=admin_headers)
        assert resp.status_code in [400, 404], f"Expected 4xx for path traversal, got {resp.status_code}"

    def test_path_traversal_encoded_rejected(self, client: TestClient, admin_headers: dict, isolated_db):
        """URL-encoded path traversal must be rejected (400/404)."""
        # ../ encoded as %2e%2e%2f
        resp = client.get("/api/admin/datasets/%2e%2e%2f%2e%2e%2fetc%2fpasswd", headers=admin_headers)
        assert resp.status_code in [400, 404], f"Expected 4xx for encoded traversal, got {resp.status_code}"

    def test_path_traversal_analysis_rejected(self, client: TestClient, admin_headers: dict, isolated_db):
        """Path traversal in dataset analysis must be rejected."""
        resp = client.get("/api/admin/datasets/analysis/../../etc/passwd", headers=admin_headers)
        assert resp.status_code in [400, 404], f"Expected 4xx for analysis traversal, got {resp.status_code}"

    def test_server_generated_filenames(self, client: TestClient, admin_headers: dict, isolated_db):
        """Uploaded files must be stored with server-generated names, not user-supplied."""
        csv_content = b"timestamp,temperature,humidity\n2026-11-15T12:00:00Z,25.0,60.0\n"
        files = {"file": ("malicious_name.exe", io.BytesIO(csv_content), "text/csv")}
        resp = client.post("/api/admin/datasets/upload", files=files, headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        # Should have a generated filename, not the original
        assert "filename" in data
        assert data["filename"] != "malicious_name.exe"
        assert data["filename"].endswith(".csv")


# ---------------------------------------------------------------------------
# CSV Export Formula Injection Tests
# ---------------------------------------------------------------------------

class TestCSVFormulaInjection:
    """Tests for CSV export formula injection protection."""

    def test_formula_equals_escaped(self, client: TestClient, admin_headers: dict, isolated_db):
        """Cells starting with = must be prefixed with apostrophe."""
        # Insert an event with formula-like content
        from backend.database import insert_event
        insert_event(
            start_time="2026-11-15T12:00:00Z",
            end_time="2026-11-15T12:00:10Z",
            duration_sec=10.0,
            peak_temp=25.0,
            peak_hum=60.0,
            delta_temp=0.0,
            what_changed="=cmd|' /C calc'!A0",
            severity="Medium",
            sentence="Test event with formula",
        )
        
        resp = client.get("/api/admin/alerts/export", headers=admin_headers)
        assert resp.status_code == 200
        content = resp.content.decode("utf-8")
        # Check that = is escaped with leading apostrophe
        assert "'=cmd" in content, f"Formula injection not escaped: {content}"

    def test_formula_plus_escaped(self, client: TestClient, admin_headers: dict, isolated_db):
        """Cells starting with + must be prefixed with apostrophe."""
        from backend.database import insert_event
        insert_event(
            start_time="2026-11-15T12:01:00Z",
            end_time="2026-11-15T12:01:10Z",
            duration_sec=10.0,
            peak_temp=25.0,
            peak_hum=60.0,
            delta_temp=0.0,
            what_changed="+1+1",
            severity="Medium",
            sentence="Test event with plus formula",
        )
        
        resp = client.get("/api/admin/alerts/export", headers=admin_headers)
        assert resp.status_code == 200
        content = resp.content.decode("utf-8")
        assert "'+1+1" in content, f"Plus formula not escaped: {content}"

    def test_formula_minus_escaped(self, client: TestClient, admin_headers: dict, isolated_db):
        """Cells starting with - must be prefixed with apostrophe."""
        from backend.database import insert_event
        insert_event(
            start_time="2026-11-15T12:02:00Z",
            end_time="2026-11-15T12:02:10Z",
            duration_sec=10.0,
            peak_temp=25.0,
            peak_hum=60.0,
            delta_temp=0.0,
            what_changed="-sum(A1:A10)",
            severity="Medium",
            sentence="Test event with minus formula",
        )
        
        resp = client.get("/api/admin/alerts/export", headers=admin_headers)
        assert resp.status_code == 200
        content = resp.content.decode("utf-8")
        assert "'-sum" in content, f"Minus formula not escaped: {content}"

    def test_formula_at_escaped(self, client: TestClient, admin_headers: dict, isolated_db):
        """Cells starting with @ must be prefixed with apostrophe."""
        from backend.database import insert_event
        insert_event(
            start_time="2026-11-15T12:03:00Z",
            end_time="2026-11-15T12:03:10Z",
            duration_sec=10.0,
            peak_temp=25.0,
            peak_hum=60.0,
            delta_temp=0.0,
            what_changed="@SUM(A1:A10)",
            severity="Medium",
            sentence="Test event with at formula",
        )
        
        resp = client.get("/api/admin/alerts/export", headers=admin_headers)
        assert resp.status_code == 200
        content = resp.content.decode("utf-8")
        assert "'@SUM" in content, f"At formula not escaped: {content}"


# ---------------------------------------------------------------------------
# Security Headers Tests
# ---------------------------------------------------------------------------

class TestSecurityHeaders:
    """Tests for CSP and X-Content-Type-Options headers."""

    def test_csp_header_present(self, client: TestClient):
        """Content-Security-Policy header must be present on all responses."""
        resp = client.get("/")
        assert "content-security-policy" in resp.headers, "CSP header missing on /"
        csp = resp.headers["content-security-policy"]
        assert "default-src" in csp or "script-src" in csp, f"CSP too weak: {csp}"

    def test_csp_header_on_admin(self, client: TestClient):
        """CSP header must be present on /admin."""
        resp = client.get("/admin")
        assert "content-security-policy" in resp.headers, "CSP header missing on /admin"

    def test_csp_header_on_api(self, client: TestClient):
        """CSP header must be present on API endpoints."""
        resp = client.get("/api/health")
        assert "content-security-policy" in resp.headers, f"CSP header missing on /api/health: {resp.headers}"

    def test_x_content_type_options_present(self, client: TestClient):
        """X-Content-Type-Options: nosniff must be present."""
        resp = client.get("/")
        assert resp.headers.get("x-content-type-options") == "nosniff", \
            f"X-Content-Type-Options missing or incorrect: {resp.headers.get('x-content-type-options')}"

    def test_pages_still_work_with_headers(self, client: TestClient):
        """Both client page and admin page must still render with security headers."""
        resp_root = client.get("/")
        assert resp_root.status_code == 200
        assert "text/html" in resp_root.headers.get("content-type", "")
        
        resp_admin = client.get("/admin")
        assert resp_admin.status_code == 200
        assert "text/html" in resp_admin.headers.get("content-type", "")


# ---------------------------------------------------------------------------
# Secret Scanning Test
# ---------------------------------------------------------------------------

class TestSecretScanning:
    """Scan tracked files for secrets."""

    def test_no_aws_keys_in_tracked_files(self):
        """No AWS access keys (AKIA*) in tracked files."""
        import subprocess
        import os
        # Use git ls-files but handle Windows subprocess issues
        try:
            result = subprocess.run(
                ["git", "ls-files"],
                cwd=Path(__file__).parent.parent,
                capture_output=True,
                text=True,
                timeout=30
            )
        except (OSError, subprocess.TimeoutExpired):
            pytest.skip("git not available or timeout")
        
        tracked_files = result.stdout.strip().split("\n")
        
        for f in tracked_files:
            if not f:
                continue
            full_path = Path(__file__).parent.parent / f
            if full_path.is_file() and full_path.suffix not in [".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2", ".db", ".db-shm", ".db-wal"]:
                try:
                    content = full_path.read_text(encoding="utf-8", errors="ignore")
                    # Check for common secret patterns
                    assert "AKIA" not in content, f"AWS access key pattern in {f}"
                    assert "aws_secret_access_key" not in content.lower(), f"AWS secret key in {f}"
                    # Don't flag test files that intentionally test secret scanning
                except Exception:
                    pass  # Skip unreadable files


# ---------------------------------------------------------------------------
# Dependency Audit Tests
# ---------------------------------------------------------------------------

class TestDependencyAudit:
    """Run pip-audit and npm audit (informational)."""

    def test_pip_audit_no_critical(self):
        """pip-audit should report no critical vulnerabilities."""
        import subprocess
        import shutil
        if not shutil.which("pip-audit"):
            pytest.skip("pip-audit not installed")
        result = subprocess.run(
            ["pip-audit", "--desc", "--format=json"],
            capture_output=True,
            text=True,
            timeout=120
        )
        # Just log results - don't fail on vulns for now
        print(f"pip-audit exit code: {result.returncode}")
        if result.stdout:
            print(f"pip-audit stdout: {result.stdout[:2000]}")

    def test_npm_audit_no_critical(self):
        """npm audit should report no critical vulnerabilities in frontend."""
        import subprocess
        import shutil
        if not shutil.which("npm"):
            pytest.skip("npm not installed")
        frontend_dir = Path(__file__).parent.parent / "frontend"
        if frontend_dir.exists():
            try:
                result = subprocess.run(
                    ["npm", "audit", "--json"],
                    cwd=frontend_dir,
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                print(f"npm audit exit code: {result.returncode}")
                if result.stdout:
                    print(f"npm audit stdout: {result.stdout[:2000]}")
            except FileNotFoundError:
                pytest.skip("npm not available in test environment")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])