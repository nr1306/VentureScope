"""
Orchestrator agent — fans out to specialist sub-agents, synthesizes results
into a structured DueDiligenceReport, and produces the final recommendation.
"""
from __future__ import annotations
import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from config import settings
from models.report import (
    AgentStep, SectionReport, DueDiligenceReport, ToolCall
)
from agents.market_agent import MarketAgent
from agents.financial_agent import FinancialAgent
from agents.competitor_agent import CompetitorAgent
from agents.risk_agent import RiskAgent
from guardrails.output_guardrails import apply_output_guardrails
from observability import Tracer
from openai import APIConnectionError, APIError, APITimeoutError, AsyncOpenAI, RateLimitError


def _get_openai_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=settings.openai_api_key,
        timeout=settings.openai_timeout_seconds,
        max_retries=0,
    )

SYNTHESIZER_PROMPT = """You are a senior investment partner reviewing a due diligence package.

You have received analysis from four specialist agents:
1. Market Analysis
2. Financial Analysis
3. Competitive Analysis
4. Risk Analysis

Your task is to synthesize these into:
1. An overall investment recommendation: "invest" | "monitor" | "pass"
2. An overall confidence score: 0.0 (no confidence) to 1.0 (high confidence)
3. A brief 2-3 sentence synthesis rationale

Respond ONLY with valid JSON in this exact format:
{
  "recommendation": "invest" | "monitor" | "pass",
  "confidence": 0.0-1.0,
  "rationale": "..."
}"""


def _section_from_step(section_name: str, step: AgentStep) -> SectionReport:
    """Convert an AgentStep into a SectionReport with guardrails applied."""
    output, triggered = apply_output_guardrails(step.output, section_name)

    # Parse risk level from output
    risk_level = "medium"
    lower = output.lower()
    if "overall risk level: high" in lower or "high risk" in lower:
        risk_level = "high"
    elif "overall risk level: low" in lower or "low risk" in lower:
        risk_level = "low"

    # Extract key findings (bullet points or numbered list items)
    import re
    findings = re.findall(r"(?:^|\n)[•\-\*\d]+\.?\s+(.+)", output)
    key_findings = [f.strip() for f in findings[:8]] or [output[:300]]

    return SectionReport(
        section=section_name,
        summary=output[:1000],
        key_findings=key_findings,
        risk_level=risk_level,
        confidence=step.confidence,
        citations=step.citations,
        guardrails_triggered=triggered,
        agent_steps=[step],
        needs_review=step.confidence < settings.confidence_threshold,
    )


def _failed_agent_step(agent_name: str, error: str) -> AgentStep:
    return AgentStep(
        agent_name=agent_name,
        reasoning=error[:500],
        output=error,
        confidence=0.1,
        citations=[],
        tokens_used=0,
    )


async def _run_agent_step(
    agent: Any,
    user_prompt: str,
    context: dict[str, Any],
    tracer: Tracer,
    span_name: str,
) -> AgentStep:
    with tracer.span(span_name) as span:
        try:
            return await agent.run(
                user_prompt=user_prompt,
                context=context,
                tracer_span=span,
            )
        except Exception as exc:
            error = f"{agent.NAME} failed: {exc}"
            span.log_tool_call("agent_failure", {"agent": agent.NAME}, error)
            return _failed_agent_step(agent.NAME, error)


async def run_orchestrator(
    report_id: str,
    company_name: str,
    rag_retrieve: Callable,
) -> DueDiligenceReport:
    """
    Main entry point — runs all sub-agents and returns a complete report.
    This is called from the Celery worker.
    """
    tracer = Tracer(company_name=company_name, report_id=report_id)

    # Shared context passed to all sub-agents for tool dispatch
    agent_context = {"rag_retrieve": rag_retrieve}

    sections: list[SectionReport] = []
    orchestrator_steps: list[AgentStep] = []

    # ── Market Agent ─────────────────────────────────────────────────────────
    market_step = await _run_agent_step(
        agent=MarketAgent(),
        user_prompt=f"Research the market opportunity for {company_name}. Be thorough and cite all figures.",
        context=agent_context,
        tracer=tracer,
        span_name="market_agent",
    )
    sections.append(_section_from_step("market", market_step))
    orchestrator_steps.append(market_step)

    # ── Financial Agent ───────────────────────────────────────────────────────
    financial_step = await _run_agent_step(
        agent=FinancialAgent(),
        user_prompt=f"Research the financial profile of {company_name}. Include funding history, revenue signals, and valuation context.",
        context=agent_context,
        tracer=tracer,
        span_name="financial_agent",
    )
    sections.append(_section_from_step("financial", financial_step))
    orchestrator_steps.append(financial_step)

    # ── Competitor Agent ──────────────────────────────────────────────────────
    competitor_step = await _run_agent_step(
        agent=CompetitorAgent(),
        user_prompt=f"Map the competitive landscape for {company_name}. Identify direct and indirect competitors and assess the moat.",
        context=agent_context,
        tracer=tracer,
        span_name="competitor_agent",
    )
    sections.append(_section_from_step("competitor", competitor_step))
    orchestrator_steps.append(competitor_step)

    # ── Risk Agent ────────────────────────────────────────────────────────────
    risk_step = await _run_agent_step(
        agent=RiskAgent(),
        user_prompt=f"Assess all major risks for investing in or partnering with {company_name}.",
        context=agent_context,
        tracer=tracer,
        span_name="risk_agent",
    )
    sections.append(_section_from_step("risk", risk_step))
    orchestrator_steps.append(risk_step)

    # ── Synthesis ─────────────────────────────────────────────────────────────
    recommendation = "monitor"
    overall_confidence = round(
        sum(section.confidence for section in sections) / max(len(sections), 1),
        2,
    )
    with tracer.span("synthesizer") as span:
        synthesis_prompt = "\n\n".join([
            f"## {s.section.upper()} ANALYSIS\n{s.summary}" for s in sections
        ])
        try:
            async with asyncio.timeout(settings.openai_timeout_seconds):
                synthesis_response = await _get_openai_client().chat.completions.create(
                    model=settings.openai_synthesis_model,
                    max_tokens=512,
                    messages=[
                        {"role": "system", "content": SYNTHESIZER_PROMPT},
                        {"role": "user", "content": f"Company: {company_name}\n\n{synthesis_prompt}"},
                    ],
                )
            span.log_tokens(
                synthesis_response.usage.prompt_tokens,
                synthesis_response.usage.completion_tokens,
            )
            synthesis_text = (synthesis_response.choices[0].message.content or "").strip()
            synthesis = json.loads(synthesis_text)
            recommendation = synthesis.get("recommendation", "monitor")
            overall_confidence = float(synthesis.get("confidence", overall_confidence))
        except TimeoutError:
            span.log_tool_call("synthesizer_error", {"company_name": company_name}, "Synthesis timed out.")
        except (json.JSONDecodeError, ValueError):
            span.log_tool_call("synthesizer_error", {"company_name": company_name}, "Synthesis JSON parsing failed.")
        except (APIConnectionError, APITimeoutError, APIError, RateLimitError) as exc:
            span.log_tool_call("synthesizer_error", {"company_name": company_name}, str(exc))

    report = DueDiligenceReport(
        id=report_id,
        company_name=company_name,
        created_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        status="completed",
        sections=sections,
        overall_recommendation=recommendation,
        overall_confidence=overall_confidence,
        agent_trace=orchestrator_steps,
        langfuse_trace_id=tracer.trace_id,
    )

    tracer.finish(metadata={
        "recommendation": recommendation,
        "confidence": overall_confidence,
        "sections_completed": len(sections),
    })

    return report
