"""
scripts/capture_refine_c_screenshots.py
Captures Area C before/after screenshots at 1440x900 and 390x844 viewports.
"""
from __future__ import annotations
import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright

OUTPUT_DIR = Path("docs/screenshots")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


async def capture(mode: str = "before"):
    # Step 1: Define viewport resolutions
    viewports = [
        (f"refine_{mode}_C_1440.png", 1440, 900),
        (f"refine_{mode}_C_390.png", 390, 844),
    ]

    # Step 2: Launch browser and take screenshots
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        for filename, width, height in viewports:
            context = await browser.new_context(
                viewport={"width": width, "height": height},
                device_scale_factor=1,
            )
            page = await context.new_page()
            await page.goto("http://127.0.0.1:8000/", wait_until="networkidle")
            await page.wait_for_timeout(1000)

            out_path = OUTPUT_DIR / filename
            await page.screenshot(path=str(out_path), full_page=True)
            print(f"Captured {filename} at {width}x{height} -> {out_path}")
            await context.close()
        await browser.close()


if __name__ == "__main__":
    mode_arg = sys.argv[1] if len(sys.argv) > 1 else "before"
    asyncio.run(capture(mode_arg))
