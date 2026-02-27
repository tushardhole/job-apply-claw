"""OpenAI-compatible LLM client with tool/function calling support.

Uses ``urllib.request`` for HTTP calls (no external HTTP library needed),
matching the pattern used elsewhere in the codebase.
"""

from __future__ import annotations

import asyncio
import json
import urllib.request
from typing import Any

from domain.models import LLMToolResponse, ToolCall, ToolDefinition


class OpenAIToolCallingClient:
    """Implements ``LLMClientPort`` using the OpenAI chat/completions API."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o",
        timeout: int = 120,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout

    async def complete(
        self,
        prompt: str,
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if temperature is not None:
            payload["temperature"] = temperature

        data = await asyncio.to_thread(self._post_chat_completions, payload)
        return data["choices"][0]["message"].get("content", "")

    async def complete_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[ToolDefinition],
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> LLMToolResponse:
        openai_tools = [self._to_openai_tool(t) for t in tools]

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "tools": openai_tools,
            "tool_choice": "auto",
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if temperature is not None:
            payload["temperature"] = temperature

        data = await asyncio.to_thread(self._post_chat_completions, payload)
        return self._parse_response(data)

    # -- internal helpers ---------------------------------------------------

    def _post_chat_completions(self, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base_url}/chat/completions"
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Authorization", f"Bearer {self._api_key}")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    @staticmethod
    def _to_openai_tool(td: ToolDefinition) -> dict[str, Any]:
        properties: dict[str, Any] = {}
        required: list[str] = []
        for name, schema in td.parameters.items():
            properties[name] = {k: v for k, v in schema.items() if k != "default"}
            if "default" not in schema:
                required.append(name)

        return {
            "type": "function",
            "function": {
                "name": td.name,
                "description": td.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }

    @staticmethod
    def _parse_response(data: dict[str, Any]) -> LLMToolResponse:
        choice = data["choices"][0]
        message = choice["message"]
        finish = choice.get("finish_reason")

        raw_tool_calls = message.get("tool_calls")
        if not raw_tool_calls:
            return LLMToolResponse(
                text=message.get("content"),
                finish_reason=finish,
            )

        tool_calls: list[ToolCall] = []
        for tc in raw_tool_calls:
            fn = tc["function"]
            args = json.loads(fn["arguments"]) if isinstance(fn["arguments"], str) else fn["arguments"]
            tool_calls.append(ToolCall(name=fn["name"], arguments=args))

        return LLMToolResponse(
            tool_calls=tool_calls,
            text=message.get("content"),
            finish_reason=finish,
        )
