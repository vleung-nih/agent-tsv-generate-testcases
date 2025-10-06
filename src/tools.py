# tools.py - Simplified for basic URL navigation and test case generation

import os
from playwright.async_api import async_playwright


async def open_all_dropdowns(page):
    """
    Open all dropdowns in the left sidebar to expose filter options.
    This ensures all filter options are visible in the DOM for scraping.
    """
    try:
        print("🔍 Looking for dropdowns in the left sidebar...")
        
        # First, try to identify the left sidebar/panel
        sidebar_selectors = [
            ".sidebar",
            ".left-panel", 
            ".filter-panel",
            ".navigation",
            ".menu",
            ".filters",
            "[data-testid*='sidebar']",
            "[data-testid*='panel']",
            "[data-testid*='filter']",
            ".left-sidebar",
            ".side-panel",
            ".filter-sidebar"
        ]
        
        sidebar_element = None
        for selector in sidebar_selectors:
            try:
                element = await page.query_selector(selector)
                if element and await element.is_visible():
                    sidebar_element = element
                    print(f"  📍 Found sidebar: {selector}")
                    break
            except:
                continue
        
        # If we found a sidebar, focus our search within it
        search_context = sidebar_element if sidebar_element else page
        
        # Common selectors for dropdowns/expandable elements
        dropdown_selectors = [
            # Generic dropdown/accordion selectors
            "[data-testid*='dropdown']",
            "[data-testid*='accordion']", 
            "[data-testid*='expand']",
            "[data-testid*='collapse']",
            "[aria-expanded='false']",
            
            # Common class-based selectors
            ".dropdown-toggle",
            ".accordion-header",
            ".expandable",
            ".collapsible", 
            ".filter-group",
            ".filter-section",
            ".filter-header",
            ".filter-title",
            
            # Button selectors
            "button[aria-expanded='false']",
            "button[aria-expanded='true']",
            "button[data-toggle='collapse']",
            "button[data-bs-toggle='collapse']",
            
            # Specific to common UI frameworks
            ".ant-collapse-header",
            ".ant-menu-submenu-title", 
            ".el-collapse-item__header",
            ".v-expansion-panel-header",
            ".MuiAccordionSummary-root",
            ".chakra-accordion__button",
            
            # Generic clickable elements that might be dropdowns
            "button:has-text('▼')",
            "button:has-text('▼')", 
            "button:has-text('+')",
            "button:has-text('expand')",
            "button:has-text('show')",
            "button:has-text('more')",
            "button:has-text('filters')",
            "button:has-text('options')",
            "button:has-text('categories')",
            "button:has-text('types')",
            "button:has-text('status')",
            "button:has-text('details')",
            "button:has-text('advanced')",
        ]
        
        opened_count = 0
        
        # Search within the sidebar context
        for selector in dropdown_selectors:
            try:
                # Find all elements matching this selector within the context
                if sidebar_element:
                    elements = await sidebar_element.query_selector_all(selector)
                else:
                    elements = await page.query_selector_all(selector)
                
                for element in elements:
                    try:
                        # Check if element is visible and clickable
                        is_visible = await element.is_visible()
                        if not is_visible:
                            continue
                            
                        # Check if it's already expanded
                        aria_expanded = await element.get_attribute("aria-expanded")
                        if aria_expanded == "true":
                            continue
                            
                        # Get element text for logging
                        element_text = await element.text_content()
                        element_text = element_text.strip()[:50] if element_text else "unknown"
                            
                        # Try to click the element
                        await element.click()
                        await page.wait_for_timeout(300)  # Small delay between clicks
                        opened_count += 1
                        print(f"  ✅ Opened dropdown: '{element_text}' ({selector})")
                        
                    except Exception as e:
                        # Individual element click failed, continue with next
                        continue
                        
            except Exception as e:
                # Selector failed, continue with next
                continue
        
        # Also try to find and click any elements with common dropdown text patterns
        text_patterns = [
            "expand", "show", "more", "filters", "options", "details", 
            "advanced", "settings", "categories", "types", "status",
            "breeds", "diagnoses", "demographics", "studies", "samples"
        ]
        
        for pattern in text_patterns:
            try:
                if sidebar_element:
                    elements = await sidebar_element.query_selector_all(f"button:has-text('{pattern}')")
                else:
                    elements = await page.query_selector_all(f"button:has-text('{pattern}')")
                    
                for element in elements:
                    try:
                        if await element.is_visible():
                            await element.click()
                            await page.wait_for_timeout(300)
                            opened_count += 1
                            print(f"  ✅ Opened dropdown with text: '{pattern}'")
                    except:
                        continue
            except:
                continue
        
        print(f"🎯 Successfully opened {opened_count} dropdowns")
        
        # Wait a bit more for any animations to complete
        await page.wait_for_timeout(1000)
        
        # Debug: Check if dropdowns are actually visible in the DOM
        try:
            # Look for common dropdown content indicators
            expanded_elements = await page.query_selector_all("[aria-expanded='true']")
            visible_dropdowns = await page.query_selector_all(".show, [style*='display: block'], [style*='display:block']")
            
            print(f"🔍 Debug: Found {len(expanded_elements)} elements with aria-expanded='true'")
            print(f"🔍 Debug: Found {len(visible_dropdowns)} elements with visible dropdown classes")
            
            # Check for any filter options that might be visible now
            filter_options = await page.query_selector_all("input[type='checkbox'], input[type='radio'], select option, .filter-option, .dropdown-item")
            print(f"🔍 Debug: Found {len(filter_options)} potential filter options in DOM")
            
        except Exception as e:
            print(f"🔍 Debug: Error checking dropdown state: {e}")
        
    except Exception as e:
        print(f"⚠️ Error opening dropdowns: {e}")


async def navigate_and_capture(url: str, screenshot_path: str) -> str:
    """
    Navigate to URL, click Continue button if present, open all dropdowns, and capture screenshot.
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

            # Open all dropdowns in the left sidebar to expose filter options
            await open_all_dropdowns(page)

            # Take a full-page screenshot
            await page.screenshot(path=screenshot_path, full_page=True)
            
            # Get HTML content for analysis
            html_content = await page.content()
            
            await browser.close()
            return html_content

    except Exception as e:
        print(f"❌ Error during navigation: {e}")
        return ""
