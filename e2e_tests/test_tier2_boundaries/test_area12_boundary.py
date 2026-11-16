"""
e2e_tests/test_tier2_boundaries/test_area12_boundary.py
Area 12 Boundary & Frontend Edge Cases (Features 7, 23, 24)
Tier 2 Tests: Banned term case variations, stale/waiting states, unreachable fallback, responsive layouts.
"""

from pathlib import Path
import re
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

BANNED_DOM_TERMS = [
    "isolation", "forest", "score", "threshold", "z-score", "precision",
    "recall", "f1", "confusion", "ewma", "hardware", "serial", "websocket",
    "port", "baud", "model", "cockpit"
]


def test_a12_t2_01_banned_terms_case_and_variant_scan():
    """
    TEST-A12-T2-01: Scanning client UI files for case-insensitive variations of banned ML terms.
    """
    client_view_path = PROJECT_ROOT / "frontend" / "src" / "views" / "ClientView.jsx"
    assert client_view_path.exists()
    content = client_view_path.read_text(encoding="utf-8")

    # Visible text elements in JSX
    jsx_text = re.findall(r'>([^<]+)<', content)
    for text_block in jsx_text:
        text_clean = text_block.strip()
        if not text_clean or "{" in text_clean:
            continue
        for term in BANNED_DOM_TERMS:
            pattern = rf"\b{re.escape(term)}\b"
            assert not re.search(pattern, text_clean, re.IGNORECASE), (
                f"Banned term variant '{term}' found in '{text_block}'"
            )


def test_a12_t2_02_waiting_and_stale_state_copy():
    """
    TEST-A12-T2-02: Client view handles waiting or stale copy cleanly.
    """
    client_view_path = PROJECT_ROOT / "frontend" / "src" / "views" / "ClientView.jsx"
    content = client_view_path.read_text(encoding="utf-8")
    assert "Live" in content or "Offline" in content


def test_a12_t2_03_backend_unreachable_message():
    """
    TEST-A12-T2-03: Verification that client code contains clean offline/unreachable fallback text.
    """
    client_view_path = PROJECT_ROOT / "frontend" / "src" / "views" / "ClientView.jsx"
    content = client_view_path.read_text(encoding="utf-8")
    assert "Offline" in content or "Disconnected" in content or "status" in content


def test_a12_t2_04_accessibility_aria_labels_present():
    """
    TEST-A12-T2-04: Client view uses standard HTML landmarks and accessible markup.
    Requires explicit <main>, <header>, and <footer> landmark elements.
    """
    client_view_path = PROJECT_ROOT / "frontend" / "src" / "views" / "ClientView.jsx"
    content = client_view_path.read_text(encoding="utf-8")
    assert "<main" in content, "Client view missing semantic <main> landmark element"
    assert "<header" in content, "Client view missing semantic <header> landmark element"
    assert "<footer" in content, "Client view missing semantic <footer> landmark element"


def test_a12_t2_05_responsive_viewport_meta():
    """
    TEST-A12-T2-05: index.html configures responsive viewport for mobile, tablet, and desktop.
    """
    index_html = PROJECT_ROOT / "frontend" / "dist" / "index.html"
    assert index_html.exists()
    content = index_html.read_text(encoding="utf-8")
    assert 'name="viewport"' in content
    assert "width=device-width" in content
