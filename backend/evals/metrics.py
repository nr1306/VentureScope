"""
Eval metrics — deterministic scoring against the golden dataset.
"""
from __future__ import annotations
import re
from models.report import DueDiligenceReport


def score_competitor_recall(report: DueDiligenceReport, ground_truth: dict) -> float:
    """Fraction of expected competitors found in the competitor section."""
    competitor_section = next((s for s in report.sections if s.section == "competitor"), None)
    if not competitor_section:
        return 0.0

    text = (competitor_section.summary + " ".join(competitor_section.key_findings)).lower()
    expected = ground_truth["competitors"]["must_include_any"]
    min_required = ground_truth["competitors"]["min_competitors_found"]

    found = sum(1 for c in expected if c.lower() in text)
    # Score based on meeting the minimum threshold
    return min(1.0, found / max(min_required, 1))


def score_citation_rate(report: DueDiligenceReport) -> float:
    """Fraction of numeric claims that are followed by a URL citation."""
    url_re = re.compile(r"https?://[^\s\"'<>]+")
    numeric_re = re.compile(r"(\$[\d,]+(?:\s*(?:billion|million|B|M))?|\d+(?:\.\d+)?%|\d+x)", re.IGNORECASE)

    total_claims = 0
    cited_claims = 0

    for section in report.sections:
        text = section.summary
        for match in numeric_re.finditer(text):
            total_claims += 1
            window = text[match.end(): match.end() + 250]
            if url_re.search(window):
                cited_claims += 1

    if total_claims == 0:
        return 1.0  # No numeric claims = no citation violations
    return cited_claims / total_claims


def score_risk_coverage(report: DueDiligenceReport, ground_truth: dict) -> float:
    """Fraction of expected risk topics covered."""
    risk_section = next((s for s in report.sections if s.section == "risk"), None)
    if not risk_section:
        return 0.0

    text = (risk_section.summary + " ".join(risk_section.key_findings)).lower()
    expected_topics = ground_truth["risks"]["expected_risk_topics"]
    min_required = ground_truth["risks"]["min_topics_covered"]

    covered = sum(1 for topic in expected_topics if topic.lower() in text)
    return min(1.0, covered / max(min_required, 1))


def score_hallucination_rate(report: DueDiligenceReport) -> float:
    """
    Estimate hallucination rate from guardrail triggers.
    Higher citation_enforcer triggers = higher potential hallucination.
    Returns a score where 1.0 = no hallucination signals, 0.0 = high signals.
    """
    total_trigger_count = sum(
        1 for s in report.sections if "citation_enforcer" in s.guardrails_triggered
    )
    # Penalize by 0.2 per section that triggered citation enforcer
    return max(0.0, 1.0 - total_trigger_count * 0.2)


def compute_all_metrics(report: DueDiligenceReport, ground_truth: dict) -> dict[str, float]:
    return {
        "competitor_recall": score_competitor_recall(report, ground_truth),
        "citation_rate": score_citation_rate(report),
        "risk_coverage": score_risk_coverage(report, ground_truth),
        "hallucination_proxy": score_hallucination_rate(report),
        "average_confidence": sum(s.confidence for s in report.sections) / max(len(report.sections), 1),
    }
