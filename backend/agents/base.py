"""
Base agent class — handles the OpenAI function-calling agentic loop.

Sub-agents extend this and provide:
  - SYSTEM_PROMPT
  - TOOLS  (list of OpenAI function tool schemas)
  - _dispatch_tool(tool_name, tool_input, context) → str  (async)
"""
from __future__ import annotations
import asyncio
import json
from typing import Any

from openai import APIConnectionError, APIError, APITimeoutError, AsyncOpenAI, RateLimitError

from config import settings
from models.report import AgentStep, ToolCall
from observability import SpanCtx


def _get_client() -> AsyncOpenAI:
    """Create a fresh AsyncOpenAI client per call to avoid event-loop binding issues."""
    return AsyncOpenAI(
        api_key=settings.openai_api_key,
        timeout=settings.openai_timeout_seconds,
        max_retries=0,
    )


class BaseAgent:
    SYSTEM_PROMPT: str = ""
    TOOLS: list[dict] = []
    NAME: str = "base_agent"

    async def run(
        self,
        user_prompt: str,
        context: dict[str, Any],
        tracer_span: SpanCtx | None = None,
    ) -> AgentStep:
        """
        Execute the tool-calling loop until the model issues a final text response.
        Returns an AgentStep with all tool calls, citations, and confidence.
        """
        messages: list[dict] = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        tool_calls_log: list[ToolCall] = []
        citations: list[str] = []
        total_input_tokens = 0
        total_output_tokens = 0

        kwargs: dict[str, Any] = dict(
            model=settings.openai_agent_model,
            max_tokens=4096,
            messages=messages,
        )
        if self.TOOLS:
            kwargs["tools"] = self.TOOLS

        client = _get_client()
        try:
            for _ in range(settings.max_agent_iterations):
                if total_input_tokens + total_output_tokens >= settings.agent_max_total_tokens:
                    return self._build_step(
                        tool_calls_log=tool_calls_log,
                        citations=citations,
                        total_input_tokens=total_input_tokens,
                        total_output_tokens=total_output_tokens,
                        final_text="Analysis incomplete — token budget exhausted.",
                        confidence=0.2,
                        tracer_span=tracer_span,
                    )

                kwargs["messages"] = messages
                try:
                    async with asyncio.timeout(settings.openai_timeout_seconds):
                        response = await client.chat.completions.create(**kwargs)
                except TimeoutError as exc:
                    return self._error_step(
                        tool_calls_log=tool_calls_log,
                        citations=citations,
                        total_input_tokens=total_input_tokens,
                        total_output_tokens=total_output_tokens,
                        error_text="Agent LLM call timed out.",
                        tracer_span=tracer_span,
                        exc=exc,
                    )
                except (APIConnectionError, APITimeoutError, APIError, RateLimitError) as exc:
                    return self._error_step(
                        tool_calls_log=tool_calls_log,
                        citations=citations,
                        total_input_tokens=total_input_tokens,
                        total_output_tokens=total_output_tokens,
                        error_text=f"Agent LLM call failed: {self._format_exception(exc)}",
                        tracer_span=tracer_span,
                        exc=exc,
                    )

                usage = response.usage
                total_input_tokens += getattr(usage, "prompt_tokens", 0) or 0
                total_output_tokens += getattr(usage, "completion_tokens", 0) or 0

                message = response.choices[0].message
                finish_reason = response.choices[0].finish_reason

                # Append assistant turn to history
                assistant_msg: dict[str, Any] = {
                    "role": "assistant",
                    "content": message.content,
                }
                if message.tool_calls:
                    assistant_msg["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in message.tool_calls
                    ]
                messages.append(assistant_msg)

                if finish_reason != "tool_calls" or not message.tool_calls:
                    # Model is done — final text response
                    final_text = message.content or ""
                    confidence = self._estimate_confidence(final_text)
                    citations.extend(self._extract_citations(final_text, tool_calls_log))
                    return self._build_step(
                        tool_calls_log=tool_calls_log,
                        citations=citations,
                        total_input_tokens=total_input_tokens,
                        total_output_tokens=total_output_tokens,
                        final_text=final_text,
                        confidence=confidence,
                        tracer_span=tracer_span,
                    )

                # Execute each tool call and collect results
                for tc in message.tool_calls:
                    tool_name = tc.function.name
                    tool_input: dict[str, Any]
                    try:
                        parsed_input = json.loads(tc.function.arguments or "{}")
                        if not isinstance(parsed_input, dict):
                            raise ValueError("Tool input must be a JSON object.")
                        tool_input = parsed_input
                    except (json.JSONDecodeError, ValueError) as exc:
                        tool_output = f"Tool input parsing failed for {tool_name}: {self._format_exception(exc)}"
                        tool_calls_log.append(
                            ToolCall(
                                tool_name=tool_name,
                                input={},
                                output=tool_output[:2000],
                                error=tool_output[:2000],
                            )
                        )
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": tool_output,
                        })
                        continue

                    try:
                        tool_output = await self._dispatch_tool(tool_name, tool_input, context)
                        tool_error = None
                    except Exception as exc:
                        tool_output = f"Tool {tool_name} failed: {self._format_exception(exc)}"
                        tool_error = tool_output

                    tool_calls_log.append(
                        ToolCall(
                            tool_name=tool_name,
                            input=tool_input,
                            output=tool_output[:2000],
                            error=tool_error[:2000] if tool_error else None,
                        )
                    )
                    citations.extend(self._extract_urls_from_output(tool_output))
                    if tracer_span:
                        tracer_span.log_tool_call(tool_name, tool_input, tool_output)

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": tool_output,
                    })
        except Exception as exc:
            return self._error_step(
                tool_calls_log=tool_calls_log,
                citations=citations,
                total_input_tokens=total_input_tokens,
                total_output_tokens=total_output_tokens,
                error_text=f"Agent run failed: {self._format_exception(exc)}",
                tracer_span=tracer_span,
                exc=exc,
            )

        return self._build_step(
            tool_calls_log=tool_calls_log,
            citations=citations,
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            final_text="Analysis incomplete — max iterations reached.",
            confidence=0.2,
            tracer_span=tracer_span,
        )

    async def _dispatch_tool(self, tool_name: str, tool_input: dict, context: dict) -> str:
        raise NotImplementedError

    def _estimate_confidence(self, text: str) -> float:
        """Heuristic confidence score based on hedging language."""
        hedges = ["unclear", "uncertain", "not sure", "limited data", "could not find",
                  "no information", "unavailable", "unknown"]
        hedge_count = sum(1 for h in hedges if h.lower() in text.lower())
        return max(0.1, 1.0 - hedge_count * 0.15)

    def _build_step(
        self,
        tool_calls_log: list[ToolCall],
        citations: list[str],
        total_input_tokens: int,
        total_output_tokens: int,
        final_text: str,
        confidence: float,
        tracer_span: SpanCtx | None,
    ) -> AgentStep:
        step = AgentStep(
            agent_name=self.NAME,
            tool_calls=tool_calls_log,
            reasoning=final_text[:500],
            output=final_text,
            confidence=max(0.0, min(confidence, 1.0)),
            citations=list(set(citations)),
            tokens_used=total_input_tokens + total_output_tokens,
        )
        if tracer_span:
            tracer_span.log_tokens(total_input_tokens, total_output_tokens)
        return step

    def _error_step(
        self,
        tool_calls_log: list[ToolCall],
        citations: list[str],
        total_input_tokens: int,
        total_output_tokens: int,
        error_text: str,
        tracer_span: SpanCtx | None,
        exc: Exception,
    ) -> AgentStep:
        error_output = f"{error_text} Analysis may be incomplete."
        if tracer_span:
            tracer_span.log_tool_call("agent_error", {"agent": self.NAME}, self._format_exception(exc))
        return self._build_step(
            tool_calls_log=tool_calls_log,
            citations=citations,
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            final_text=error_output,
            confidence=0.1,
            tracer_span=tracer_span,
        )

    def _extract_citations(self, text: str, tool_calls: list[ToolCall]) -> list[str]:
        urls = []
        for tc in tool_calls:
            urls.extend(self._extract_urls_from_output(tc.output))
        return urls

    def _extract_urls_from_output(self, text: str) -> list[str]:
        import re
        return re.findall(r"https?://[^\s\"'<>]+", text)

    def _format_exception(self, exc: Exception) -> str:
        return str(exc).strip() or exc.__class__.__name__
