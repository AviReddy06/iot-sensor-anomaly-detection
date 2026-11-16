"""
scripts/capture_state_screenshots.py
Captures the 7 distinct system states of the client UI using Playwright route mocking:
  1. loading: 'Reading the sensor.'
  2. no_data: 'No readings yet. Start the sensor or switch to the demo.'
  3. waiting: 'Collecting readings. Charts appear after about a minute.'
  4. offline: Grey dot, last seen time, charts at 60% opacity, banner 'Sensor offline since 11:32. Showing the last readings.'
  5. stale_data: Reading older than 20s adds 'Last reading 3 min ago.' to status line
  6. backend_unreachable: 'Cannot reach the monitor. Retrying in 10 s.'
  7. simulated: Amber status dot and 'Simulated' badge

Outputs:
  docs/screenshots/states_<state>_390.png (390x844)
  docs/screenshots/states_<state>_1440.png (1440x900)
"""

from __future__ import annotations
import asyncio
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from playwright.async_api import async_playwright

OUTPUT_DIR = Path("docs/screenshots")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

VIEWPORTS = [
    ("390", 390, 844),
    ("1440", 1440, 900),
]

BASE_URL = "http://127.0.0.1:8000/"

# Step 1: Generate synthetic sensor reading stream for state mocks
def generate_sample_readings(count: int = 40):
    now = datetime.now(timezone.utc)
    readings = []
    for i in range(count):
        t = now - timedelta(seconds=(count - i) * 4)
        readings.append({
            "timestamp": t.strftime("%Y-%m-%d %H:%M:%S"),
            "temperature": round(23.5 + 0.3 * (i % 5), 1),
            "humidity": round(48.0 + 0.5 * (i % 7), 1),
            "is_simulated": False,
        })
    return readings

# Step 2: Define enumeration of 7 target client system states
STATES = [
    "loading",
    "no_data",
    "waiting",
    "offline",
    "stale_data",
    "backend_unreachable",
    "simulated",
]

# Step 3: Route mocking and responsive screenshot capture per state
async def capture_state(browser, state_name: str, suffix: str, width: int, height: int):
    context = await browser.new_context(viewport={"width": width, "height": height}, device_scale_factor=1)
    page = await context.new_page()

    # Route handler
    async def handle_route(route):
        url = route.request.url
        if state_name == "loading":
            # Never complete request before page renders initial state
            await asyncio.sleep(60)
            return

        if state_name == "backend_unreachable":
            await route.abort()
            return

        if "/api/client/status" in url:
            if state_name == "no_data":
                data = {
                    "status": "Offline",
                    "current_temperature": None,
                    "current_humidity": None,
                    "last_reading_time": None,
                    "headline": "The room is normal.",
                    "active_unusual_reading": False,
                }
            elif state_name == "waiting":
                data = {
                    "status": "Live",
                    "current_temperature": 24.2,
                    "current_humidity": 48.0,
                    "last_reading_time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                    "headline": "The room is normal.",
                    "active_unusual_reading": False,
                }
            elif state_name == "offline":
                data = {
                    "status": "Offline",
                    "offline_time": "11:32",
                    "current_temperature": 22.8,
                    "current_humidity": 51.5,
                    "last_reading_time": "2026-11-14 11:32:00",
                    "headline": "The room is normal.",
                    "active_unusual_reading": False,
                }
            elif state_name == "stale_data":
                data = {
                    "status": "Live",
                    "is_stale": True,
                    "stale_text": "Last reading 3 min ago.",
                    "current_temperature": 23.4,
                    "current_humidity": 50.2,
                    "last_reading_time": (datetime.now(timezone.utc) - timedelta(minutes=3)).strftime("%Y-%m-%d %H:%M:%S"),
                    "headline": "The room is normal.",
                    "active_unusual_reading": False,
                }
            elif state_name == "simulated":
                data = {
                    "status": "Simulated",
                    "current_temperature": 25.1,
                    "current_humidity": 49.3,
                    "last_reading_time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                    "headline": "The room is normal.",
                    "active_unusual_reading": False,
                }
            else:
                data = {"status": "Live"}

            await route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(data),
            )
            return

        if "/api/client/readings" in url:
            if state_name in ("no_data", "loading"):
                readings = []
            elif state_name == "waiting":
                readings = generate_sample_readings(count=3)
            else:
                readings = generate_sample_readings(count=50)

            await route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(readings),
            )
            return

        if "/api/client/events" in url:
            await route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps([]),
            )
            return

        await route.continue_()

    await page.route("**/api/client/**", handle_route)

    try:
        if state_name == "loading":
            # Navigate without waiting for networkidle since loading route hangs intentionally
            await page.goto(BASE_URL, wait_until="domcontentloaded")
            await page.wait_for_timeout(400)
        else:
            await page.goto(BASE_URL, wait_until="networkidle")
            await page.wait_for_timeout(600)
    except Exception:
        # Ignore navigation timeout or route abort in tests
        pass

    out_file = OUTPUT_DIR / f"states_{state_name}_{suffix}.png"
    await page.screenshot(path=str(out_file), full_page=True)
    print(f"Captured {out_file.name} ({width}x{height})")
    await context.close()


# Step 4: Multi-viewport orchestration loop (390px mobile and 1440px desktop)
async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        for state in STATES:
            for suffix, w, h in VIEWPORTS:
                await capture_state(browser, state, suffix, w, h)
        await browser.close()


# Step 5: Entry point execution
if __name__ == "__main__":
    asyncio.run(main())
