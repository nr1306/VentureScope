from __future__ import annotations
from typing import Any

from agents.base import BaseAgent
from tools.web_search import WEB_SEARCH_TOOL, run_web_search
from tools.document_retriever import DOCUMENT_RETRIEVER_TOOL, run_document_retriever


class MarketAgent(BaseAgent):
    NAME = "market_agent"
    SYSTEM_PROMPT = """You are a senior market research analyst specializing in investment due diligence.

Your task is to research and analyze the market opportunity for a company.

Focus on:
- Total Addressable Market (TAM), Serviceable Addressable Market (SAM), Serviceable Obtainable Market (SOM)
- Market growth rate and key trends
- Industry tailwinds and headwinds
- Customer segments and demand drivers
- Regulatory environment affecting the market

CRITICAL RULES:
1. Every market size figure (dollar amounts, percentages, multiples) MUST be followed immediately by a citation URL in brackets, e.g. "$50B TAM [https://...]"
2. If you cannot find a reliable source for a figure, state "unverified estimate" — do NOT present it as fact
3. Use web_search for current data and document_retriever for company-specific uploaded materials
4. Structure your final response as clear prose with a summary paragraph followed by bullet-point findings"""

    TOOLS = [WEB_SEARCH_TOOL, DOCUMENT_RETRIEVER_TOOL]

    async def _dispatch_tool(self, tool_name: str, tool_input: dict, context: dict) -> str:
        if tool_name == "web_search":
            results = await run_web_search(tool_input["query"], tool_input.get("max_results", 5))
            return "\n\n".join(
                f"[{r['title']}]({r['url']})\n{r['content']}" for r in results
            )
        if tool_name == "document_retriever":
            return await run_document_retriever(
                context.get("rag_retrieve"),
                query=tool_input["query"],
                top_k=tool_input.get("top_k", 5),
            )
        return f"Unknown tool: {tool_name}"
