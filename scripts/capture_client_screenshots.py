"""
scripts/capture_client_screenshots.py
Captures client view screenshots at 1440px, 768px, and 390px widths using Playwright.
"""

from __future__ import annotations
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

OUTPUT_DIR = Path("docs/screenshots")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

VIEWPORTS = [
    ("client_final_1440.png", 1440, 900),
    ("client_final_768.png", 768, 1024),
    ("client_final_390.png", 390, 844),
]


async def capture():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        for filename, width, height in VIEWPORTS:
            context = await browser.new_context(
                viewport={"width": width, "height": height},
                device_scale_factor=1,
            )
            page = await context.new_page()
            # Navigate to client root
            await page.goto("http://127.0.0.1:8000/", wait_until="networkidle")
            # Wait for content to render
            await page.wait_for_timeout(1000)

            out_path = OUTPUT_DIR / filename
            await page.screenshot(path=str(out_path), full_page=True)
            print(f"Captured {filename} at {width}x{height} -> {out_path}")
            await context.close()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(capture())
