from __future__ import annotations
from typing import Any

from agents.base import BaseAgent
from tools.web_search import WEB_SEARCH_TOOL, run_web_search


class CompetitorAgent(BaseAgent):
    NAME = "competitor_agent"
    SYSTEM_PROMPT = """You are a competitive intelligence analyst specializing in technology markets.

Your task is to map the competitive landscape for a company.

Focus on:
- Identify 3-5 direct competitors (same customer, same problem)
- Identify 2-3 indirect/substitute competitors
- Compare product positioning, pricing, and go-to-market strategy
- Assess the company's competitive moat (network effects, switching costs, IP, brand, scale)
- Note any recent competitive moves (acquisitions, product launches, funding)

CRITICAL RULES:
1. Only name competitors that you found via web search — do NOT invent competitor names
2. For each competitor, include the source URL where you confirmed their existence
3. Clearly distinguish between direct competitors (same ICP) and indirect substitutes
4. Rate the moat as: None / Weak / Moderate / Strong — with a one-sentence justification
5. Always do at least 2 web searches to validate your competitor list before finalizing"""

    TOOLS = [WEB_SEARCH_TOOL]

    async def _dispatch_tool(self, tool_name: str, tool_input: dict, context: dict) -> str:
        if tool_name == "web_search":
            results = run_web_search(tool_input["query"], tool_input.get("max_results", 5))
            return "\n\n".join(
                f"[{r['title']}]({r['url']})\n{r['content']}" for r in results
            )
        return f"Unknown tool: {tool_name}"
