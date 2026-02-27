"""Unit tests for OpenAIToolCallingClient.

HTTP calls are mocked via unittest.mock.patch to avoid real API calls.
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock, patch

from domain.models import ToolDefinition
from infra.llm.openai_tool_calling_client import OpenAIToolCallingClient


def _mock_response(body: dict) -> MagicMock:
    resp = MagicMock()
    resp.read.return_value = json.dumps(body).encode("utf-8")
    resp.__enter__ = MagicMock(return_value=resp)
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def _make_client() -> OpenAIToolCallingClient:
    return OpenAIToolCallingClient(
        api_key="sk-test-key",
        base_url="https://api.openai.com/v1",
        model="gpt-4o-test",
    )


SAMPLE_TOOLS = [
    ToolDefinition(
        name="click",
        description="Click something",
        parameters={"target": {"type": "string"}},
    ),
    ToolDefinition(
        name="done",
        description="Signal done",
        parameters={
            "status": {"type": "string"},
            "reason": {"type": "string", "default": ""},
        },
    ),
]


class TestComplete:
    @patch("urllib.request.urlopen")
    def test_returns_text_content(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.return_value = _mock_response({
            "choices": [{"message": {"content": "Hello world"}, "finish_reason": "stop"}],
        })
        client = _make_client()
        result = asyncio.run(client.complete("Hi"))
        assert result == "Hello world"

    @patch("urllib.request.urlopen")
    def test_passes_max_tokens_and_temperature(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.return_value = _mock_response({
            "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
        })
        client = _make_client()
        asyncio.run(client.complete("Hi", max_tokens=100, temperature=0.5))

        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        body = json.loads(req.data.decode())
        assert body["max_tokens"] == 100
        assert body["temperature"] == 0.5


class TestCompleteWithTools:
    @patch("urllib.request.urlopen")
    def test_returns_tool_calls(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.return_value = _mock_response({
            "choices": [{
                "message": {
                    "content": None,
                    "tool_calls": [{
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "click",
                            "arguments": '{"target": "Apply"}',
                        },
                    }],
                },
                "finish_reason": "tool_calls",
            }],
        })
        client = _make_client()
        resp = asyncio.run(client.complete_with_tools(
            messages=[{"role": "user", "content": "test"}],
            tools=SAMPLE_TOOLS,
        ))
        assert resp.tool_calls is not None
        assert len(resp.tool_calls) == 1
        assert resp.tool_calls[0].name == "click"
        assert resp.tool_calls[0].arguments == {"target": "Apply"}
        assert resp.finish_reason == "tool_calls"

    @patch("urllib.request.urlopen")
    def test_returns_text_when_no_tool_calls(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.return_value = _mock_response({
            "choices": [{
                "message": {"content": "I need more info"},
                "finish_reason": "stop",
            }],
        })
        client = _make_client()
        resp = asyncio.run(client.complete_with_tools(
            messages=[{"role": "user", "content": "test"}],
            tools=SAMPLE_TOOLS,
        ))
        assert resp.tool_calls is None
        assert resp.text == "I need more info"

    @patch("urllib.request.urlopen")
    def test_multiple_tool_calls(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.return_value = _mock_response({
            "choices": [{
                "message": {
                    "content": None,
                    "tool_calls": [
                        {"id": "c1", "type": "function", "function": {"name": "click", "arguments": '{"target":"A"}'}},
                        {"id": "c2", "type": "function", "function": {"name": "done", "arguments": '{"status":"success","reason":"ok"}'}},
                    ],
                },
                "finish_reason": "tool_calls",
            }],
        })
        client = _make_client()
        resp = asyncio.run(client.complete_with_tools(messages=[], tools=SAMPLE_TOOLS))
        assert resp.tool_calls is not None
        assert len(resp.tool_calls) == 2


class TestToolSchemaConversion:
    def test_to_openai_tool_required_params(self) -> None:
        td = ToolDefinition(
            name="fill",
            description="Fill a field",
            parameters={
                "field": {"type": "string"},
                "value": {"type": "string"},
            },
        )
        schema = OpenAIToolCallingClient._to_openai_tool(td)
        fn = schema["function"]
        assert fn["name"] == "fill"
        assert set(fn["parameters"]["required"]) == {"field", "value"}

    def test_to_openai_tool_optional_params(self) -> None:
        td = ToolDefinition(
            name="wait",
            description="Wait",
            parameters={"seconds": {"type": "integer", "default": 2}},
        )
        schema = OpenAIToolCallingClient._to_openai_tool(td)
        fn = schema["function"]
        assert fn["parameters"]["required"] == []
        assert "default" not in fn["parameters"]["properties"]["seconds"]

    @patch("urllib.request.urlopen")
    def test_sends_correct_tool_schema(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.return_value = _mock_response({
            "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
        })
        client = _make_client()
        asyncio.run(client.complete_with_tools(
            messages=[{"role": "user", "content": "x"}],
            tools=SAMPLE_TOOLS,
        ))
        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        body = json.loads(req.data.decode())
        assert body["tool_choice"] == "auto"
        assert len(body["tools"]) == 2
        assert body["tools"][0]["function"]["name"] == "click"
