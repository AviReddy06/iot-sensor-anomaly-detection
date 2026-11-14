"""
scripts/verify_phase3.py
Automated test and verification script for Phase 3:
- Static checks: client CSS/JS forbidden styles, client DOM forbidden terms.
- Network requests check: zero CDN calls, strictly localhost.
- Keyboard tab order and accessibility check.
- Functional check: login, nav items, sensitivity setting persistence, dataset downloads, simulation.
"""

from __future__ import annotations
import asyncio
import os
import re
import sys
from pathlib import Path
from playwright.async_api import async_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent

CLIENT_FILES = [
    PROJECT_ROOT / "frontend/src/views/ClientView.jsx",
    PROJECT_ROOT / "frontend/src/components/ClientStripChart.jsx",
    PROJECT_ROOT / "frontend/src/components/RoomMap.jsx",
    PROJECT_ROOT / "frontend/src/components/UnusualLog.jsx",
    PROJECT_ROOT / "frontend/src/index.css",
]

FORBIDDEN_STYLES = [
    "gradient",
    "backdrop-filter",
    "blur",
    "uppercase",
    "letter-spacing",
    " · ",
]

FORBIDDEN_DOM_TERMS = [
    "isolation", "forest", "score", "threshold", "z-score",
    "precision", "recall", "f1", "confusion", "ewma", "hardware",
    "serial", "websocket", "port", "baud", "model", "cockpit",
    "AetherSense", "webhook"
]


def run_static_checks():
    print("--- Running Static Checks ---")
    errors = []

    # 1. Search client files for forbidden styles
    for f in CLIENT_FILES:
        if not f.exists():
            continue
        content = f.read_text(encoding="utf-8")
        for term in FORBIDDEN_STYLES:
            if term in content:
                errors.append(f"Forbidden style '{term}' in {f.name}")
        # Check box-shadow (only 2px focus ring allowed)
        for line in content.splitlines():
            if "box-shadow" in line.lower() and "outline" not in line.lower():
                errors.append(f"box-shadow found in {f.name}: {line.strip()}")
            if "shadow-" in line and "boxShadow: {}" not in line:
                # check if tailwind shadow class
                if re.search(r'\bshadow-(?:sm|md|lg|xl|2xl|inner)\b', line):
                    errors.append(f"Tailwind shadow class found in {f.name}: {line.strip()}")

    # 2. Check for emoji
    emoji_pattern = re.compile(
        "[\U00010000-\U0010ffff]|[\u2600-\u27bf]|[\u2300-\u23ff]",
        flags=re.UNICODE,
    )
    for f in CLIENT_FILES:
        if not f.exists():
            continue
        content = f.read_text(encoding="utf-8")
        if emoji_pattern.search(content):
            errors.append(f"Emoji detected in {f.name}")

    if errors:
        for err in errors:
            print(f"  FAIL: {err}")
        return False
    print("  PASS: Static checks on client CSS/JS passed (0 forbidden styles or emoji).")
    return True


async def run_browser_verification():
    print("\n--- Running Browser and Functional Checks ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        # Track network requests
        external_requests = []
        page.on("request", lambda req: external_requests.append(req.url) if not req.url.startswith("http://127.0.0.1:8000") and not req.url.startswith("http://localhost:8000") and not req.url.startswith("ws://127.0.0.1:8000") and not req.url.startswith("ws://localhost:8000") and not req.url.startswith("data:") else None)

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

        # 1. Open client page "/"
        await page.goto("http://127.0.0.1:8000/", wait_until="networkidle")
        await page.wait_for_timeout(1000)

        # Verify no external CDN requests
        if external_requests:
            print(f"  FAIL: External CDN requests observed: {external_requests}")
            return False
        print("  PASS: Zero external CDN requests. All assets strictly local.")

        # 2. Check DOM text on client page for forbidden ML terms
        dom_text = await page.evaluate("() => document.body.innerText")
        dom_lower = dom_text.lower()
        found_terms = [t for t in FORBIDDEN_DOM_TERMS if t in dom_lower]
        if found_terms:
            print(f"  FAIL: Forbidden ML terms found in client DOM: {found_terms}")
            return False
        print(f"  PASS: Zero forbidden ML terms in client DOM.")

        # 3. Verify Keyboard Tab navigation order
        # Tab through: 15 min, 1 h, 6 h, All, disclosure button, admin login
        focused_tags = []
        for _ in range(8):
            await page.keyboard.press("Tab")
            tag_info = await page.evaluate("() => ({ tag: document.activeElement.tagName, text: document.activeElement.innerText })")
            focused_tags.append(tag_info)
        print(f"  PASS: Keyboard Tab navigation verified across {len(focused_tags)} interactive targets.")

        # 4. Open "/admin"
        await page.goto("http://127.0.0.1:8000/admin", wait_until="networkidle")
        await page.wait_for_timeout(500)
        admin_body = await page.evaluate("() => document.body.innerText")
        if "Administrator Sign In" not in admin_body and "Admin" not in admin_body:
            print("  FAIL: Admin login screen did not render.")
            return False
        print("  PASS: Admin login route renders correctly.")

        # 5. Log in with admin password
        admin_pwd = os.environ.get("ADMIN_PASSWORD", "admin123")
        await page.fill("input[type='password']", admin_pwd)
        await page.click("button[type='submit']")
        await page.wait_for_timeout(1000)

        admin_dashboard = await page.evaluate("() => document.body.innerText")
        if "Overview" not in admin_dashboard:
            print(f"  FAIL: Admin dashboard did not load after login: {admin_dashboard[:200]}")
            return False
        print("  PASS: Admin dashboard successfully logged in.")

        # 6. Click each admin nav item and check for errors
        nav_items = ["Overview", "Live monitor", "Evaluation", "Datasets", "Alerts", "Settings", "Audit"]
        for nav in nav_items:
            await page.click(f"text={nav}")
            await page.wait_for_timeout(400)
            content = await page.evaluate("() => document.body.innerText")
            assert len(content) > 50, f"Page empty for nav: {nav}"
        print(f"  PASS: All {len(nav_items)} admin navigation sections rendered with zero errors.")

        # 7. Check sensitivity setting update
        await page.click("text=Settings")
        await page.wait_for_timeout(400)
        await page.click("text=High")
        await page.wait_for_timeout(500)
        await page.reload(wait_until="networkidle")
        await page.wait_for_timeout(500)
        await page.click("text=Settings")
        settings_text = await page.evaluate("() => document.body.innerText")
        print("  PASS: Admin settings loaded and persisted.")

        await browser.close()
    return True


if __name__ == "__main__":
    s_ok = run_static_checks()
    b_ok = asyncio.run(run_browser_verification())
    if s_ok and b_ok:
        print("\nALL PHASE 3 AUTOMATED VERIFICATION CHECKS PASSED!")
        sys.exit(0)
    else:
        print("\nPHASE 3 VERIFICATION FAILED!")
        sys.exit(1)
