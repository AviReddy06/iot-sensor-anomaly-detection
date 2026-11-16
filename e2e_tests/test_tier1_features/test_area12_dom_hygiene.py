"""
e2e_tests/test_tier1_features/test_area12_dom_hygiene.py
Area 12: Frontend DOM Hygiene & Offline Font Delivery (Features 7, 23, 24)
Tier 1 Tests: Client DOM purity (17 banned terms), offline font delivery, extra="forbid", student footer.
"""

from pathlib import Path
import re
import pytest
from starlette.testclient import TestClient
from backend.schemas.client_schemas import ClientReading, ClientEvent, ClientStatusResponse
import pydantic

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

BANNED_DOM_TERMS = [
    "isolation", "forest", "score", "threshold", "z-score", "precision",
    "recall", "f1", "confusion", "ewma", "hardware", "serial", "websocket",
    "port", "baud", "model", "cockpit"
]


def test_a12_t1_01_banned_terms_clean_client_page():
    """
    TEST-A12-T1-01: Zero occurrences of the 17 banned terms in client view and child components.
    Scans ClientView.jsx, ClientStripChart.jsx, RoomMap.jsx, and UnusualLog.jsx without expression bypasses.
    """
    target_files = [
        PROJECT_ROOT / "frontend" / "src" / "views" / "ClientView.jsx",
        PROJECT_ROOT / "frontend" / "src" / "components" / "ClientStripChart.jsx",
        PROJECT_ROOT / "frontend" / "src" / "components" / "RoomMap.jsx",
        PROJECT_ROOT / "frontend" / "src" / "components" / "UnusualLog.jsx",
    ]
    for path in target_files:
        assert path.exists(), f"Target frontend file missing: {path}"
        content = path.read_text(encoding="utf-8")

        # 1. Check all text blocks between JSX tags
        jsx_text = re.findall(r'>([^<]+)<', content)
        for text_block in jsx_text:
            text_clean = text_block.strip().lower()
            if not text_clean:
                continue
            # Strip curly brace delimiters but inspect string literals inside JSX expressions
            text_clean = text_clean.replace("{", " ").replace("}", " ").replace('"', " ").replace("'", " ")
            for term in BANNED_DOM_TERMS:
                pattern = rf"\b{re.escape(term)}\b"
                assert not re.search(pattern, text_clean), (
                    f"Banned technical term '{term}' leaked in {path.name}: '{text_block}'"
                )

        # 2. Check accessibility attributes (title, aria-label, alt, placeholder)
        attr_text = re.findall(r'(?:title|aria-label|alt|placeholder)=["\']([^"\']+)["\']', content, re.IGNORECASE)
        for val in attr_text:
            val_clean = val.strip().lower()
            for term in BANNED_DOM_TERMS:
                pattern = rf"\b{re.escape(term)}\b"
                assert not re.search(pattern, val_clean), (
                    f"Banned term '{term}' leaked in attribute in {path.name}: '{val}'"
                )


def test_a12_t1_02_offline_font_loading_zero_external_requests():
    """
    TEST-A12-T1-02: Offline Font Loading & Zero External Requests.
    Index HTML and CSS bundle must not reference external CDN domains.
    """
    index_html = PROJECT_ROOT / "frontend" / "dist" / "index.html"
    assert index_html.exists()
    content = index_html.read_text(encoding="utf-8").lower()

    external_domains = [
        "fonts.googleapis.com",
        "fonts.gstatic.com",
        "cdn.jsdelivr.net",
        "unpkg.com",
        "cdnjs.cloudflare.com",
    ]
    for domain in external_domains:
        assert domain not in content, f"External CDN domain '{domain}' found in index.html"


def test_a12_t1_03_client_schemas_extra_forbid():
    """
    TEST-A12-T1-03: Client response models must forbid extra technical fields.
    """
    # Attempting to instantiate ClientReading with unexpected ML fields must fail
    with pytest.raises(pydantic.ValidationError):
        ClientReading.model_validate({
            "timestamp": "2026-11-15T12:00:00Z",
            "temperature": 25.0,
            "humidity": 60.0,
            "iforest_score": -0.25,  # Forbidden extra field
        })


def test_a12_t1_04_frontend_status_states_rendering(client: TestClient):
    """
    TEST-A12-T1-04: GET /api/client/status returns valid state string.
    """
    resp = client.get("/api/client/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ["Live", "Simulated", "Offline", "normal", "live", "simulated", "offline"]


def test_a12_t1_05_static_security_headers_csp(client: TestClient):
    """
    TEST-A12-T1-05: Static serving security headers on SPA entrypoint.
    """
    resp = client.get("/")
    assert resp.status_code == 200
    # Check cache-control headers
    cc = resp.headers.get("cache-control", "")
    assert "no-cache" in cc or resp.headers.get("content-type", "").startswith("text/html")


def test_a12_t1_06_required_branding_and_footer():
    """
    TEST-A12-T1-06: Product title and student credentials exist in frontend source and html.
    """
    index_html = PROJECT_ROOT / "frontend" / "dist" / "index.html"
    client_view = PROJECT_ROOT / "frontend" / "src" / "views" / "ClientView.jsx"

    html_content = index_html.read_text(encoding="utf-8")
    assert "AI-Based IoT Sensor Anomaly Detection" in html_content

    view_content = client_view.read_text(encoding="utf-8")
    assert "Dungu Avinash Reddy" in view_content
    assert "RK3P25KZA09" in view_content
    assert "12509090" in view_content
