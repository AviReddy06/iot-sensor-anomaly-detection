"""
e2e_tests/test_tier1_features/test_area13_preflight_secrets.py
Area 13: Preflight, Operational Readiness & Secrets (Features 1, 16, 25, 26)
Tier 1 Tests: Git branch status, clean tracked files secret scan, model freeze checks, CI workflow integrity.
"""

from pathlib import Path
import re
import subprocess
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def test_a13_t1_01_preflight_script_contract():
    """
    TEST-A13-T1-01: Preflight script verification.
    scripts/preflight.ps1 must exist and validate environment readiness.
    """
    preflight_script = PROJECT_ROOT / "scripts" / "preflight.ps1"
    if not preflight_script.exists():
        pytest.fail("scripts/preflight.ps1 not yet created by M6 worker")

    result = subprocess.run(
        ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(preflight_script)],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    assert "GO" in result.stdout or "NO-GO" in result.stdout


def test_a13_t1_02_git_branch_is_hardening():
    """
    TEST-A13-T1-02: Verification that working branch is 'hardening'.
    """
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        cwd=str(PROJECT_ROOT),
    )
    current_branch = result.stdout.strip()
    assert current_branch == "hardening", f"Expected branch 'hardening', got '{current_branch}'"


def test_a13_t1_03_tracked_files_secret_scan_clean():
    """
    TEST-A13-T1-03: Static Secret Scan across tracked repository files.
    Ensures no hardcoded passwords, private keys, or API tokens are checked in.
    """
    # Run git ls-files to find all tracked files
    result = subprocess.run(
        ["git", "ls-files"],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        cwd=str(PROJECT_ROOT),
    )
    tracked_files = [f.strip() for f in result.stdout.splitlines() if f.strip()]

    secret_patterns = [
        re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS Access Key
        re.compile(r"-----BEGIN\s+PRIVATE\s+KEY-----"),  # Private Key
        re.compile(r"(?i)admin_password\s*=\s*['\"][a-zA-Z0-9_\-!@#$%^&*]{8,}['\"]"),  # Hardcoded password
    ]

    leaks = []
    for rel_path in tracked_files:
        full_path = PROJECT_ROOT / rel_path
        # Skip binary, doc, or test definition files
        if full_path.suffix.lower() in [".joblib", ".db", ".png", ".jpg", ".pyc", ".ico", ".md"]:
            continue
        try:
            content = full_path.read_text(encoding="utf-8", errors="ignore")
            for pattern in secret_patterns:
                if pattern.search(content):
                    leaks.append(f"{rel_path}: matches {pattern.pattern}")
        except Exception:
            pass

    assert len(leaks) == 0, f"Potential credential leaks detected in tracked files: {leaks}"


def test_a13_t1_04_model_freeze_manifest_contract():
    """
    TEST-A11-T1-04: Freeze hashes manifest contract.
    """
    freeze_json = PROJECT_ROOT / "results" / "freeze.json"
    if not freeze_json.exists():
        pytest.fail("results/freeze.json not yet created by M5 worker")
    assert freeze_json.stat().st_size > 0


def test_a13_t1_05_ci_workflow_integrity_no_push():
    """
    TEST-A13-T1-05: .github/workflows/ci.yml must define CI and strictly omit 'git push'.
    """
    ci_path = PROJECT_ROOT / ".github" / "workflows" / "ci.yml"
    if not ci_path.exists():
        pytest.fail(".github/workflows/ci.yml not yet created by M6 worker")

    content = ci_path.read_text(encoding="utf-8")
    assert "git push" not in content, "CI workflow must not execute 'git push'"
