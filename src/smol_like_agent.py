# smol_like_agent.py

import asyncio
import re
from playwright.async_api import async_playwright

class SmolLikeAgent:
    def __init__(self, tools=None):
        self.tools = tools if tools else []
        self.logs = []

    def register_tool(self, tool_func):
        self.tools.append(tool_func)

    def log(self, message):
        self.logs.append(message)
        print(message)

    def summarize_result(self, requirement, success):
        status = "[PASS]" if success else "[FAIL]"
        return f"{status} {requirement}\n" + "\n".join(self.logs)
    
# Run the agent with a requirement and URL
    async def run(self, requirement: str, url: str):
        self.logs.clear()
        self.log(f"🧠 Starting SmolLikeAgent on: '{requirement}'")

        for tool in self.tools:
            try:
                self.log(f"🔧 Trying tool: {tool.__name__}")
                result = await tool(self, requirement, url)
                if isinstance(result, str):
                    self.log(result)
                    if result.strip().startswith("[PASS]"):
                        return self.summarize_result(requirement, success=True)
            except Exception as e:
                self.log(f"❌ Tool {tool.__name__} failed with error: {e}")

        return self.summarize_result(requirement, success=False)
