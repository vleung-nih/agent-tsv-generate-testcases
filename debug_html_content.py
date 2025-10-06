#!/usr/bin/env python3
"""
Debug script to analyze HTML content after dropdown opening.
This helps identify if dropdowns are actually opening and what content is available.
"""

import asyncio
import sys
from pathlib import Path

# Add the src directory to the Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from tools import navigate_and_capture

async def debug_html_content():
    """
    Debug the HTML content to see if dropdowns are actually opening.
    """
    
    # Replace with your target URL
    test_url = "https://example.com"  # Replace with your actual target URL
    
    print("🔍 Debugging HTML Content After Dropdown Opening")
    print("=" * 60)
    print(f"Target URL: {test_url}")
    print()
    
    # Create output directory
    output_dir = Path("debug_output")
    output_dir.mkdir(exist_ok=True)
    screenshot_path = output_dir / "debug_screenshot.png"
    
    try:
        print("🚀 Starting navigation and dropdown opening...")
        html_content = await navigate_and_capture(test_url, str(screenshot_path))
        
        if html_content:
            print("✅ Successfully captured page content!")
            print(f"📊 Total HTML content length: {len(html_content)} characters")
            
            # Save full HTML content
            html_path = output_dir / "full_content.html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"📄 Full HTML saved to: {html_path}")
            
            # Analyze dropdown indicators
            print("\n🔍 Analyzing dropdown indicators...")
            dropdown_indicators = [
                ("aria-expanded=\"true\"", "Expanded elements"),
                ("aria-expanded=\"false\"", "Collapsed elements"), 
                ("class=\"show\"", "Elements with 'show' class"),
                ("style=\"display: block\"", "Elements with display: block"),
                ("style=\"display:block\"", "Elements with display:block (no space)"),
                ("aria-hidden=\"false\"", "Elements with aria-hidden=false"),
                ("dropdown-menu", "Dropdown menu elements"),
                ("filter-option", "Filter option elements"),
                ("checkbox", "Checkbox elements"),
                ("radio", "Radio button elements"),
            ]
            
            for indicator, description in dropdown_indicators:
                count = html_content.count(indicator)
                print(f"  {description}: {count} occurrences")
            
            # Look for specific filter-related content
            print("\n🎯 Looking for filter-related content...")
            filter_patterns = [
                "input[type='checkbox'",
                "input[type='radio'",
                "select",
                "option",
                "filter",
                "dropdown",
                "accordion",
                "collapse"
            ]
            
            for pattern in filter_patterns:
                count = html_content.count(pattern)
                if count > 0:
                    print(f"  Found '{pattern}': {count} occurrences")
            
            # Extract a sample of the HTML around filter-related content
            print("\n📋 Sample HTML content around filter elements...")
            lines = html_content.split('\n')
            filter_lines = []
            
            for i, line in enumerate(lines):
                if any(pattern in line.lower() for pattern in ['filter', 'dropdown', 'checkbox', 'radio', 'select', 'option']):
                    # Get context around this line
                    start = max(0, i - 2)
                    end = min(len(lines), i + 3)
                    context = lines[start:end]
                    filter_lines.extend(context)
                    if len(filter_lines) > 50:  # Limit output
                        break
            
            if filter_lines:
                sample_html = '\n'.join(filter_lines)
                print("=" * 50)
                print(sample_html)
                print("=" * 50)
            else:
                print("⚠️ No filter-related content found in HTML")
            
            # Save a searchable version
            searchable_path = output_dir / "searchable_content.txt"
            with open(searchable_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"🔍 Searchable content saved to: {searchable_path}")
            print("   You can search this file for specific terms like 'filter', 'dropdown', etc.")
            
        else:
            print("❌ Failed to capture page content")
            
    except Exception as e:
        print(f"❌ Error during debug: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🔧 HTML Content Debug Tool")
    print("This tool helps analyze what's actually in the HTML after dropdown opening.")
    print()
    print("Before running:")
    print("1. Update the test_url variable with your target website")
    print("2. Make sure the website has dropdowns in the left sidebar")
    print()
    
    # Run the debug
    asyncio.run(debug_html_content())
