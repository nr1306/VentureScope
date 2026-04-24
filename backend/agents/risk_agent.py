from __future__ import annotations
from typing import Any

from agents.base import BaseAgent
from tools.web_search import WEB_SEARCH_TOOL, run_web_search
from tools.document_retriever import DOCUMENT_RETRIEVER_TOOL, run_document_retriever


class RiskAgent(BaseAgent):
    NAME = "risk_agent"
    SYSTEM_PROMPT = """You are a risk analyst specializing in venture and growth-stage investment risk assessment.

Your task is to identify and score risks for a company.

Assess each risk category (score 1-10, where 10 = highest risk):
- Regulatory risk: licensing requirements, compliance burden, government intervention risk
- Market risk: market timing, adoption curve, macro sensitivity
- Execution risk: team depth, key-person dependency, operational complexity
- Competitive risk: threat of new entrants, incumbent response, commoditization risk
- Financial risk: dilution, burn trajectory, fundraising risk

CRITICAL RULES:
1. For each risk, provide: (a) risk score 1-10, (b) a one-sentence justification, (c) a source URL if you found evidence
2. Flag any regulatory or legal issues with HIGH PRIORITY
3. If a company operates in a regulated industry (fintech, healthcare, crypto), dig deeper into compliance
4. Use document_retriever to check for any risk-related disclosures in uploaded materials
5. End your response with an OVERALL RISK LEVEL: Low | Medium | High — with a 2-sentence summary"""

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
