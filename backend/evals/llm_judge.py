"""
LLM-as-judge — uses a separate Claude call to score each report section.

Rubric (1-5 per dimension):
  - accuracy: Are facts correct and well-sourced?
  - completeness: Are all expected topics covered?
  - reasoning: Is the analysis coherent and insightful?
  - citation_quality: Are claims properly cited?
"""
from __future__ import annotations
import asyncio
import json

from openai import APIConnectionError, APIError, APITimeoutError, AsyncOpenAI, RateLimitError
from config import settings
from models.report import DueDiligenceReport


def _get_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=settings.openai_api_key,
        timeout=settings.openai_timeout_seconds,
        max_retries=0,
    )

JUDGE_SYSTEM_PROMPT = """You are an expert investment analyst evaluating the quality of AI-generated due diligence reports.

Score the provided report section on a scale of 1-5 for each dimension:
- accuracy (1=many errors, 5=highly accurate and well-sourced)
- completeness (1=major gaps, 5=thorough coverage)
- reasoning (1=shallow, 5=deep insightful analysis)
- citation_quality (1=uncited claims, 5=every claim well-cited)

Also write a 1-2 sentence feedback string.

Respond ONLY with valid JSON:
{
  "accuracy": <1-5>,
  "completeness": <1-5>,
  "reasoning": <1-5>,
  "citation_quality": <1-5>,
  "feedback": "<string>"
}"""


async def judge_section(section_name: str, section_text: str, ground_truth_context: str) -> dict:
    """
    Score one report section using Claude-as-judge.
    Returns a dict with scores and feedback.
    """
    user_msg = f"""SECTION: {section_name.upper()}

GROUND TRUTH CONTEXT (for reference only):
{ground_truth_context}

REPORT SECTION TO EVALUATE:
{section_text[:3000]}"""

    try:
        async with asyncio.timeout(settings.openai_timeout_seconds):
            response = await _get_client().chat.completions.create(
                model=settings.openai_synthesis_model,
                max_tokens=512,
                messages=[
                    {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
            )
    except TimeoutError:
        return {
            "accuracy": 0.5, "completeness": 0.5, "reasoning": 0.5,
            "citation_quality": 0.5, "average": 0.5,
            "feedback": "Judge request timed out.",
        }
    except (APIConnectionError, APITimeoutError, APIError, RateLimitError) as exc:
        return {
            "accuracy": 0.5, "completeness": 0.5, "reasoning": 0.5,
            "citation_quality": 0.5, "average": 0.5,
            "feedback": f"Judge request failed: {str(exc)[:200]}",
        }

    raw = (response.choices[0].message.content or "").strip()
    try:
        result = json.loads(raw)
        # Normalize to 0.0-1.0
        for key in ["accuracy", "completeness", "reasoning", "citation_quality"]:
            if key in result:
                result[key] = round(result[key] / 5.0, 2)
        result["average"] = round(
            sum(result[k] for k in ["accuracy", "completeness", "reasoning", "citation_quality"]) / 4, 2
        )
        return result
    except (json.JSONDecodeError, KeyError):
        return {
            "accuracy": 0.5, "completeness": 0.5, "reasoning": 0.5,
            "citation_quality": 0.5, "average": 0.5,
            "feedback": "Judge parsing failed — raw output: " + raw[:200],
        }


async def judge_report(report: DueDiligenceReport, ground_truth: dict) -> dict[str, dict]:
    """Judge all sections of a report. Returns {section_name: scores_dict}."""
    results = {}
    gt_str = json.dumps(ground_truth, indent=2)

    for section in report.sections:
        scores = await judge_section(
            section_name=section.section,
            section_text=section.summary + "\n" + "\n".join(section.key_findings),
            ground_truth_context=gt_str,
        )
        results[section.section] = scores

        # Write judge score back to section
        section.llm_judge_score = scores.get("average")

    return results
