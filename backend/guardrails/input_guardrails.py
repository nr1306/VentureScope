"""
Input guardrails — run before any agent call.

1. Prompt injection detector
2. Company name sanitizer
3. Upload size / type validator
"""
from __future__ import annotations
import re

from fastapi import HTTPException

from config import settings

# Patterns that suggest prompt injection attempts
_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"disregard\s+(all\s+)?(previous|prior)\s+(instructions|directives|prompts)",
    r"you\s+are\s+now\s+(a\s+)?",
    r"new\s+instructions?:",
    r"system\s*prompt\s*:",
    r"<\s*system\s*>",
    r"\[INST\]",
    r"act\s+as\s+(if\s+you\s+are|a\s+)",
    r"forget\s+(everything|all)",
    r"print\s+(your\s+)?(system\s+)?prompt",
    r"reveal\s+(your\s+)?(instructions|system\s+prompt)",
]

_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)

_ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/markdown",
    "application/octet-stream",  # fallback for some clients
}


def validate_company_input(company_name: str) -> None:
    """
    Validate a company name field for prompt injection and format issues.
    Raises HTTPException(400) on violation.
    """
    if not company_name or not company_name.strip():
        raise HTTPException(status_code=400, detail="Company name cannot be empty.")

    if len(company_name) > 200:
        raise HTTPException(status_code=400, detail="Company name too long (max 200 chars).")

    if _INJECTION_RE.search(company_name):
        raise HTTPException(
            status_code=400,
            detail="Invalid company name: contains disallowed content.",
        )

    # Must look vaguely like a company name — letters, numbers, spaces, common punctuation
    if not re.match(r"^[a-zA-Z0-9\s\.,\-&'\"()/]+$", company_name):
        raise HTTPException(
            status_code=400,
            detail="Company name contains invalid characters.",
        )


def validate_upload(filename: str, content_type: str, size_bytes: int) -> None:
    """
    Validate an uploaded document.
    Raises HTTPException(400) on violation.
    """
    if size_bytes > settings.max_upload_bytes:
        mb = settings.max_upload_bytes // (1024 * 1024)
        raise HTTPException(status_code=400, detail=f"File too large. Maximum size is {mb}MB.")

    # Normalize content type (strip parameters like '; charset=utf-8')
    base_type = content_type.split(";")[0].strip().lower()
    if base_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{base_type}'. Allowed: PDF, DOCX, TXT, Markdown.",
        )

    # Block obviously dangerous filenames
    if filename and re.search(r"\.(exe|sh|bat|js|py|php|rb)$", filename, re.IGNORECASE):
        raise HTTPException(status_code=400, detail="Executable file types are not allowed.")
