"""
Output guardrails — run on each sub-agent output before it enters the report.

1. Citation enforcer — flags uncited numeric claims
2. Hallucination flag — low confidence marks section needs_review
3. Tone normalizer — strips overconfident speculation
"""
from __future__ import annotations
import re

# Numeric patterns that should have a citation
_NUMERIC_CLAIM_RE = re.compile(
    r"(\$[\d,]+(?:\.\d+)?(?:\s*(?:billion|million|trillion|B|M|T))?|\d+(?:\.\d+)?%|\d+x)",
    re.IGNORECASE,
)

# URL pattern — a citation present nearby
_URL_RE = re.compile(r"https?://[^\s\"'<>]+")

# Overconfident speculative language to soften
_SPECULATION_PATTERNS = [
    (r"\bwill definitely\b", "is likely to"),
    (r"\bguaranteed to\b", "may"),
    (r"\bcertainly will\b", "is expected to"),
    (r"\bwithout a doubt\b", "likely"),
    (r"\b100%\s+certain\b", "highly confident"),
    (r"\bnever fail\b", "rarely fail"),
]


def _check_citations(text: str) -> list[str]:
    """
    Find numeric claims that are NOT followed by a URL within 200 characters.
    Returns a list of violation descriptions.
    """
    violations = []
    for match in _NUMERIC_CLAIM_RE.finditer(text):
        start = match.start()
        end = match.end()
        window = text[end: end + 250]  # look ahead 250 chars for a URL
        if not _URL_RE.search(window):
            violations.append(f"Uncited numeric claim: '{match.group()}'")
    return violations


def _normalize_tone(text: str) -> str:
    """Replace overconfident language with appropriately hedged alternatives."""
    for pattern, replacement in _SPECULATION_PATTERNS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def apply_output_guardrails(text: str, section: str) -> tuple[str, list[str]]:
    """
    Apply all output guardrails to agent text.

    Returns:
        (processed_text, list_of_triggered_guardrail_names)
    """
    triggered: list[str] = []

    # 1. Tone normalization
    normalized = _normalize_tone(text)
    if normalized != text:
        triggered.append("tone_normalizer")
    text = normalized

    # 2. Citation check — we annotate but do NOT block (agent did its best)
    violations = _check_citations(text)
    if violations:
        triggered.append("citation_enforcer")
        # Append a visible warning at the end of the section
        warning = (
            "\n\n⚠️ **Guardrail Warning — Citation Enforcer**: "
            f"{len(violations)} numeric claim(s) may lack source citations. "
            "Review before relying on these figures:\n"
            + "\n".join(f"  - {v}" for v in violations[:5])
        )
        text = text + warning

    return text, triggered


def flag_low_confidence(confidence: float, threshold: float) -> bool:
    """Returns True if the section should be flagged for human review."""
    return confidence < threshold
