"""Unit tests for the BrowserAgent loop.

Uses inline scripted fakes for the LLM and browser tools.
"""

from __future__ import annotations

import asyncio
from typing import Any

from domain.models import (
    AgentTask,
    LLMToolResponse,
    ToolCall,
    ToolDefinition,
)
from infra.agent.browser_agent import BrowserAgent
from test.mocks.fake_runtime import InMemoryLogger as FakeLogger


# ---------- Inline fakes -------------------------------------------------

class _ScriptedLLM:
    """Returns pre-programmed tool calls one at a time."""

    def __init__(self, steps: list[ToolCall]) -> None:
        self._steps = list(steps)
        self._index = 0

    async def complete(self, prompt: str, **kw: Any) -> str:
        return ""

    async def complete_with_tools(
        self, messages: list[dict[str, Any]], tools: list[ToolDefinition], **kw: Any,
    ) -> LLMToolResponse:
        if self._index >= len(self._steps):
            return LLMToolResponse(
                tool_calls=[ToolCall(name="done", arguments={"status": "failed", "reason": "Script exhausted"})],
            )
        tc = self._steps[self._index]
        self._index += 1
        return LLMToolResponse(tool_calls=[tc])


class _FakeTools:
    """Records tool executions and returns canned results."""

    def __init__(self) -> None:
        self.executed: list[ToolCall] = []

    def available_tools(self) -> list[ToolDefinition]:
        return [ToolDefinition(name="goto", description="Go", parameters={})]

    async def execute(self, tool_call: ToolCall) -> str:
        self.executed.append(tool_call)
        return f"ok:{tool_call.name}"


# ---------- Helpers -------------------------------------------------------

def _run(coro: Any) -> Any:
    return asyncio.run(coro)


def _make_agent(
    steps: list[ToolCall],
    tools: _FakeTools | None = None,
) -> tuple[BrowserAgent, _FakeTools]:
    fake_tools = tools or _FakeTools()
    agent = BrowserAgent(
        llm=_ScriptedLLM(steps),
        browser_tools=fake_tools,
        logger=FakeLogger(),
    )
    return agent, fake_tools


# ---------- Tests ---------------------------------------------------------

def test_agent_returns_done_result() -> None:
    agent, tools = _make_agent([
        ToolCall(name="goto", arguments={"url": "https://x.com"}),
        ToolCall(name="done", arguments={"status": "success", "reason": "Applied"}),
    ])
    result = _run(agent.execute_task(AgentTask(objective="Apply")))
    assert result.status == "success"
    assert result.reason == "Applied"
    assert len(tools.executed) == 1
    assert tools.executed[0].name == "goto"


def test_agent_records_steps() -> None:
    agent, _ = _make_agent([
        ToolCall(name="goto", arguments={"url": "https://x.com"}),
        ToolCall(name="goto", arguments={"url": "https://y.com"}),
        ToolCall(name="done", arguments={"status": "success"}),
    ])
    result = _run(agent.execute_task(AgentTask(objective="Test")))
    assert len(result.steps_taken) == 2
    assert result.steps_taken[0].tool_name == "goto"
    assert result.steps_taken[0].tool_result == "ok:goto"


def test_agent_exceeds_max_steps() -> None:
    many_steps = [ToolCall(name="goto", arguments={"url": "x"})] * 10
    agent, tools = _make_agent(many_steps)
    result = _run(agent.execute_task(AgentTask(objective="Loop", max_steps=3)))
    assert result.status == "failed"
    assert "maximum steps" in result.reason.lower()


def test_agent_handles_text_only_response() -> None:
    class _TextThenDoneLLM:
        def __init__(self) -> None:
            self._call = 0

        async def complete(self, prompt: str, **kw: Any) -> str:
            return ""

        async def complete_with_tools(self, messages: Any, tools: Any, **kw: Any) -> LLMToolResponse:
            self._call += 1
            if self._call == 1:
                return LLMToolResponse(text="Thinking...")
            return LLMToolResponse(
                tool_calls=[ToolCall(name="done", arguments={"status": "success"})],
            )

    agent = BrowserAgent(
        llm=_TextThenDoneLLM(),
        browser_tools=_FakeTools(),
        logger=FakeLogger(),
    )
    result = _run(agent.execute_task(AgentTask(objective="Test")))
    assert result.status == "success"


def test_agent_skipped_status() -> None:
    agent, _ = _make_agent([
        ToolCall(name="done", arguments={"status": "skipped", "reason": "Debug mode: final submit skipped"}),
    ])
    result = _run(agent.execute_task(AgentTask(objective="Debug", debug=True)))
    assert result.status == "skipped"
    assert "Debug mode" in (result.reason or "")


def test_agent_failed_status() -> None:
    agent, _ = _make_agent([
        ToolCall(name="done", arguments={"status": "failed", "reason": "Image captcha"}),
    ])
    result = _run(agent.execute_task(AgentTask(objective="Captcha")))
    assert result.status == "failed"
    assert result.reason == "Image captcha"


def test_agent_uses_task_context_for_prompt() -> None:
    agent, _ = _make_agent([
        ToolCall(name="done", arguments={"status": "success"}),
    ])
    task = AgentTask(
        objective="Apply",
        context={
            "profile": {"full_name": "Jane", "email": "jane@test.com"},
            "job_url": "https://example.com/jobs/1",
            "company": "Example",
            "job_title": "SWE",
            "resume_available": True,
            "cover_letter_available": False,
        },
        debug=False,
    )
    result = _run(agent.execute_task(task))
    assert result.status == "success"


def test_agent_script_exhaustion_returns_failed() -> None:
    agent, _ = _make_agent([])
    result = _run(agent.execute_task(AgentTask(objective="Empty")))
    assert result.status == "failed"
    assert "Script exhausted" in (result.reason or "")
