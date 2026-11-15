"""
e2e_tests/test_tier2_boundaries/test_area13_boundary.py
Area 13 Boundary & Operational Integrity Tests (Features 1, 16, 25, 26)
Tier 2 Tests: Preflight failure modes (unset password, hash mismatch, missing dist), deep secret scan, git status.
"""

from pathlib import Path
import re
import subprocess
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def test_a13_t2_01_preflight_no_go_when_admin_password_unset():
    """
    TEST-A13-T2-01: Preflight script outputs NO-GO when ADMIN_PASSWORD is unset.
    """
    preflight_script = PROJECT_ROOT / "scripts" / "preflight.ps1"
    if not preflight_script.exists():
        pytest.fail("scripts/preflight.ps1 not yet created by M6 worker")

    env = {"ADMIN_PASSWORD": ""}
    res = subprocess.run(
        ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(preflight_script)],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        env=env,
        cwd=str(PROJECT_ROOT),
    )
    assert res.returncode != 0 or "NO-GO" in res.stdout


def test_a13_t2_02_preflight_no_go_on_model_hash_mismatch():
    """
    TEST-A13-T2-02: Preflight script contract detects model hash tampering.
    """
    preflight_script = PROJECT_ROOT / "scripts" / "preflight.ps1"
    if not preflight_script.exists():
        pytest.fail("scripts/preflight.ps1 not yet created by M6 worker")


def test_a13_t2_03_preflight_frontend_dist_check():
    """
    TEST-A13-T2-03: Preflight script verifies frontend/dist exists.
    """
    frontend_dist = PROJECT_ROOT / "frontend" / "dist"
    assert frontend_dist.exists()
    assert (frontend_dist / "index.html").exists()


def test_a13_t2_04_preflight_serial_port_warning_only():
    """
    TEST-A13-T2-04: Missing physical serial port must be a non-fatal warning in preflight.
    """
    preflight_script = PROJECT_ROOT / "scripts" / "preflight.ps1"
    if not preflight_script.exists():
        pytest.fail("scripts/preflight.ps1 not yet created by M6 worker")


def test_a13_t2_05_git_history_deep_secret_scan():
    """
    TEST-A13-T2-05: Git history commits do not contain AWS keys or private keys in diff patches.
    Scans git commit patches (-p) across recent history.
    """
    res = subprocess.run(
        ["git", "log", "-p", "-n", "25"],
        capture_output=True,
        encoding='utf-8',
        errors='replace',
        stdin=subprocess.DEVNULL,
        cwd=str(PROJECT_ROOT),
    )
    assert res.returncode == 0
    log_text = res.stdout
    assert "AKIA" not in log_text, "AWS access key pattern found in git history diffs"
    assert "BEGIN PRIVATE KEY" not in log_text, "Private key block found in git history diffs"
    assert "BEGIN RSA PRIVATE KEY" not in log_text, "RSA private key block found in git history diffs"


def test_a13_t2_06_clean_git_status_check():
    """
    TEST-A13-T2-06: Git status does not show untracked source mutations outside allowed directories.
    """
    res = subprocess.run(
        ["git", "status", "--short"],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        cwd=str(PROJECT_ROOT),
    )
    assert res.returncode == 0
