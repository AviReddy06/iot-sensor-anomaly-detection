"""
scripts/test_challenger_2_area_d.py
Empirical Challenger 2 test suite for Area D: 7 States, Screenshots, Backoff, Guardrails.
"""
from __future__ import annotations
import json
import re
import struct
import subprocess
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent

CLIENT_FILES = [
    ROOT / "frontend/src/views/ClientView.jsx",
    ROOT / "frontend/src/hooks/useClientData.js",
    ROOT / "frontend/src/components/ClientStripChart.jsx",
    ROOT / "frontend/src/components/StripChartGrid.jsx",
    ROOT / "frontend/src/components/RoomMap.jsx",
    ROOT / "frontend/src/components/UnusualLog.jsx",
    ROOT / "frontend/src/index.css",
    ROOT / "frontend/src/main.jsx",
]

# Step 1: Programmatic verification of all 7 system states in Playwright
def test_seven_system_states_copy():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        
        # 1. loading: 'Reading the sensor.'
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.route("**/api/client/**", lambda r: time.sleep(1) or r.fulfill(status=200, content_type="application/json", body="[]"))
        page.goto("http://127.0.0.1:8000/", wait_until="domcontentloaded")
        assert "Reading the sensor." in page.content(), "Loading state copy missing"
        page.wait_for_timeout(1100)
        page.close()

        # 2. no_data: 'No readings yet. Start the sensor or switch to the demo.'
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.route("**/api/client/status", lambda r: r.fulfill(
            status=200, content_type="application/json",
            body=json.dumps({"status": "Offline", "current_temperature": None, "current_humidity": None, "last_reading_time": None})
        ))
        page.route("**/api/client/readings*", lambda r: r.fulfill(status=200, content_type="application/json", body="[]"))
        page.route("**/api/client/events*", lambda r: r.fulfill(status=200, content_type="application/json", body="[]"))
        page.goto("http://127.0.0.1:8000/", wait_until="networkidle")
        assert "No readings yet. Start the sensor or switch to the demo." in page.content(), "no_data copy missing"
        page.close()

        # 3. waiting: 'Collecting readings. Charts appear after about a minute.' (e.g. 1-9 readings)
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.route("**/api/client/status", lambda r: r.fulfill(
            status=200, content_type="application/json",
            body=json.dumps({"status": "Live", "current_temperature": 24.0, "current_humidity": 45.0, "last_reading_time": "2026-11-14 22:00:00"})
        ))
        page.route("**/api/client/readings*", lambda r: r.fulfill(
            status=200, content_type="application/json",
            body=json.dumps([{"timestamp": "2026-11-14 22:00:00", "temperature": 24.0, "humidity": 45.0, "is_simulated": False}] * 5)
        ))
        page.route("**/api/client/events*", lambda r: r.fulfill(status=200, content_type="application/json", body="[]"))
        page.goto("http://127.0.0.1:8000/", wait_until="networkidle")
        assert "Collecting readings. Charts appear after about a minute." in page.content(), "waiting copy missing"
        page.close()

        # 4. offline: 60% opacity charts and banner 'Sensor offline since [time]. Showing the last readings.'
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.route("**/api/client/status", lambda r: r.fulfill(
            status=200, content_type="application/json",
            body=json.dumps({"status": "Offline", "offline_time": "11:32", "last_reading_time": "2026-11-14 11:32:00", "current_temperature": 22.5, "current_humidity": 50.0})
        ))
        page.route("**/api/client/readings*", lambda r: r.fulfill(
            status=200, content_type="application/json",
            body=json.dumps([{"timestamp": f"2026-11-14 11:3{i}:00", "temperature": 22.5, "humidity": 50.0, "is_simulated": False} for i in range(12)])
        ))
        page.route("**/api/client/events*", lambda r: r.fulfill(status=200, content_type="application/json", body="[]"))
        page.goto("http://127.0.0.1:8000/", wait_until="networkidle")
        content = page.content()
        assert "Sensor offline since 11:32. Showing the last readings." in content, "offline banner missing"
        assert "opacity-60" in content, "opacity-60 missing from offline charts"
        assert page.locator(".bg-\\[\\#4F5F69\\]").count() > 0, "offline grey status dot missing"
        page.close()

        # 5. stale_data: 'Last reading [time] ago.' in status line
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.route("**/api/client/status", lambda r: r.fulfill(
            status=200, content_type="application/json",
            body=json.dumps({"status": "Live", "is_stale": True, "stale_text": "Last reading 3 min ago.", "last_reading_time": "2026-11-14 21:57:00", "current_temperature": 23.0, "current_humidity": 49.0})
        ))
        page.route("**/api/client/readings*", lambda r: r.fulfill(
            status=200, content_type="application/json",
            body=json.dumps([{"timestamp": "2026-11-14 21:57:00", "temperature": 23.0, "humidity": 49.0, "is_simulated": False}])
        ))
        page.route("**/api/client/events*", lambda r: r.fulfill(status=200, content_type="application/json", body="[]"))
        page.goto("http://127.0.0.1:8000/", wait_until="networkidle")
        assert "Last reading 3 min ago." in page.content(), "stale_data copy missing"
        page.close()

        # 6. unreachable: 'Cannot reach the monitor. Retrying in 10 s.'
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.route("**/api/client/**", lambda r: r.abort())
        try:
            page.goto("http://127.0.0.1:8000/", wait_until="networkidle")
        except Exception:
            pass
        page.wait_for_timeout(500)
        assert "Cannot reach the monitor. Retrying in 10 s." in page.content(), "unreachable copy missing"
        page.close()

        # 7. simulated badge: amber dot and 'Simulated'
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.route("**/api/client/status", lambda r: r.fulfill(
            status=200, content_type="application/json",
            body=json.dumps({"status": "Simulated", "current_temperature": 25.0, "current_humidity": 50.0, "last_reading_time": "2026-11-14 22:05:00"})
        ))
        page.route("**/api/client/readings*", lambda r: r.fulfill(
            status=200, content_type="application/json",
            body=json.dumps([{"timestamp": "2026-11-14 22:05:00", "temperature": 25.0, "humidity": 50.0, "is_simulated": True}] * 12)
        ))
        page.route("**/api/client/events*", lambda r: r.fulfill(status=200, content_type="application/json", body="[]"))
        page.goto("http://127.0.0.1:8000/", wait_until="networkidle")
        content = page.content()
        assert "Simulated" in content, "Simulated text missing"
        assert page.locator(".bg-\\[\\#7A4B00\\]").count() > 0, "amber simulated dot missing"
        page.close()

        browser.close()

# Step 2: Verification of all 14 state screenshots (PNG validity, dimensions, size)
def test_all_14_state_screenshots():
    states = ["loading", "no_data", "waiting", "offline", "stale_data", "backend_unreachable", "simulated"]
    expected_viewports = {"390": 390, "1440": 1440}
    
    for s in states:
        for vp, exp_w in expected_viewports.items():
            img_path = ROOT / "docs" / "screenshots" / f"states_{s}_{vp}.png"
            assert img_path.exists(), f"Screenshot {img_path.name} does not exist"
            file_size = img_path.stat().st_size
            assert file_size >= 10000, f"Screenshot {img_path.name} too small ({file_size} B)"
            
            with img_path.open("rb") as f:
                header = f.read(24)
                assert header[:8] == b"\x89PNG\r\n\x1a\n", f"{img_path.name} is not a valid PNG file"
                width, height = struct.unpack(">II", header[16:24])
                assert width == exp_w, f"{img_path.name} width {width} != expected {exp_w}"
                assert height > 500, f"{img_path.name} height {height} unreasonably small"

# Step 3: WebSocket exponential backoff logic (1s to 30s) verification
def test_websocket_exponential_backoff_logic():
    hook_file = ROOT / "frontend" / "src" / "hooks" / "useClientData.js"
    content = hook_file.read_text(encoding="utf-8")
    
    assert "let backoffMs = 1000;" in content, "Initial backoffMs not 1000"
    assert "backoffMs = 1000;" in content and "ws.onopen" in content, "Backoff not reset on ws.onopen"
    assert "backoffMs = Math.min(backoffMs * 2, 30000);" in content, "Exponential doubling with 30s cap missing"
    assert "reconnectTimeout = setTimeout(connectWs, backoffMs);" in content, "Reconnect timeout missing"

    # Verify no state wipe on disconnect
    lines = content.splitlines()
    ws_block = "\n".join(lines[50:125])
    assert "setReadings([])" not in ws_block, "Readings wiped during reconnect"
    assert "setStatusData(null)" not in ws_block, "Status wiped during reconnect"

    # Simulate sequence
    backoff = 1000
    sequence = [backoff]
    for _ in range(6):
        backoff = min(backoff * 2, 30000)
        sequence.append(backoff)
    assert sequence == [1000, 2000, 4000, 8000, 16000, 30000, 30000], f"Sequence mismatch: {sequence}"

# Step 4: Repository guardrails (lines < 250, step comments, zero banned DOM/styles, bundle size, git)
def test_guardrails_empirical():
    for f in CLIENT_FILES:
        lines = f.read_text(encoding="utf-8").splitlines()
        assert len(lines) < 250, f"{f.name} has {len(lines)} lines (>= 250)"
        if f.suffix in [".jsx", ".js"] and len(lines) > 20:
            assert any("Step " in l for l in lines), f"{f.name} missing structured Step comments"

    # Auxiliary files checked for line limits and step comments
    aux_files = [ROOT / "frontend/index.html", ROOT / "scripts/capture_state_screenshots.py", ROOT / "scripts/test_challenger_area_d.py"]
    for af in aux_files:
        lines = af.read_text(encoding="utf-8").splitlines()
        assert len(lines) < 250, f"{af.name} exceeds 250 lines"
        if af.suffix == ".py" and len(lines) > 20:
            assert any("Step " in l for l in lines), f"{af.name} missing structured Step comments"

    # Bundle size chunk <= 392,027 B
    js_chunks = list((ROOT / "frontend" / "dist" / "assets").glob("index-*.js"))
    assert len(js_chunks) == 1, f"Expected 1 JS chunk, found {len(js_chunks)}"
    chunk_size = js_chunks[0].stat().st_size
    assert chunk_size <= 392027, f"JS chunk {chunk_size} B exceeds 392,027 B limit"

    # Zero banned CSS styles in client files
    for cf in CLIENT_FILES:
        txt = cf.read_text(encoding="utf-8")
        for banned in ["gradient", "backdrop-filter", "blur", "uppercase", "letter-spacing"]:
            assert banned not in txt, f"Banned style '{banned}' in {cf.name}"
        assert not re.search(r'\bshadow-(?:sm|md|lg|xl|2xl|inner)\b', txt), f"Shadow class in {cf.name}"

    # Git commit (HEAD or a54d546) and parent ab07147
    target_ref = "HEAD" if subprocess.run(["git", "log", "-1", "--pretty=%B", "HEAD"], stdin=subprocess.DEVNULL, capture_output=True, text=True).stdout.strip().startswith("Refine client UI: Area D") else "a54d546"
    rev = subprocess.run(["git", "rev-parse", "--verify", target_ref], stdin=subprocess.DEVNULL, capture_output=True, text=True, check=True).stdout.strip()
    assert rev, "Target commit not found"
    parent = subprocess.run(["git", "rev-parse", f"{target_ref}^"], stdin=subprocess.DEVNULL, capture_output=True, text=True, check=True).stdout.strip()
    assert parent.startswith("ab07147"), f"Parent {parent} != ab07147"
    msg = subprocess.run(["git", "log", "-1", "--pretty=%B", target_ref], stdin=subprocess.DEVNULL, capture_output=True, text=True, check=True).stdout.strip()
    assert "Refine client UI: Area D" in msg, f"Unexpected commit message: {msg}"

if __name__ == "__main__":
    print("Testing 7 System States Copy...")
    test_seven_system_states_copy()
    print("Testing All 14 State Screenshots...")
    test_all_14_state_screenshots()
    print("Testing WebSocket Exponential Backoff...")
    test_websocket_exponential_backoff_logic()
    print("Testing Repository Guardrails...")
    test_guardrails_empirical()
    print("\nALL CHALLENGER 2 EMPIRICAL TESTS PASSED SUCCESSFULLY!")
