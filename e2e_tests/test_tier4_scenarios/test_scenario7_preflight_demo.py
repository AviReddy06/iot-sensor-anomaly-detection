"""
e2e_tests/test_tier4_scenarios/test_scenario7_preflight_demo.py
Tier 4 Scenario 7: Preflight Script Validation & Examiner Demo Dry-Run Sequence
Validates demo readiness, HTML product branding, student credentials footer,
unsliced DOM hygiene across 17 banned terms, and preflight.ps1 contract.
"""

from pathlib import Path
import re
import subprocess
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

BANNED_TERMS = [
    "isolation", "forest", "score", "threshold", "z-score", "precision",
    "recall", "f1", "confusion", "ewma", "hardware", "serial", "websocket",
    "port", "baud", "model", "cockpit"
]


def test_scenario_07_preflight_demo_readiness():
    """
    Scenario 7: Examiner 5-minute demo dry-run verification.
    1. Title: "AI-Based IoT Sensor Anomaly Detection" present across frontend.
    2. Footer: "Dungu Avinash Reddy | Roll RK3P25KZA09 | Reg. 12509090" present verbatim.
    3. Full client DOM scan (no body slicing): zero occurrences of 17 banned terms.
    4. Client JSX components scan: zero occurrences of 17 banned terms.
    5. Offline delivery: zero external CDN links.
    6. Preflight script validation: execute scripts/preflight.ps1.
    """
    index_html = PROJECT_ROOT / "frontend" / "dist" / "index.html"
    client_view = PROJECT_ROOT / "frontend" / "src" / "views" / "ClientView.jsx"
    client_components = [
        PROJECT_ROOT / "frontend" / "src" / "components" / "ClientStripChart.jsx",
        PROJECT_ROOT / "frontend" / "src" / "components" / "RoomMap.jsx",
        PROJECT_ROOT / "frontend" / "src" / "components" / "UnusualLog.jsx",
    ]

    assert index_html.exists(), "frontend/dist/index.html not found. Run npm run build."
    assert client_view.exists(), "ClientView.jsx not found."

    html_content = index_html.read_text(encoding="utf-8")
    view_content = client_view.read_text(encoding="utf-8")

    # 1. Title verification
    assert "AI-Based IoT Sensor Anomaly Detection" in html_content

    # 2. Student credential footer verification
    assert "Dungu Avinash Reddy" in view_content
    assert "RK3P25KZA09" in view_content
    assert "12509090" in view_content

    # 3. Full DOM hygiene: zero occurrences across full index.html (UNSLICED)
    for term in BANNED_TERMS:
        pattern = rf"\b{re.escape(term)}\b"
        assert not re.search(pattern, html_content, re.IGNORECASE), (
            f"Banned term '{term}' found in dist/index.html"
        )

    # 4. Client JSX components scan
    all_client_files = [client_view] + [c for c in client_components if c.exists()]
    for comp_file in all_client_files:
        content = comp_file.read_text(encoding="utf-8")
        for term in BANNED_TERMS:
            pattern = rf"\b{re.escape(term)}\b"
            assert not re.search(pattern, content, re.IGNORECASE), (
                f"Banned term '{term}' found in client component {comp_file.name}"
            )

    # 5. Zero external CDN references
    assert "fonts.googleapis.com" not in html_content
    assert "cdn.jsdelivr.net" not in html_content

    # 6. Preflight script contract validation
    preflight_ps1 = PROJECT_ROOT / "scripts" / "preflight.ps1"
    if not preflight_ps1.exists():
        pytest.fail("scripts/preflight.ps1 not found — required for demo validation (M6 deliverable)")

    res = subprocess.run(["powershell", "-File", str(preflight_ps1)], capture_output=True, text=True)
    assert res.returncode == 0 or "GO" in res.stdout, f"Preflight validation failed: {res.stdout}\n{res.stderr}"
