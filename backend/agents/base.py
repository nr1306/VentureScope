"""
Base agent class — handles the OpenAI function-calling agentic loop.

Sub-agents extend this and provide:
  - SYSTEM_PROMPT
  - TOOLS  (list of OpenAI function tool schemas)
  - _dispatch_tool(tool_name, tool_input, context) → str  (async)
"""
from __future__ import annotations
import json
from typing import Any

from openai import AsyncOpenAI

from config import settings
from models.report import AgentStep, ToolCall
from observability import SpanCtx


def _get_client() -> AsyncOpenAI:
    """Create a fresh AsyncOpenAI client per call to avoid event-loop binding issues."""
    return AsyncOpenAI(api_key=settings.openai_api_key)


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
        for _ in range(settings.max_agent_iterations):
            kwargs["messages"] = messages
            response = await client.chat.completions.create(**kwargs)

            total_input_tokens += response.usage.prompt_tokens
            total_output_tokens += response.usage.completion_tokens

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

                step = AgentStep(
                    agent_name=self.NAME,
                    tool_calls=tool_calls_log,
                    reasoning=final_text[:500],
                    output=final_text,
                    confidence=confidence,
                    citations=list(set(citations)),
                    tokens_used=total_input_tokens + total_output_tokens,
                )
                if tracer_span:
                    tracer_span.log_tokens(total_input_tokens, total_output_tokens)
                return step

            # Execute each tool call and collect results
            for tc in message.tool_calls:
                tool_name = tc.function.name
                tool_input = json.loads(tc.function.arguments)
                tool_output = await self._dispatch_tool(tool_name, tool_input, context)

                tool_calls_log.append(
                    ToolCall(tool_name=tool_name, input=tool_input, output=tool_output[:2000])
                )
                citations.extend(self._extract_urls_from_output(tool_output))
                if tracer_span:
                    tracer_span.log_tool_call(tool_name, tool_input, tool_output)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": tool_output,
                })

        # Max iterations reached — return what we have
        return AgentStep(
            agent_name=self.NAME,
            tool_calls=tool_calls_log,
            reasoning="Max iterations reached",
            output="Analysis incomplete — max iterations reached.",
            confidence=0.2,
            citations=list(set(citations)),
            tokens_used=total_input_tokens + total_output_tokens,
        )

    async def _dispatch_tool(self, tool_name: str, tool_input: dict, context: dict) -> str:
        raise NotImplementedError

    def _estimate_confidence(self, text: str) -> float:
        """Heuristic confidence score based on hedging language."""
        hedges = ["unclear", "uncertain", "not sure", "limited data", "could not find",
                  "no information", "unavailable", "unknown"]
        hedge_count = sum(1 for h in hedges if h.lower() in text.lower())
        return max(0.1, 1.0 - hedge_count * 0.15)

    def _extract_citations(self, text: str, tool_calls: list[ToolCall]) -> list[str]:
        urls = []
        for tc in tool_calls:
            urls.extend(self._extract_urls_from_output(tc.output))
        return urls

    def _extract_urls_from_output(self, text: str) -> list[str]:
        import re
        return re.findall(r"https?://[^\s\"'<>]+", text)
