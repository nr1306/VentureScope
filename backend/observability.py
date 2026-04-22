"""
Langfuse observability wrapper — v4 compatible.
Every agent step, tool call, and token count flows through here.
Falls back to no-ops when Langfuse is not configured.
"""
from __future__ import annotations
from typing import Any

from config import settings

_client = None
_PLACEHOLDER_PREFIXES = ("your_", "sk-your", "")


def _looks_like_placeholder(value: str) -> bool:
    return not value or value.startswith("your_") or value.startswith("sk-your")


def get_langfuse():
    """Return a Langfuse client if credentials are properly configured, else None."""
    global _client
    if _client is not None:
        return _client
    if (
        not _looks_like_placeholder(settings.langfuse_public_key)
        and not _looks_like_placeholder(settings.langfuse_secret_key)
    ):
        try:
            from langfuse import Langfuse
            _client = Langfuse(
                public_key=settings.langfuse_public_key,
                secret_key=settings.langfuse_secret_key,
                host=settings.langfuse_host,
            )
        except Exception:
            pass
    return _client


class Tracer:
    """
    Thin wrapper around a Langfuse trace for one due-diligence run.

    Usage:
        tracer = Tracer(company_name="Stripe")
        with tracer.span("market_agent") as span:
            span.log_tool_call("web_search", input={...}, output="...")
            span.log_tokens(input=500, output=300)
        tracer.finish(metadata={"recommendation": "invest"})
    """

    def __init__(self, company_name: str, report_id: str):
        self.company_name = company_name
        self.report_id = report_id
        self.trace_id: str | None = None
        self._obs = None
        lf = get_langfuse()
        if lf:
            try:
                self._obs = lf.start_observation(
                    type="trace",
                    name=f"due_diligence_{company_name}",
                    metadata={"report_id": report_id, "company": company_name},
                )
                self.trace_id = getattr(self._obs, "trace_id", None) or getattr(self._obs, "id", None)
            except Exception:
                self._obs = None

    def span(self, name: str) -> "SpanCtx":
        return SpanCtx(name=name, parent=self._obs)

    def finish(self, metadata: dict[str, Any] | None = None) -> None:
        if self._obs:
            try:
                if metadata:
                    self._obs.update(metadata=metadata)
                self._obs.end()
            except Exception:
                pass
        lf = get_langfuse()
        if lf:
            try:
                lf.flush()
            except Exception:
                pass


class SpanCtx:
    def __init__(self, name: str, parent: Any):
        self._name = name
        self._parent = parent
        self._span = None

    def __enter__(self) -> "SpanCtx":
        if self._parent:
            try:
                self._span = self._parent.start_observation(type="span", name=self._name)
            except Exception:
                self._span = None
        return self

    def __exit__(self, *_) -> None:
        if self._span:
            try:
                self._span.end()
            except Exception:
                pass

    def log_tool_call(self, tool: str, input: dict, output: str) -> None:
        if self._span:
            try:
                self._span.start_observation(
                    type="event",
                    name=f"tool:{tool}",
                    metadata={"input": input, "output": output[:500]},
                ).end()
            except Exception:
                pass

    def log_tokens(self, input: int, output: int) -> None:
        if self._span:
            try:
                self._span.update(usage={"input": input, "output": output, "total": input + output})
            except Exception:
                pass

    def log_guardrail(self, name: str, triggered: bool, reason: str = "") -> None:
        if self._span:
            try:
                self._span.start_observation(
                    type="event",
                    name=f"guardrail:{name}",
                    metadata={"triggered": triggered, "reason": reason},
                ).end()
            except Exception:
                pass
