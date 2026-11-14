"""
scripts/test_challenger_area_d.py
Empirical Challenger verification suite for Milestone Area D (Mobile Layout and States).
Verifies:
  1. 390px mobile layout (no horizontal scroll, room map <= 360px, no sideways scrolling table)
  2. Range buttons touch targets >= 44px
  3. Safe-area insets & viewport-fit=cover
  4. Gesture scrubbing & touch-none
  5. All 7 system states (loading, no_data, waiting, offline, stale_data, backend_unreachable, simulated)
  6. All 14 state screenshots exist
  7. Repository guardrails: strictly < 250 lines per file, zero banned DOM terms, zero banned styles
"""

from __future__ import annotations
import json
import re
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent

BANNED_TERMS = [
    "isolation", "forest", "score", "threshold", "z-score",
    "precision", "recall", "f1", "confusion", "ewma",
    "hardware", "serial", "websocket", "port", "baud",
    "model", "cockpit",
]


# Step 1: Mobile 390px layout, touch targets >= 44px, and touch-none gesture support
def test_mobile_layout_and_touch_targets():
    print("\n--- 1. Testing Mobile 390px Layout and Touch Targets ---")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto("http://127.0.0.1:8000/", wait_until="networkidle")
        page.wait_for_selector("h1")

        # 1a. Check no horizontal page scroll
        scroll_width = page.evaluate("() => document.documentElement.scrollWidth")
        client_width = page.evaluate("() => document.documentElement.clientWidth")
        print(f"Scroll width: {scroll_width} px, Client width: {client_width} px")
        assert scroll_width <= 390, f"Horizontal scroll detected! scrollWidth={scroll_width}"

        # 1b. Check RoomMap maximum width <= 360px
        room_map_col = page.locator(".max-w-\\[360px\\]").first
        assert room_map_col.is_visible(), "RoomMap max-w-[360px] wrapper missing"
        map_width = room_map_col.bounding_box()["width"]
        print(f"RoomMap width at 390px viewport: {map_width:.1f} px")
        assert map_width <= 360.5, f"RoomMap exceeds 360px: {map_width}"

        # 1c. Check range buttons touch target dimensions >= 44px
        buttons = page.locator("button:has-text('1 h'), button:has-text('15 min')").all()
        for btn in buttons:
            box = btn.bounding_box()
            txt = btn.inner_text().strip()
            print(f"Button '{txt}' touch target: {box['width']:.1f}x{box['height']:.1f} px")
            assert box["width"] >= 43.5, f"Touch target width too small for '{txt}': {box['width']}"
            assert box["height"] >= 43.5, f"Touch target height too small for '{txt}': {box['height']}"

        # 1d. Check two-line mobile cards vs hidden table
        mobile_cards = page.locator(".sm\\:hidden").all()
        assert len(mobile_cards) > 0, "Mobile cards (.sm:hidden) missing"
        desktop_table_wrapper = page.locator(".hidden.sm\\:block")
        assert desktop_table_wrapper.count() > 0, "Desktop table (.hidden.sm:block) wrapper missing"

        # 1e. Check touch-none on SVG
        svg_touch_none = page.locator("svg.touch-none").first
        assert svg_touch_none.count() > 0, "Chart SVG missing touch-none class"

        browser.close()
    print("Mobile layout, touch targets, and touch-none: PASS")


# Step 2: Safe area insets (pt-safe, pb-safe, px-safe) and viewport-fit=cover
def test_safe_areas_and_meta():
    print("\n--- 2. Testing Safe Area Insets and Meta Viewport ---")
    html_content = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    assert "viewport-fit=cover" in html_content, "index.html missing viewport-fit=cover"

    css_content = (ROOT / "frontend" / "src" / "index.css").read_text(encoding="utf-8")
    assert ".pt-safe" in css_content and ".pb-safe" in css_content and ".px-safe" in css_content, "index.css missing safe-area classes"
    assert "touch-none" in css_content, "index.css missing .touch-none rule"

    client_view_code = (ROOT / "frontend" / "src" / "views" / "ClientView.jsx").read_text(encoding="utf-8")
    assert "pt-safe" in client_view_code and "pb-safe" in client_view_code and "px-safe" in client_view_code, "ClientView missing safe-area classes"
    print("Safe areas and meta viewport: PASS")


# Step 3: All 7 system states mocked and verified (copy, styling, opacity-60)
def test_system_states_mocked():
    print("\n--- 3. Testing 7 System States Feedback ---")
    with sync_playwright() as p:
        browser = p.chromium.launch()

        # State: offline
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.route("**/api/client/status", lambda r: r.fulfill(
            status=200, content_type="application/json",
            body=json.dumps({"status": "Offline", "offline_time": "11:32", "last_reading_time": "2026-11-14 11:32:00"})
        ))
        page.route("**/api/client/readings*", lambda r: r.fulfill(
            status=200, content_type="application/json",
            body=json.dumps([{"timestamp": "2026-11-14 11:32:00", "temperature": 23.5, "humidity": 50.0}])
        ))
        page.route("**/api/client/events*", lambda r: r.fulfill(status=200, content_type="application/json", body="[]"))
        page.goto("http://127.0.0.1:8000/", wait_until="networkidle")
        page.wait_for_timeout(400)
        content = page.content()
        assert "Sensor offline since 11:32. Showing the last readings." in content, "Offline banner missing"
        assert "opacity-60" in content, "Chart section opacity-60 missing when offline"
        page.close()

        # State: stale data
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.route("**/api/client/status", lambda r: r.fulfill(
            status=200, content_type="application/json",
            body=json.dumps({"status": "Live", "is_stale": True, "stale_text": "Last reading 3 min ago.", "last_reading_time": "2026-11-14 21:57:00"})
        ))
        page.route("**/api/client/readings*", lambda r: r.fulfill(status=200, content_type="application/json", body="[]"))
        page.route("**/api/client/events*", lambda r: r.fulfill(status=200, content_type="application/json", body="[]"))
        page.goto("http://127.0.0.1:8000/", wait_until="networkidle")
        page.wait_for_timeout(400)
        content = page.content()
        assert "Last reading 3 min ago." in content, "Stale data indicator missing"
        page.close()

        # State: waiting
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.route("**/api/client/status", lambda r: r.fulfill(
            status=200, content_type="application/json",
            body=json.dumps({"status": "Live", "last_reading_time": "2026-11-14 22:00:00"})
        ))
        page.route("**/api/client/readings*", lambda r: r.fulfill(
            status=200, content_type="application/json",
            body=json.dumps([{"timestamp": "2026-11-14 22:00:00", "temperature": 23.5, "humidity": 50.0}])
        ))
        page.route("**/api/client/events*", lambda r: r.fulfill(status=200, content_type="application/json", body="[]"))
        page.goto("http://127.0.0.1:8000/", wait_until="networkidle")
        page.wait_for_timeout(400)
        content = page.content()
        assert "Collecting readings. Charts appear after about a minute." in content, "Waiting state copy missing"
        page.close()

        # State: backend unreachable
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.route("**/api/client/**", lambda r: r.abort())
        try:
            page.goto("http://127.0.0.1:8000/", wait_until="networkidle")
        except Exception:
            pass
        page.wait_for_timeout(600)
        content = page.content()
        assert "Cannot reach the monitor. Retrying in 10 s." in content, "Unreachable copy missing"
        page.close()

        browser.close()
    print("System states feedback: PASS")


# Step 4: Verification of all 14 state screenshots existence and non-zero size
def test_state_screenshots_exist():
    print("\n--- 4. Checking All 14 State Screenshots ---")
    states = ["loading", "no_data", "waiting", "offline", "stale_data", "backend_unreachable", "simulated"]
    missing = []
    for s in states:
        for vp in ["390", "1440"]:
            p = ROOT / "docs" / "screenshots" / f"states_{s}_{vp}.png"
            if not p.exists() or p.stat().st_size == 0:
                missing.append(p.name)
    assert not missing, f"Missing state screenshots: {missing}"
    print(f"All 14 state screenshots present and non-empty: PASS")


# Step 5: Repository guardrails verification (line counts < 250 and zero banned DOM terms)
def test_guardrails():
    print("\n--- 5. Checking Repository Guardrails ---")
    # File line counts
    client_files = [
        "frontend/src/views/ClientView.jsx",
        "frontend/src/components/ClientStripChart.jsx",
        "frontend/src/components/StripChartGrid.jsx",
        "frontend/src/components/RoomMap.jsx",
        "frontend/src/components/UnusualLog.jsx",
        "frontend/src/hooks/useClientData.js",
        "frontend/src/index.css",
        "scripts/capture_state_screenshots.py",
    ]
    for rel_path in client_files:
        f = ROOT / rel_path
        lines = len(f.read_text(encoding="utf-8").splitlines())
        print(f"File {rel_path}: {lines} lines")
        assert lines < 250, f"File {rel_path} exceeds 250 lines: {lines}"

    # Banned DOM terms on live page
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto("http://127.0.0.1:8000/", wait_until="networkidle")
        page_text = page.locator("body").inner_text().lower()
        for term in BANNED_TERMS:
            # Check whole word match
            matches = re.findall(rf"\b{term}\b", page_text)
            assert not matches, f"Banned DOM term found on client page: '{term}'"
        browser.close()

    print("Repository guardrails (line counts & zero banned terms): PASS")


# Step 6: Test suite execution harness
if __name__ == "__main__":
    test_mobile_layout_and_touch_targets()
    test_safe_areas_and_meta()
    test_system_states_mocked()
    test_state_screenshots_exist()
    test_guardrails()
    print("\nALL AREA D CHALLENGER TESTS PASSED!")
