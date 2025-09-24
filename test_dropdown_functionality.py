#!/usr/bin/env python3
"""
Test script to demonstrate the enhanced dropdown opening functionality.
This script shows how the agent will now open all dropdowns before scraping.
"""

import asyncio
import sys
from pathlib import Path

# Add the src directory to the Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from tools import navigate_and_capture

async def test_dropdown_functionality():
    """
    Test the enhanced dropdown opening functionality.
    Replace the URL with your target website.
    """
    
    # Example URL - replace with your actual target website
    test_url = "https://example.com"  # Replace with your target URL
    
    print("🧪 Testing Enhanced Dropdown Opening Functionality")
    print("=" * 60)
    print(f"Target URL: {test_url}")
    print()
    
    # Create output directory
    output_dir = Path("test_output")
    output_dir.mkdir(exist_ok=True)
    screenshot_path = output_dir / "test_screenshot.png"
    
    try:
        print("🚀 Starting navigation and dropdown opening...")
        html_content = await navigate_and_capture(test_url, str(screenshot_path))
        
        if html_content:
            print("✅ Successfully captured page content with dropdowns opened!")
            print(f"📸 Screenshot saved to: {screenshot_path}")
            print(f"📄 HTML content length: {len(html_content)} characters")
            
            # Save HTML content for inspection
            html_path = output_dir / "test_content.html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"📄 HTML content saved to: {html_path}")
            
        else:
            print("❌ Failed to capture page content")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")

if __name__ == "__main__":
    print("🔧 Enhanced Autonomous UI Validator - Dropdown Test")
    print("This test demonstrates the new dropdown opening functionality.")
    print()
    print("Before running this test:")
    print("1. Update the test_url variable with your target website")
    print("2. Make sure the website has a 'Continue' button")
    print("3. Ensure the website has dropdowns in the left sidebar")
    print()
    
    # Run the test
    asyncio.run(test_dropdown_functionality())
