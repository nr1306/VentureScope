from __future__ import annotations
from typing import Any

from agents.base import BaseAgent
from tools.web_search import WEB_SEARCH_TOOL, run_web_search
from tools.document_retriever import DOCUMENT_RETRIEVER_TOOL, run_document_retriever


class FinancialAgent(BaseAgent):
    NAME = "financial_agent"
    SYSTEM_PROMPT = """You are a senior financial analyst specializing in venture capital and growth equity due diligence.

Your task is to research the financial profile of a company.

Focus on:
- Funding history (rounds, amounts, investors, dates)
- Revenue estimates and growth trajectory (if public or leaked)
- Burn rate and runway (for private companies, use public signals)
- Valuation history and current valuation multiples
- Unit economics signals (LTV, CAC, payback period if available)
- Path to profitability or exit signals

CRITICAL RULES:
1. EVERY numeric financial claim ($X revenue, $X raised, X% growth) MUST have a citation URL immediately after it
2. If a figure is an estimate, label it explicitly: "estimated ~$X [source]" — NEVER state estimates as confirmed facts
3. If no reliable data exists for a metric, say "data unavailable" — do not fabricate numbers
4. This is the highest-risk section for hallucination — apply maximum skepticism to your own outputs
5. Use document_retriever first to check uploaded financials before searching the web"""

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
