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
from PIL import Image
from playwright.async_api import async_playwright
import json
from smol_like_agent import SmolLikeAgent
from tools import click_buttons_and_search, ocr_check_text, rekognition_check_object, textract_analyze_document
import re



# Claude 3.5 Sonnet on AWS Bedrock
MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"
REGION = "us-east-1"


def encode_image_to_base64(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


async def capture_screenshot(url: str, save_path: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1920, "height": 2160})
        page = await context.new_page()
        try:
            await page.goto(url, timeout=45000)
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
        except Exception as e:
            print(f"No 'Continue' button to click or error occurred: {e}")

        # Take a full-page screenshot
        await page.screenshot(path=save_path, full_page=True)
        await browser.close()


def suggest_test_cases(url: str) -> list[str]:
    """Generate high-level UI test cases for a given URL.

    This helper launches the page with Playwright, attempts to dismiss a
    "Continue" button if present, captures a screenshot and a snippet of the
    DOM, and then calls Claude on Bedrock asking for suggested UI test cases.
    The returned suggestions are written to ``result.txt`` inside a per-run
    folder under ``data/runs`` and also returned as a list of strings.
    """

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_dir = Path(f"data/runs/run_{timestamp}")
    base_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = base_dir / "screenshot.png"
    result_path = base_dir / "result.txt"

    async def _collect(url: str) -> str:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(viewport={"width": 1920, "height": 1080})
            page = await context.new_page()
            await page.goto(url, timeout=45000)
            await page.wait_for_load_state("networkidle")
            try:
                btn = await page.query_selector("button:has-text('Continue')")
                if btn:
                    await btn.click()
                    await page.wait_for_timeout(500)
            except Exception:
                pass
            html = await page.content()
            await page.screenshot(path=screenshot_path, full_page=True)
            await browser.close()
            return html

    html_content = asyncio.run(_collect(url))
    dom_snippet = html_content[:2000]

    base64_img = encode_image_to_base64(str(screenshot_path))
    prompt = (
        "You are a QA engineer. Given the following DOM snippet and screenshot, "
        "propose high-level UI test cases as a bullet list."
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

    with open(result_path, "w") as f:
        f.write(text.strip())

    return [line.strip() for line in text.strip().splitlines() if line.strip()]



# Run Claude 3.5 Sonnet on AWS Bedrock with image input
def run_claude_bedrock(prompt_text: str, image_path: str) -> str:
    base64_img = encode_image_to_base64(image_path)

    # Updated prompt structure
    full_prompt = f"""
You are a UI test agent.

Using the following screenshot:

---SCREENSHOT INCLUDED---

Verify whether the following user story is satisfied:

---USER STORY---
{prompt_text}
---END---

Respond and start with ONLY [PASS] or [FAIL] for each item, make a new line, and explain your reasoning.
"""

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": full_prompt},
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": base64_img
                        }
                    }
                ]
            }
        ],
        "max_tokens": 1024
    }

    bedrock = boto3.client("bedrock-runtime", region_name=REGION)

    response = bedrock.invoke_model(
        body=json.dumps(body).encode("utf-8"),
        modelId=MODEL_ID,
        accept="application/json",
        contentType="application/json",
    )
    return response["body"].read().decode("utf-8")


# Suggest potential test cases for a given URL using Claude
def suggest_test_cases(url: str) -> str:
    prompt = (
        "You are a QA test planner. "
        f"Suggest a list of high level test cases for the webpage located at: {url}. "
        "Return each test case on a new line starting with '- '."
    )

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
        "max_tokens": 400,
    }

    bedrock = boto3.client("bedrock-runtime", region_name=REGION)
    response = bedrock.invoke_model(
        body=json.dumps(body).encode("utf-8"),
        modelId=MODEL_ID,
        accept="application/json",
        contentType="application/json",
    )

    raw = response["body"].read().decode("utf-8")
    parsed = json.loads(raw)
    text = ""
    if "content" in parsed and isinstance(parsed["content"], list):
        for item in parsed["content"]:
            if item.get("type") == "text":
                text += item["text"]

    return text.strip()



# Agent investigates the requirement
def investigate(requirement: str, url: str, image_path: str = "screenshot.png") -> str:
    agent = SmolLikeAgent()

    async def ocr_tool(agent, req, url): 
        return await ocr_check_text(agent, req, url, image_path)

    async def rekognition_tool(agent, req, url): 
        return await rekognition_check_object(agent, req, url, image_path)

    async def textract_structured_tool(agent, req, url): 
        return await textract_analyze_document(agent, req, url, image_path)

    tool_map = {
        "ocr": ocr_tool,
        "vision": rekognition_tool,
        "dom": click_buttons_and_search,
        "textract_structured": textract_structured_tool
    }

    tools_from_claude = ask_claude_which_tools(requirement)

    if not tools_from_claude:
        print("⚠️ Claude did not suggest any tools. Falling back to ['dom', 'ocr', 'vision']")
        tools_from_claude = ["dom", "ocr", "vision"]

    # if it's a structured data check
    if any(word in requirement.lower() for word in ["table", "cell", "value"]):
        tools_from_claude.append("textract_structured")
    
    # ✅ Remove duplicates
    tools_from_claude = list(dict.fromkeys(tools_from_claude))

    for tool_name in tools_from_claude:
        tool_func = tool_map.get(tool_name)
        if tool_func:
            agent.register_tool(tool_func)

    # return asyncio.run(agent.run(requirement, url))

     # ADD DEBUG HERE:
    result = asyncio.run(agent.run(requirement, url))
    # print(f"🐛 DEBUG: investigate() returning: '{result}'")
    return result



# Ask Claude which tools to use based on the requirement
def ask_claude_which_tools(requirement: str) -> list[str]:
    prompt = f"""
You are helping a visual testing agent decide how to verify a UI requirement.

Given the requirement:
\"\"\"{requirement}\"\"\"

Choose one or more tools that should be used to verify it:
- "dom": click buttons or tabs and inspect HTML structure
- "ocr": analyze visual text from a screenshot
- "vision": detect objects (like cat, dog, chart, etc.) in a screenshot
- "textract_structured": extract structured data from documents (like tables, forms, etc.)

Respond with your reasoning and then also include a Python-style list. Make sure to always include the Python-style list, such as ["dom"]. 
If the requirement mentions tables, cells, forms, or structured data, suggest ["textract_structured"].
Example:
To verify the requirement "There should be a picture of a cat on the page," the appropriate tools would be:
["ocr","vision"]
The vision tool is best suited because...
"""

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
        "max_tokens": 100,
    }

    bedrock = boto3.client("bedrock-runtime", region_name=REGION)

    response = bedrock.invoke_model(
        body=json.dumps(body).encode("utf-8"),
        modelId=MODEL_ID,
        accept="application/json",
        contentType="application/json",
    )

    result = response["body"].read().decode("utf-8")
    parsed = json.loads(result)
    full_text = parsed["content"][0]["text"].strip()
   # text = parsed["content"][0]["text"].strip()

    # ✅ Print full reasoning from Claude
    print("🤖 Full Claude planner response:")
    print(full_text)
    #print(f"🤖 Claude planner suggestion: {text}")

    # NEW: Extract first list-like string from text
    match = re.search(r"\[.*?\]", full_text)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass

    return []  # fallback if Claude returns non-parseable text



# Get Claude to reflect on the final results of the agent
def get_claude_reflection(requirements: list[str], results: list[str]) -> str:
    joined_requirements = "\n".join(f"- {r}" for r in requirements)
    joined_results = "\n".join(results)

    prompt = f"""
You are a QA reviewer. A test agent tried to verify the following user story requirements:

{joined_requirements}

Here are the results from the test run (including original verdicts and any fallback agent attempts):

{joined_results}

Please review and reflect on the agent’s performance.

Respond with a summary that:
- Mentions if the agent did a good job or missed anything.
- Suggests improvements or follow-up checks if needed.
- Rates the confidence in the results (0-100).
"""

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
        "max_tokens": 400,
    }

    bedrock = boto3.client("bedrock-runtime", region_name=REGION)

    response = bedrock.invoke_model(
        body=json.dumps(body).encode("utf-8"),
        modelId=MODEL_ID,
        accept="application/json",
        contentType="application/json",
    )

    result = response["body"].read().decode("utf-8")
    parsed = json.loads(result)

    return parsed["content"][0]["text"]


# Generate an HTML report from the AI results
def generate_html_report(ai_result_lines, html_path):
    html_content = """<html><head><title>Visual Test Report</title>
<style>
body { font-family: Arial, sans-serif; padding: 20px; line-height: 1.6; }
.pass { color: green; }
.fail { color: red; }
.cannot-verify { color: orange; }
blockquote.reflection {
    border-left: 4px solid #ccc;
    margin: 1em 0;
    padding-left: 1em;
    color: #333;
    background: #f9f9f9;
    font-style: italic;
}
</style></head><body>
<h1>Visual Test Report</h1>
<ul>
"""

    in_reflection = False
    reflected_results = {}

    # First pass: extract verdicts from Claude Reflection
    for i, line in enumerate(ai_result_lines):
        if line.strip() == "[Claude Reflection]":
            in_reflection = True
        elif in_reflection:
            if line.strip() == "-----":
                break  # End of reflection section
            elif line.strip() in ["[PASS]", "[FAIL]", "[CANNOT BE VERIFIED]"]:
                # Grab next line as the requirement text
                requirement = ai_result_lines[i + 1].strip() if i + 1 < len(ai_result_lines) else ""
                if requirement:
                    reflected_results[requirement] = line.strip()

    # Second pass: render results, possibly overriding
    in_reflection = False
    for i, line in enumerate(ai_result_lines):
        line = line.strip()
        if line == "[Claude Reflection]":
            html_content += "</ul><h2>Claude Reflection</h2><blockquote class='reflection'>\n"
            in_reflection = True
        elif in_reflection:
            if line == "-----":
                html_content += "</blockquote><ul>\n"
                in_reflection = False
            else:
                html_content += f"{line}<br>\n"
        else:
            if any(line.startswith(v) for v in ["[PASS]", "[FAIL]", "[CANNOT BE VERIFIED]"]):
                label, _, requirement = line.partition("] ")
                requirement = requirement.strip()
                original_label = label.strip() + "]"

                # Check for Claude override
                if requirement in reflected_results and reflected_results[requirement] != original_label:
                    override_label = reflected_results[requirement]
                    css_class = "fail" if "FAIL" in override_label else "pass" if "PASS" in override_label else "cannot-verify"
                    html_content += f'<li class="{css_class}">{override_label}] {requirement} <em>(🧠 Claude override)</em></li>\n'
                else:
                    # Standard display
                    css_class = "fail" if "FAIL" in label else "pass" if "PASS" in label else "cannot-verify"
                    html_content += f'<li class="{css_class}">{line}</li>\n'
            else:
                html_content += f"<li>{line}</li>\n"

    html_content += "</ul></body></html>"

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


# Main function to run the agent
def main():
    parser = argparse.ArgumentParser(description="Visual UI Validator using Claude 3.5 on Bedrock")
    parser.add_argument("--url", required=True, help="URL of the webpage to validate")
    parser.add_argument("--output", help="Path to save the AI response", default=None)

    args = parser.parse_args()


    # Set up output paths
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_dir = Path(f"data/runs/run_{timestamp}")  # Create a folder for each run
    base_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = base_dir / f"screenshot.png"
    result_txt_path = base_dir / f"result.txt"
    html_report_path = base_dir / f"report.html"
    zip_path = base_dir / f"archive.zip"
    csv_log_path = base_dir / "run_log.csv"

    print(f"📸 Capturing screenshot from {args.url} ...")
    asyncio.run(capture_screenshot(args.url, screenshot_path))

    print("🧪 Suggesting test cases via Claude 3.5 on AWS Bedrock...")
    result = suggest_test_cases(args.url)

    with open(result_txt_path, "w") as f:
        f.write(result)

    result_lines = result.strip().splitlines()

    generate_html_report(result_lines, html_report_path)
    archive_files(zip_path, [screenshot_path, result_txt_path, html_report_path])
    log_to_csv(csv_log_path, timestamp, screenshot_path, result_txt_path, html_report_path, zip_path)

    # Output result or summary
    if args.output:
        with open(args.output, "w") as f:
            f.write(result)
        print(f"✅ Raw result saved to {args.output}")
    else:
        print("📝 Claude AI Result:\n")
        print(result)

    print(f"📄 HTML report: {html_report_path}")
    print(f"📦 ZIP archive: {zip_path}")
    print(f"📊 Log updated: {csv_log_path}")


if __name__ == "__main__":
    main()



