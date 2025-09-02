# tools.py - Simplified for basic URL navigation and test case generation

import os
from playwright.async_api import async_playwright


async def navigate_and_capture(url: str, screenshot_path: str) -> str:
    """
    Navigate to URL, click Continue button if present, and capture screenshot.
    Returns the HTML content for analysis.
    """
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(viewport={"width": 1920, "height": 2160})
            page = await context.new_page()

            try:
                await page.goto(url, timeout=60000)
                await page.wait_for_load_state("networkidle")
            except Exception as e:
                print(f"⚠️ First navigation failed: {e}. Retrying once...")
                await page.reload()
                await page.wait_for_timeout(20000)

            # Attempt to click the 'Continue' button if it exists
            try:
                continue_button = await page.query_selector("button:has-text('Continue')")
                if continue_button:
                    await continue_button.click()
                    await page.wait_for_timeout(500)  # Wait for the action to complete
                    print("✅ Clicked 'Continue' button")
            except Exception as e:
                print(f"No 'Continue' button to click or error occurred: {e}")

            # Take a full-page screenshot
            await page.screenshot(path=screenshot_path, full_page=True)
            
            # Get HTML content for analysis
            html_content = await page.content()
            
            await browser.close()
            return html_content

    except Exception as e:
        print(f"❌ Error during navigation: {e}")
        return ""
