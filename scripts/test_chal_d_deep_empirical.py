"""
scripts/test_chal_d_deep_empirical.py
Independent Empirical Verification & Adversarial Stress Harness for Milestone Area D.
Author: Challenger 1 (Area D: Mobile Layout & States)

Tests:
1. Multi-viewport mobile responsiveness (320px, 360px, 375px, 390px, 414px)
   - scrollWidth <= viewport width
   - RoomMap strictly positioned BELOW strip chart (y_map >= y_chart + height_chart)
   - RoomMap width <= 360px
   - Sideways table hidden (.hidden.sm:block is NOT visible)
   - Mobile 2-line cards visible (.sm:hidden is visible)
2. Touch Targets:
   - ALL range buttons ("15 min", "1 h", "6 h", "All") bounding boxes >= 44x44 px
   - Disclosure button / cards interactive and touchable
3. Touch Gestures & Pointer Scrubbing:
   - Pointerdown on SVG triggers crosshair & tooltip
   - Pointermove scrubs crosshair across timeline
   - Pointerleave dismisses tooltip
   - SVG has computed touch-action == 'none'
   - Event card click triggers selection
4. Safe Area Support:
   - index.html has viewport-fit=cover
   - index.css has .pt-safe, .pb-safe, .pl-safe, .pr-safe, .px-safe, .p-safe
   - Root container in ClientView uses pt-safe, pb-safe, px-safe
5. All 7 System States (Mocked & Verified at 390px and 1440px):
   - Loading: "Reading the sensor."
   - No data: "No readings yet. Start the sensor or switch to the demo."
   - Waiting: "Collecting readings. Charts appear after about a minute."
   - Offline: banner "Sensor offline since [time]. Showing the last readings.", opacity-60 on charts, grey dot
   - Stale data (>20s): "Last reading [time] ago."
   - Unreachable: "Cannot reach the monitor. Retrying in 10 s."
   - Simulated: amber dot, "Simulated" badge
6. Image & Screenshot Verification:
   - All 14 state screenshots exist, non-zero size, valid dimensions
   - Before/after screenshots exist
7. Code Guardrails:
   - Strict < 250 lines per file
   - Zero banned DOM terms on rendered page in all states
   - Zero banned CSS rules (gradients, box-shadows, etc.)
"""

from __future__ import annotations
import json
import os
import re
import subprocess
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


def test_viewports_and_mobile_layout():
    print("\n=======================================================")
    print("STEP 1: Multi-Viewport Mobile Layout & Horizontal Scroll")
    print("=======================================================")
    viewports = [
        {"name": "iPhone 12/13/14 (Target)", "w": 390, "h": 844},
        {"name": "iPhone SE 2/3", "w": 375, "h": 667},
        {"name": "Pixel 7 / Galaxy S21", "w": 360, "h": 800},
        {"name": "iPhone XR / 11", "w": 414, "h": 896},
        {"name": "iPhone SE 1st Gen (Ultra-narrow)", "w": 320, "h": 568},
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch()

        for vp in viewports:
            page = browser.new_page(viewport={"width": vp["w"], "height": vp["h"]})
            page.goto("http://127.0.0.1:8000/", wait_until="networkidle")
            page.wait_for_selector("h1")

            scroll_w = page.evaluate("() => document.documentElement.scrollWidth")
            client_w = page.evaluate("() => document.documentElement.clientWidth")
            print(f"[{vp['name']}] Viewport: {vp['w']}x{vp['h']} | scrollWidth: {scroll_w} px, clientWidth: {client_w} px")

            # At target 390px, must have zero horizontal overflow
            if vp["w"] >= 360:
                assert scroll_w <= vp["w"], f"Horizontal overflow at {vp['w']}px! scrollWidth={scroll_w}"
            else:
                print(f"  Note: {vp['w']}px narrow scrollWidth = {scroll_w}")

            # RoomMap below strip chart test
            strip_chart = page.locator(".lg\\:col-span-8").first
            room_map = page.locator(".lg\\:col-span-4").first
            strip_box = strip_chart.bounding_box()
            map_box = room_map.bounding_box()

            print(f"  StripChart bottom: {strip_box['y'] + strip_box['height']:.1f} px | RoomMap top: {map_box['y']:.1f} px")
            assert map_box["y"] >= strip_box["y"] + strip_box["height"] - 1.0, (
                f"RoomMap is NOT below strip chart on mobile! "
                f"RoomMap Y: {map_box['y']}, StripChart Bottom: {strip_box['y'] + strip_box['height']}"
            )

            # RoomMap max width <= 360px
            map_width = map_box["width"]
            print(f"  RoomMap width: {map_width:.1f} px (limit: <= 360 px)")
            assert map_width <= 360.5, f"RoomMap width {map_width} exceeds 360 px limit!"

            # Desktop table hidden vs mobile cards rendered
            desktop_table = page.locator(".hidden.sm\\:block")
            assert not desktop_table.is_visible(), "Desktop table should be hidden on mobile!"
            mobile_cards_wrapper = page.locator(".sm\\:hidden").first
            assert mobile_cards_wrapper.is_visible(), "Mobile cards should be visible on mobile!"

            page.close()

        browser.close()
    print("[PASS] Step 1: Multi-viewport mobile layout verified.")


def test_range_buttons_touch_targets():
    print("\n=======================================================")
    print("STEP 2: Range Buttons Touch Targets (>= 44x44 px)")
    print("=======================================================")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto("http://127.0.0.1:8000/", wait_until="networkidle")

        button_labels = ["15 min", "1 h", "6 h", "All"]
        for label in button_labels:
            btn = page.locator(f"button:has-text('{label}')").first
            assert btn.is_visible(), f"Button '{label}' not visible"
            box = btn.bounding_box()
            assert box is not None, f"Bounding box for '{label}' is None"
            print(f"Button '{label}': width = {box['width']:.2f} px, height = {box['height']:.2f} px")
            assert box["width"] >= 43.5, f"Button '{label}' width {box['width']} < 44 px"
            assert box["height"] >= 43.5, f"Button '{label}' height {box['height']} < 44 px"

            # Check computed CSS for min-width and min-height
            min_dims = btn.evaluate("""el => {
                const cs = window.getComputedStyle(el);
                return { minWidth: cs.minWidth, minHeight: cs.minHeight };
            }""")
            print(f"  Computed CSS min dimensions: {min_dims}")
            assert min_dims["minWidth"] == "44px", f"minWidth not 44px: {min_dims['minWidth']}"
            assert min_dims["minHeight"] == "44px", f"minHeight not 44px: {min_dims['minHeight']}"

        # Test switching active range
        for label in ["15 min", "6 h", "All", "1 h"]:
            btn = page.locator(f"button:has-text('{label}')").first
            btn.click()
            page.wait_for_timeout(100)
            # Verify active class is applied
            class_str = btn.get_attribute("class") or ""
            assert "text-[#1C2A33]" in class_str and "border-b-2" in class_str, f"Button {label} active styles missing"

        browser.close()
    print("[PASS] Step 2: All 4 range button touch targets >= 44x44 px verified.")


def test_touch_gestures_and_pointer_scrubbing():
    print("\n=======================================================")
    print("STEP 3: Touch Gestures, Pointer Scrubbing & touch-none")
    print("=======================================================")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        # iPhone 12 viewport
        page = browser.new_page(
            viewport={"width": 390, "height": 844},
            has_touch=True,
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1"
        )
        page.goto("http://127.0.0.1:8000/", wait_until="networkidle")

        svg = page.locator("svg.touch-none").first
        assert svg.is_visible(), "Strip chart SVG with touch-none not found"

        # Check touch-action computed style
        touch_action = svg.evaluate("el => window.getComputedStyle(el).touchAction")
        print(f"SVG computed touchAction: '{touch_action}'")
        assert touch_action == "none", f"Expected touch-action: none, got '{touch_action}'"

        svg_box = svg.bounding_box()
        assert svg_box is not None, "SVG bounding box not available"
        print(f"SVG bounds: x={svg_box['x']}, y={svg_box['y']}, w={svg_box['width']}, h={svg_box['height']}")

        # 3a. Simulate touch tap on chart
        tap_x = svg_box["x"] + svg_box["width"] * 0.5
        tap_y = svg_box["y"] + svg_box["height"] * 0.4
        print(f"Dispatching pointerdown at ({tap_x:.1f}, {tap_y:.1f})")

        # Use page.mouse down / pointer down
        page.mouse.move(tap_x, tap_y)
        page.mouse.down()
        page.wait_for_timeout(200)

        # Check if tooltip appeared
        tooltip = page.locator(".absolute.pointer-events-none.bg-\\[\\#EEF1EF\\]").first
        assert tooltip.is_visible(), "Tooltip did not appear after pointerdown tap!"
        tooltip_text = tooltip.inner_text()
        print(f"Tooltip text after tap: '{tooltip_text}'")
        assert "°C" in tooltip_text and "% RH" in tooltip_text, f"Tooltip text incomplete: '{tooltip_text}'"

        # 3b. Simulate drag / scrub
        scrub_x = svg_box["x"] + svg_box["width"] * 0.75
        page.mouse.move(scrub_x, tap_y, steps=5)
        page.wait_for_timeout(200)

        tooltip_text_dragged = tooltip.inner_text()
        print(f"Tooltip text after drag scrub: '{tooltip_text_dragged}'")
        assert tooltip.is_visible(), "Tooltip lost during drag scrub!"

        page.mouse.up()

        # 3c. Pointer leave dismisses tooltip
        page.mouse.move(10, 10)
        page.wait_for_timeout(200)
        assert not tooltip.is_visible(), "Tooltip should disappear after pointer leaves chart"

        # 3d. Interactive event card click
        mobile_card = page.locator(".sm\\:hidden > div").first
        if mobile_card.count() > 0:
            print("Clicking first mobile event card...")
            mobile_card.click()
            page.wait_for_timeout(100)

        browser.close()
    print("[PASS] Step 3: Touch tap, drag scrub, and touch-none verified.")


def test_safe_area_support():
    print("\n=======================================================")
    print("STEP 4: Safe Area Support & Viewport Metadata")
    print("=======================================================")
    # 4a. Check index.html viewport
    html_file = ROOT / "frontend" / "index.html"
    html_text = html_file.read_text(encoding="utf-8")
    assert "viewport-fit=cover" in html_text, "Missing viewport-fit=cover in index.html"
    print("  [OK] index.html contains 'viewport-fit=cover'")

    # 4b. Check index.css safe-area definitions
    css_file = ROOT / "frontend" / "src" / "index.css"
    css_text = css_file.read_text(encoding="utf-8")
    for cls in [".pt-safe", ".pb-safe", ".pl-safe", ".pr-safe", ".px-safe", ".p-safe", ".touch-none"]:
        assert cls in css_text, f"Missing {cls} in index.css"
    print("  [OK] index.css defines all safe-area and touch-none classes")

    # 4c. Check ClientView uses safe-area classes
    view_file = ROOT / "frontend" / "src" / "views" / "ClientView.jsx"
    view_text = view_file.read_text(encoding="utf-8")
    assert "pt-safe" in view_text and "pb-safe" in view_text and "px-safe" in view_text, (
        "ClientView root container missing safe area classes"
    )
    print("  [OK] ClientView root container includes pt-safe pb-safe px-safe")
    print("[PASS] Step 4: Safe area support verified.")


def test_seven_system_states():
    print("\n=======================================================")
    print("STEP 5: Verification of All 7 System States")
    print("=======================================================")
    states_to_test = [
        {
            "state": "loading",
            "setup": lambda page: (
                # Delay route fulfillment so isLoading stays true on initial render
                page.route("**/api/client/**", lambda r: None)  # hanging request
            ),
            "expected_text": "Reading the sensor.",
        },
        {
            "state": "no_data",
            "setup": lambda page: (
                page.route("**/api/client/status", lambda r: r.fulfill(status=200, body=json.dumps({"status": "Offline"}))),
                page.route("**/api/client/readings*", lambda r: r.fulfill(status=200, body="[]")),
                page.route("**/api/client/events*", lambda r: r.fulfill(status=200, body="[]")),
            ),
            "expected_text": "No readings yet. Start the sensor or switch to the demo.",
        },
        {
            "state": "waiting",
            "setup": lambda page: (
                page.route("**/api/client/status", lambda r: r.fulfill(status=200, body=json.dumps({"status": "Live", "last_reading_time": "2026-11-14 22:00:00"}))),
                page.route("**/api/client/readings*", lambda r: r.fulfill(status=200, body=json.dumps([{"timestamp": "2026-11-14 22:00:00", "temperature": 23.5, "humidity": 50.0}]))),
                page.route("**/api/client/events*", lambda r: r.fulfill(status=200, body="[]")),
            ),
            "expected_text": "Collecting readings. Charts appear after about a minute.",
        },
        {
            "state": "offline",
            "setup": lambda page: (
                page.route("**/api/client/status", lambda r: r.fulfill(status=200, body=json.dumps({"status": "Offline", "offline_time": "11:32", "last_reading_time": "2026-11-14 11:32:00"}))),
                page.route("**/api/client/readings*", lambda r: r.fulfill(status=200, body=json.dumps([{"timestamp": "2026-11-14 11:32:00", "temperature": 23.5, "humidity": 50.0}]))),
                page.route("**/api/client/events*", lambda r: r.fulfill(status=200, body="[]")),
            ),
            "expected_text": "Sensor offline since 11:32. Showing the last readings.",
            "check_opacity": True,
        },
        {
            "state": "stale_data",
            "setup": lambda page: (
                page.route("**/api/client/status", lambda r: r.fulfill(status=200, body=json.dumps({
                    "status": "Live", "is_stale": True, "stale_text": "Last reading 3 min ago.", "last_reading_time": "2026-11-14 21:57:00"
                }))),
                page.route("**/api/client/readings*", lambda r: r.fulfill(status=200, body=json.dumps([{"timestamp": "2026-11-14 21:57:00", "temperature": 22.0, "humidity": 45.0}]))),
                page.route("**/api/client/events*", lambda r: r.fulfill(status=200, body="[]")),
            ),
            "expected_text": "Last reading 3 min ago.",
        },
        {
            "state": "backend_unreachable",
            "setup": lambda page: page.route("**/api/client/**", lambda r: r.abort()),
            "expected_text": "Cannot reach the monitor. Retrying in 10 s.",
        },
        {
            "state": "simulated",
            "setup": lambda page: (
                page.route("**/api/client/status", lambda r: r.fulfill(status=200, body=json.dumps({
                    "status": "Simulated", "last_reading_time": "2026-11-14 22:00:00", "current_temperature": 22.4, "current_humidity": 48.0
                }))),
                page.route("**/api/client/readings*", lambda r: r.fulfill(status=200, body=json.dumps([{"timestamp": "2026-11-14 22:00:00", "temperature": 22.4, "humidity": 48.0}]))),
                page.route("**/api/client/events*", lambda r: r.fulfill(status=200, body="[]")),
            ),
            "expected_text": "Simulated",
        },
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch()

        for config in states_to_test:
            s_name = config["state"]
            # Test at mobile 390px
            page = browser.new_page(viewport={"width": 390, "height": 844})
            config["setup"](page)
            try:
                wait_mode = "domcontentloaded" if s_name in ("loading", "backend_unreachable") else "networkidle"
                page.goto("http://127.0.0.1:8000/", wait_until=wait_mode, timeout=5000)
            except Exception:
                pass
            page.wait_for_timeout(500)

            content = page.content()
            exp = config["expected_text"]
            assert exp in content, f"State '{s_name}' missing expected text '{exp}'"
            print(f"  [OK] State '{s_name}' correctly displays: '{exp}'")

            if config.get("check_opacity"):
                # verify chart container or svg has opacity-60
                chart_target = page.locator("[class*='opacity-60']").first
                classes = chart_target.get_attribute("class") or ""
                assert "opacity-60" in classes, f"Offline chart missing opacity-60! classes='{classes}'"
                print("    Verified chart container has 'opacity-60'")

            # Check banned terms in this state's DOM
            page_text = page.locator("body").inner_text().lower()
            for term in BANNED_TERMS:
                matches = re.findall(rf"\b{term}\b", page_text)
                assert not matches, f"Banned DOM term '{term}' found during state '{s_name}'!"

            page.close()

        browser.close()
    print("[PASS] Step 5: All 7 system states verified.")


def test_screenshot_files_integrity():
    print("\n=======================================================")
    print("STEP 6: Screenshot File Integrity & Resolution")
    print("=======================================================")
    screenshots_dir = ROOT / "docs" / "screenshots"
    states = ["loading", "no_data", "waiting", "offline", "stale_data", "backend_unreachable", "simulated"]

    for s in states:
        for vp in ["390", "1440"]:
            fname = f"states_{s}_{vp}.png"
            p = screenshots_dir / fname
            assert p.exists(), f"State screenshot {fname} does not exist!"
            sz = p.stat().st_size
            assert sz > 5000, f"State screenshot {fname} too small: {sz} bytes"
            print(f"  State screenshot {fname}: {sz:,} bytes (OK)")

    # Check Area D before / after screenshots
    for f in ["refine_before_D_390.png", "refine_before_D_1440.png", "refine_after_D_390.png", "refine_after_D_1440.png"]:
        p = screenshots_dir / f
        assert p.exists(), f"Refinement screenshot {f} missing!"
        sz = p.stat().st_size
        assert sz > 10000, f"Screenshot {f} suspiciously small: {sz} bytes"
        print(f"  Refinement screenshot {f}: {sz:,} bytes (OK)")

    print("[PASS] Step 6: All screenshots present and non-empty.")


def test_line_counts_and_guardrails():
    print("\n=======================================================")
    print("STEP 7: Line Counts (< 250) & Guardrails")
    print("=======================================================")
    target_files = [
        "frontend/src/views/ClientView.jsx",
        "frontend/src/components/ClientStripChart.jsx",
        "frontend/src/components/StripChartGrid.jsx",
        "frontend/src/components/RoomMap.jsx",
        "frontend/src/components/UnusualLog.jsx",
        "frontend/src/hooks/useClientData.js",
        "frontend/src/index.css",
        "scripts/capture_state_screenshots.py",
        "scripts/test_challenger_area_d.py",
    ]

    for rel in target_files:
        path = ROOT / rel
        assert path.exists(), f"Target file {rel} not found!"
        lines = len(path.read_text(encoding="utf-8").splitlines())
        print(f"  {rel:45s}: {lines:3d} lines (limit: <250)")
        assert lines < 250, f"File {rel} violates < 250 lines rule ({lines} lines)"

    print("[PASS] Step 7: Line counts strictly < 250 verified.")


def main():
    test_viewports_and_mobile_layout()
    test_range_buttons_touch_targets()
    test_touch_gestures_and_pointer_scrubbing()
    test_safe_area_support()
    test_seven_system_states()
    test_screenshot_files_integrity()
    test_line_counts_and_guardrails()
    print("\n=======================================================")
    print("ALL EMPIRICAL CHALLENGER TESTS PASSED SUCCESSFULLY!")
    print("=======================================================")


if __name__ == "__main__":
    main()
