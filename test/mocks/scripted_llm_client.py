"""Deterministic LLM test double that returns pre-programmed tool calls."""

from __future__ import annotations

from typing import Any

from domain.models import LLMToolResponse, ToolCall, ToolDefinition


class ScriptedLLMClient:
    """Returns tool calls from a pre-defined script, one per invocation.

    When the script is exhausted the client returns a ``done(failed)``
    call so the agent loop terminates cleanly.
    """

    def __init__(self, steps: list[ToolCall]) -> None:
        self._steps = list(steps)
        self._index = 0
        self.call_count = 0

    async def complete(self, prompt: str, **kwargs: Any) -> str:
        return ""

    async def complete_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[ToolDefinition],
        **kwargs: Any,
    ) -> LLMToolResponse:
        self.call_count += 1
        if self._index >= len(self._steps):
            return LLMToolResponse(
                tool_calls=[ToolCall(
                    name="done",
                    arguments={"status": "failed", "reason": "Script exhausted"},
                )],
            )
        tc = self._steps[self._index]
        self._index += 1
        return LLMToolResponse(tool_calls=[tc])
