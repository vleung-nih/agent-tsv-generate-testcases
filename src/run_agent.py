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
from smol_like_agent import SmolLikeAgent
from tools import navigate_and_capture



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
    
    # Get a snippet of the DOM for context
    dom_snippet = html_content[:2000]
    
    # Encode the screenshot for Claude
    base64_img = encode_image_to_base64(screenshot_path)
    
    prompt = (
        "You are a QA engineer. Given the following DOM snippet and screenshot, "
        "propose high-level UI test cases as a bullet list. Focus on common UI elements "
        "like navigation, buttons, forms, and content verification."
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
        "max_tokens": 400,
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
    zip_path = base_dir / "archive.zip"
    csv_log_path = base_dir / "run_log.csv"

    print(f"🌐 Navigating to {args.url}...")
    print("📸 Capturing screenshot and HTML content...")
    
    # Navigate to URL, click Continue button, and capture screenshot
    html_content = asyncio.run(navigate_and_capture(args.url, screenshot_path))
    
    if not html_content:
        print("❌ Failed to capture page content. Exiting.")
        return

    print("🧪 Generating test cases via Claude 3.5 on AWS Bedrock...")
    test_cases = suggest_test_cases(args.url, screenshot_path, html_content)

    # Save results
    with open(result_txt_path, "w") as f:
        f.write(test_cases)

    # Generate HTML report
    generate_html_report(test_cases, html_report_path)
    
    # Create archive
    archive_files(zip_path, [screenshot_path, result_txt_path, html_report_path])
    
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
    print(f"📦 ZIP archive: {zip_path}")
    print(f"📊 Log updated: {csv_log_path}")


if __name__ == "__main__":
    main()



