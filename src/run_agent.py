#!/usr/bin/env python3

import argparse
import asyncio
import base64
import boto3
import csv
import os
import zipfile
from pathlib import Path
from datetime import datetime
import json

try:
    from .tools import navigate_and_capture
    from .wire_expected import wire_expected_for_run
except ImportError:
    # Fallback for when running as a script directly
    from tools import navigate_and_capture
    from wire_expected import wire_expected_for_run  



# Claude 3.5 Sonnet on AWS Bedrock
MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"
REGION = "us-east-1"


def encode_image_to_base64(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def suggest_test_cases(url: str, screenshot_path: str, html_content: str) -> str:
    """Generate high-level UI test cases for a given URL using Claude.

    Takes a screenshot and HTML content, then asks Claude to suggest UI test cases.
    Returns the test case suggestions as a string.
    """
    
    # Get a larger snippet of the DOM for context (increased from 20k to 100k)
    dom_snippet = html_content[:100000]
    
    # Print the HTML content to console for debugging
    print("📄 HTML Content (first 100000 characters):")
    print("=" * 50)
    print(dom_snippet)
    print("=" * 50)
    
    # Also print the total HTML length for reference
    print(f"📊 Total HTML content length: {len(html_content)} characters")
    
    # Check if dropdown options are present in the HTML
    dropdown_indicators = ["aria-expanded=\"true\"", "class=\"show\"", "aria-hidden=\"false\"", "style=\"display: block\""]
    found_indicators = []
    for indicator in dropdown_indicators:
        if indicator in html_content:
            found_indicators.append(indicator)
    
    if found_indicators:
        print(f"✅ Found dropdown indicators in HTML: {found_indicators}")
    else:
        print("⚠️ No obvious dropdown indicators found in HTML - dropdowns may not have opened properly")
    
    # Encode the screenshot for Claude
    base64_img = encode_image_to_base64(screenshot_path)
    
    prompt = (
        "You are a QA engineer analyzing a data exploration interface. Given the following DOM snippet and screenshot, "
        "generate test cases for the filter functionality on the left sidebar. "
        "Create test cases that test different filter combinations using checkboxes, text fields, and dropdowns. "
        "Each test case should be a JSON object with the following structure:\n\n"
        "{\n"
        '  "test_name": "Descriptive test name",\n'
        '  "study": "OSA01",\n'
        '  "filters": {\n'
        '    "filter_field_name": ["value1", "value2"],\n'
        '    "another_filter": ["single_value"]\n'
        '  },\n'
        '  "expected": {\n'
        '    "count": 123,\n'
        '    "description": "What this test verifies"\n'
        '  }\n'
        "}\n\n"
        "IMPORTANT: Use actual values from the DOM/screenshot, not placeholders like 'expected_number_of_results' or 'study_id'.\n"
        "Generate 5-8 test cases covering:\n"
        #"- Study should always be set to: OSA01\n" #For testing purposes only
        "- Study filter should be set using the studies from the scraped DOM/HTML or screenshot\n"
        "- Single filter selections\n"
        "- Multiple filter combinations\n"
        "- Edge cases (empty results, all results)\n"
        "- Different data types (breeds, diagnoses, demographics)\n\n"
        "CRITICAL: Return ONLY the JSON array, no explanatory text, no 'Here's a set of test cases' or similar phrases. Start your response directly with [ and end with ].\n"
        f"\n\nDOM snippet:\n{dom_snippet}"
    )

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": base64_img,
                        },
                    },
                ],
            }
        ],
        "max_tokens": 2000,
    }

    bedrock = boto3.client("bedrock-runtime", region_name=REGION)
    response = bedrock.invoke_model(
        body=json.dumps(body).encode("utf-8"),
        modelId=MODEL_ID,
        accept="application/json",
        contentType="application/json",
    )

    raw_result = response["body"].read().decode("utf-8")
    parsed = json.loads(raw_result)
    text = ""
    if "content" in parsed and isinstance(parsed["content"], list):
        for item in parsed["content"]:
            if item.get("type") == "text":
                text += item.get("text", "")

    # Try to parse the response as JSON to validate it
    try:
        # Clean up the response text to extract JSON
        cleaned_text = text.strip()
        
        # Remove markdown code blocks
        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text[7:]
        elif cleaned_text.startswith("```"):
            cleaned_text = cleaned_text[3:]
        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-3]
        
        # Remove explanatory text before JSON array
        # Look for the first '[' character which should start the JSON array
        json_start = cleaned_text.find('[')
        if json_start > 0:
            cleaned_text = cleaned_text[json_start:]
        
        # Also look for the last ']' to ensure we have a complete JSON array
        json_end = cleaned_text.rfind(']')
        if json_end > json_start:
            cleaned_text = cleaned_text[:json_end + 1]
        
        # Remove any leading/trailing whitespace
        cleaned_text = cleaned_text.strip()
        
        # Print the cleaned text for debugging
        print("🔍 Attempting to parse JSON:")
        print("=" * 30)
        print(cleaned_text[:500] + "..." if len(cleaned_text) > 500 else cleaned_text)
        print("=" * 30)
        
        # Check if the text is empty
        if not cleaned_text:
            print("❌ Empty response from AI")
            return "[]"
        
        # Parse to validate JSON structure
        test_cases = json.loads(cleaned_text)
        if isinstance(test_cases, list):
            print("✅ Successfully parsed JSON array with", len(test_cases), "test cases")
            return json.dumps(test_cases, indent=2)
        else:
            print("⚠️ Parsed JSON but it's not an array")
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing failed: {e}")
        print("📝 Raw AI response:")
        print("=" * 30)
        print(text[:1000] + "..." if len(text) > 1000 else text)
        print("=" * 30)
        print("📝 Returning raw text instead")
    
    return text.strip()



# Simplified functions for basic test case generation


# Generate an HTML report from the test case suggestions
def generate_html_report(test_cases: str, html_path: str):
    """Generate a simple HTML report with the test case suggestions."""
    
    # Escape any curly braces in the test cases to prevent format string issues
    escaped_test_cases = test_cases.replace("{", "{{").replace("}", "}}")
    
    html_content = f"""<html><head><title>UI Test Case Suggestions</title>
<style>
body {{ font-family: Arial, sans-serif; padding: 20px; line-height: 1.6; }}
h1 {{ color: #333; }}
.test-cases {{ background: #f9f9f9; padding: 20px; border-radius: 5px; }}
</style></head><body>
<h1>UI Test Case Suggestions</h1>
<div class="test-cases">
<pre>{escaped_test_cases}</pre>
</div>
</body></html>"""

    with open(html_path, "w") as f:
        f.write(html_content)


# Archive files into a ZIP
def archive_files(zip_path, files):
    with zipfile.ZipFile(zip_path, "w") as zipf:
        for file in files:
            zipf.write(file, arcname=os.path.basename(file))


# Log results to a CSV file
def log_to_csv(log_path, timestamp, screenshot, result_txt, html_report, zip_file):
    csv_exists = log_path.exists()
    with open(log_path, "a", newline="") as csvfile:
        writer = csv.writer(csvfile)
        if not csv_exists:
            writer.writerow(["Timestamp", "Screenshot", "Result File", "HTML Report", "ZIP Archive"])
        writer.writerow([timestamp, screenshot, result_txt, html_report, zip_file])


# Log trace entries to a JSONL file
def log_trace(trace_path, entry):
    with open(trace_path, "a") as f:
        f.write(json.dumps(entry) + "\n")


# Main function to run the simplified UI test case generator
def main():
    parser = argparse.ArgumentParser(description="UI Test Case Generator using Claude 3.5 on Bedrock")
    parser.add_argument("--url", required=True, help="URL of the webpage to analyze")
    parser.add_argument("--output", help="Path to save the AI response", default=None)

    args = parser.parse_args()

    # Set up output paths
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_dir = Path(f"data/runs/run_{timestamp}")
    base_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = base_dir / "screenshot.png"
    result_txt_path = base_dir / "result.txt"
    html_report_path = base_dir / "report.html"
    html_content_path = base_dir / "scraped_html.txt"
    zip_path = base_dir / "archive.zip"
    csv_log_path = base_dir / "run_log.csv"

    print(f"🌐 Navigating to {args.url}...")
    print("📸 Capturing screenshot and HTML content...")
    
    # Navigate to URL, click Continue button, and capture screenshot
    html_content = asyncio.run(navigate_and_capture(args.url, screenshot_path))
    
    if not html_content:
        print("❌ Failed to capture page content. Exiting.")
        return

    # Save the full HTML content to a text file
    with open(html_content_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"📄 Full HTML content saved to: {html_content_path}")

    print("🧪 Generating test cases via Claude 3.5 on AWS Bedrock...")
    test_cases = suggest_test_cases(args.url, screenshot_path, html_content)

    # Save results
    with open(result_txt_path, "w") as f:
        f.write(test_cases)

    # Try to save as JSON if it's valid JSON
    try:
        test_cases_json = json.loads(test_cases)
        if isinstance(test_cases_json, list):
            json_path = base_dir / "test_cases.json"
            with open(json_path, "w") as f:
                json.dump(test_cases_json, f, indent=2)
            print(f"📋 Test cases saved as JSON: {json_path}")

            # 🔗 NEW: Call backend API for expected data (no verification yet)
            try:
                wire_expected_for_run(base_dir)
                print(f"🧩 Expected results written to: {base_dir / 'expected_results.json'}")
            except Exception as e:
                print(f"⚠️ Expected results generation failed: {e}")
                print("📝 Continuing without expected results...")
    except json.JSONDecodeError:
        print("⚠️ Test cases are not in valid JSON format")

    # Generate HTML report
    generate_html_report(test_cases, html_report_path)
    
    # Create archive
    files_to_archive = [screenshot_path, result_txt_path, html_report_path, html_content_path]
    json_path = base_dir / "test_cases.json"
    if json_path.exists():
        files_to_archive.append(json_path)
    expected_path = base_dir / "expected_results.json"
    if expected_path.exists():
        files_to_archive.append(expected_path)
    archive_files(zip_path, files_to_archive)
    
    # Log to CSV
    log_to_csv(csv_log_path, timestamp, screenshot_path, result_txt_path, html_report_path, zip_path)

    # Output result
    if args.output:
        with open(args.output, "w") as f:
            f.write(test_cases)
        print(f"✅ Test cases saved to {args.output}")
    else:
        print("📝 Generated Test Cases:\n")
        print(test_cases)

    print(f"\n📄 HTML report: {html_report_path}")
    print(f"📄 Scraped HTML: {html_content_path}")
    print(f"📦 ZIP archive: {zip_path}")
    print(f"📊 Log updated: {csv_log_path}")


if __name__ == "__main__":
    main()



