import re
from PIL import Image
import pytesseract
from playwright.async_api import async_playwright
import asyncio
import boto3
import json
import asyncio
import base64
import os
from pathlib import Path
from PIL import Image
from typing import List
import io


# Claude-Based Action Planner -- Let Claude parse the requirement into a step-by-step plan for browser actions:
def extract_ui_plan_from_claude(requirement: str) -> list[dict]:
    prompt = f"""
You are a UI test planning agent.

Given the requirement:
\"\"\"{requirement}\"\"\"

Break it into a list of step-by-step structured actions. Use this sample format:
[
  {{"action": "click", "target": "ABOUT"}},
  {{"action": "verify_text", "target": "Steering Committee"}}
]
Understand the requirement-- if the element to verify is in quotations such as "Steering Committee", only include the exact text within the quotes as the target.
Try to include only actions such as "click", "verify_text", "navigate", "verify_element_present", "verify_element_count".
Only include the list. Do not explain anything else.
"""

    MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"
    REGION = "us-east-1"
    bedrock = boto3.client("bedrock-runtime", region_name=REGION)

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
        "max_tokens": 300,
    }

    response = bedrock.invoke_model(
        body=json.dumps(body).encode("utf-8"),
        modelId=MODEL_ID,
        accept="application/json",
        contentType="application/json",
    )

    raw = response["body"].read().decode("utf-8")
    parsed = json.loads(raw)
    text = parsed["content"][0]["text"].strip()

    # ✅ Print full reasoning from Claude
    print("🤖 UI plan from Claude:")
    print(text)

    try:
        plan = json.loads(text)
        if isinstance(plan, list):
            return plan
    except Exception:
        pass

    return []


# Playwright tool to click buttons and search for text based on the plan from Claude
async def click_buttons_and_search(agent, requirement: str, url: str) -> str:
    print("📋 Using Claude to extract UI plan...")
    plan = extract_ui_plan_from_claude(requirement)
    print("🤖 UI plan from Claude:")
    print(json.dumps(plan, indent=2))

    screenshot_dir = "step_screenshots"
    os.makedirs(screenshot_dir, exist_ok=True)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(viewport={"width": 1920, "height": 2160})
            page = await context.new_page()

            try:
                await page.goto(url, timeout=60000)
            except Exception as e:
                print(f"⚠️ First navigation failed: {e}. Retrying once...")
                try:
                    await page.reload(timeout=60000)
                except Exception as e2:
                    print(f"❌ Retry failed: {e2}")
                    return f"[FAIL] Could not load page: {e2}"
                
            # Attempt to click the 'Continue' button if it exists
            try:
                continue_button = await page.query_selector("button:has-text('Continue')")
                if continue_button:
                    await continue_button.click()
                    await page.wait_for_timeout(500)  # Wait for the action to complete
            except Exception as e:
                print(f"No 'Continue' button to click or error occurred: {e}")

            results = []
            step_num = 1

            for step in plan:
                action = step.get("action", "").lower()
                target = step.get("target", "")
                expected = step.get("expected") or step.get("expected_count")
                print(f"👉 Step {step_num}: {action.upper()} '{target}'")

                try:
                    if action == "click":
                        button = await page.query_selector(f"text={target}")
                        if button and await button.is_enabled():
                            await button.click()
                            results.append(f"[PASS] Clicked {target}")
                        else:
                            results.append(f"[FAIL] Could not find or click {target}")

                    elif action == "verify_text":
                        content = await page.content()
                        if target.lower() in content.lower():
                            results.append(f"[PASS] Found text: {target}")
                        else:
                            results.append(f"[FAIL] Missing text: {target}")

                    elif action == "verify_element_count":
                        elements = await page.query_selector_all("a")
                        count = len(elements)
                        if count == expected:
                            results.append(f"[PASS] Found {count} links (as expected)")
                        else:
                            results.append(f"[FAIL] Found {count} links; expected {expected}")

                    elif action in ["navigate", "navigate_to_site"]:
                        results.append(f"[INFO] Skipping navigation action: {target}")

                    elif action == "verify_element_present":
                        # Try a more relaxed match first
                        element = await page.query_selector(f"text=\"{target}\"")

                        # Fallback: try partial match with key phrase (e.g., just "Steering Committee")
                        if not element:
                            simplified = re.findall(r"[\w\s]+", target)
                            if simplified:
                                keywords = [s.strip() for s in simplified if len(s.strip()) > 3]
                                for keyword in keywords:
                                    element = await page.query_selector(f"text={keyword}")
                                    if element:
                                        break

                        if element:
                            results.append(f"[PASS] Element '{target}' is present")
                        else:
                            results.append(f"[FAIL] Element '{target}' is not present")


                    else:
                        results.append(f"[WARN] Unknown action '{action}' for target '{target}'")

                    # 📸 Save screenshot after each step
                    screenshot_file = os.path.join(screenshot_dir, f"step{step_num}_{action}_{target.replace(' ', '_')}.png")
                    await page.screenshot(path=screenshot_file)
                    print(f"📸 Saved screenshot: {screenshot_file}")

                except Exception as step_error:
                    results.append(f"[FAIL] Step '{action} {target}' errored: {step_error}")

                step_num += 1

            return "\n".join(results)

    except Exception as final_error:
        return f"[FAIL] Unexpected error: {final_error}"



# --- Helper: Ask Claude what to detect in the image for AWS Rekognition---
def get_rekognition_labels_from_claude(requirement: str) -> list[str]:
    prompt = f"""
You are helping an AI visual test agent decide what objects to look for in a screenshot using a vision model.

The requirement is:
\"\"\"{requirement}\"\"\"

List the key visual object or concept to look for. Return a Python list of 1-3 keywords. Example:
["cat"]
or
["donut chart", "legend"]

Only return the list, nothing else.
"""

    MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"
    REGION = "us-east-1"
    bedrock = boto3.client("bedrock-runtime", region_name=REGION)

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
        "max_tokens": 100
    }

    response = bedrock.invoke_model(
        body=json.dumps(body).encode("utf-8"),
        modelId=MODEL_ID,
        accept="application/json",
        contentType="application/json",
    )

    raw = response["body"].read().decode("utf-8")
    parsed = json.loads(raw)
    content = parsed["content"][0]["text"].strip()

    try:
        return json.loads(content)
    except Exception:
        return []
    

# AWS Rekognition managed service to check for objects in an image
async def rekognition_check_object(agent, requirement: str, url: str, image_path: str = "screenshot.png") -> bool:
    agent.log("🖼️ Asking Claude what object(s) to detect in the image...")
    target_labels = get_rekognition_labels_from_claude(requirement)

    if not target_labels:
        agent.log("⚠️ Claude could not identify a target label. Skipping vision detection.")
        return False

    agent.log(f"🎯 Claude says to look for: {target_labels}")

    try:
        rekognition = boto3.client("rekognition")
        with open(image_path, "rb") as image_file:
            response = rekognition.detect_labels(
                Image={"Bytes": image_file.read()},
                MaxLabels=25,
                MinConfidence=70
            )

        detected_labels = [label["Name"].lower() for label in response["Labels"]]
        agent.log(f"🔍 Rekognition detected: {detected_labels}")

        for label in target_labels:
            if label.lower() in detected_labels:
                agent.log(f"✅ Found '{label}' in the image.")
                return True

        agent.log(f"❌ None of the target labels {target_labels} were found.")
        return False

    except Exception as e:
        agent.log(f"⚠️ Rekognition error: {e}")
        return False



# AWS Textract managed service to extract text from an image using OCR
async def ocr_check_text(agent, requirement: str, url: str, image_path: str) -> str:
    print("🔍 Using Textract to search for text in the screenshot...")

    textract = boto3.client("textract", region_name="us-east-1")

    try:
        with open(image_path, "rb") as image_file:
            image_bytes = image_file.read()

        response = textract.detect_document_text(
            Document={"Bytes": image_bytes}
        )

        lines = [
            item["Text"]
            for item in response.get("Blocks", [])
            if item["BlockType"] == "LINE"
        ]

        print("📄 Textract detected the following lines:")
        for line in lines:
            print(" •", line)

        from difflib import SequenceMatcher

        quoted = re.findall(r'"([^"]+)"', requirement)
        if not quoted:
            print(f"⚠️ No quoted string found in requirement: {requirement}")
            return "[FAIL] Requirement must include quoted text to evaluate."
        targets = quoted


        matches = []
        for target in targets:
            for line in lines:
                ratio = SequenceMatcher(None, target.lower(), line.lower()).ratio()
                print(f"🔍 Comparing '{target}' to OCR line '{line}' => similarity: {ratio:.2f}")
                if ratio >= 0.85:
                    matches.append(target)
                    break

        if matches:
            return f"[PASS] Found text via fuzzy match: {', '.join(matches)}"
        else:
            return f"[FAIL] Did not find: {', '.join(targets)}"

    except Exception as e:
        return f"[FAIL] Textract error: {e}"



# AWS Textract managed service to extract structured data from an image
async def textract_analyze_document(agent, requirement: str, url: str, image_path: str) -> str:
    print("📊 Using Textract AnalyzeDocument to extract table/form data...")

    client = boto3.client("textract", region_name="us-east-1")

    try:
        with open(image_path, "rb") as img:
            bytes_data = img.read()

        response = client.analyze_document(
            Document={"Bytes": bytes_data},
            FeatureTypes=["TABLES", "FORMS"]
        )

        lines = []
        for block in response["Blocks"]:
            if block.get("BlockType") in ("KEY_VALUE_SET", "CELL", "LINE"):
                if "Text" in block:
                    lines.append(block["Text"])
                else:
                    print(f"⚠️ Skipping block without 'Text': {block.get('BlockType')} block with ID {block.get('Id')}")

        combined_text = "\n".join(lines)

        print("📄 Textract structured text:")
        print(combined_text)

        from difflib import SequenceMatcher

        quoted = re.findall(r'"([^"]+)"', requirement)
        if not quoted:
            print(f"⚠️ No quoted string found in requirement: {requirement}")
            return "[FAIL] Requirement must include quoted text to evaluate."
        targets = quoted

        matches = []
        for target in targets:
            for line in lines:
                ratio = SequenceMatcher(None, target.lower(), line.lower()).ratio()
                print(f"🔍 Comparing '{target}' to line '{line}' → similarity: {ratio:.2f}")
                if ratio >= 0.85:
                    matches.append(target)
                    break

        if matches:
            return f"[PASS] Found structured text via fuzzy match: {', '.join(matches)}"
        else:
            return f"[FAIL] Did not find: {', '.join(targets)}"

    except Exception as e:
        return f"[FAIL] Textract structured data error: {e}"
