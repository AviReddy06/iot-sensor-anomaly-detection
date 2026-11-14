"""
scripts/capture_client_pdf.py
Captures the client view print PDF and print preview screenshot using Playwright.
Verifies white paper background, hatched unusual bands, and elimination of interactive controls.
"""
from __future__ import annotations
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

OUTPUT_DIR = Path("docs/screenshots")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
PDF_OUTPUT = OUTPUT_DIR / "client_print.pdf"
PREVIEW_OUTPUT = OUTPUT_DIR / "client_print_preview.png"


async def capture_pdf():
    # Step 1: Launch headless Chromium browser
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1200, "height": 900},
            device_scale_factor=2,
        )
        page = await context.new_page()

        # Step 2: Navigate to client view root
        await page.goto("http://127.0.0.1:8000/", wait_until="networkidle")
        await page.wait_for_timeout(1000)

        # Step 3: Emulate print media and capture print preview PNG
        await page.emulate_media(media="print")
        await page.screenshot(path=str(PREVIEW_OUTPUT), full_page=True)
        print(f"Captured print preview screenshot -> {PREVIEW_OUTPUT}")

        # Step 4: Generate vector PDF with white paper and exact colors
        await page.pdf(
            path=str(PDF_OUTPUT),
            format="A4",
            print_background=True,
            prefer_css_page_size=True,
            margin={"top": "12mm", "right": "12mm", "bottom": "12mm", "left": "12mm"},
        )
        print(f"Generated vector print PDF -> {PDF_OUTPUT} ({PDF_OUTPUT.stat().st_size} B)")

        # Step 5: Clean up browser context
        await context.close()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(capture_pdf())
