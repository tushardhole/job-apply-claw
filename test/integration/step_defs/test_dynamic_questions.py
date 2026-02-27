"""Step definitions for dynamic questions BDD scenarios.

Tests that the LLM agent asks the user for dynamic fields (salary,
work auth, essays) via ask_user and fills static fields directly.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

import pytest
from pytest_bdd import given, when, then, scenarios, parsers

from domain.models import AgentTask, ToolCall, UserProfile
from infra.agent import BrowserAgent
from test.mocks import FakeBrowserTools, InMemoryLogger, ScriptedLLMClient

scenarios("../features/dynamic_questions.feature")


@dataclass
class DynCtx:
    profile: UserProfile | None = None
    llm_steps: list[ToolCall] = field(default_factory=list)
    user_responses: list[str] = field(default_factory=list)
    result: object = None
    tools: FakeBrowserTools | None = None


@pytest.fixture()
def dctx() -> DynCtx:
    return DynCtx()


# -- Given ------------------------------------------------------------------


@given(
    parsers.parse('a profile with name "{name}" and email "{email}"'),
    target_fixture="dctx",
)
def given_profile(name: str, email: str) -> DynCtx:
    ctx = DynCtx()
    ctx.profile = UserProfile(full_name=name, email=email)
    return ctx


@given("the LLM agent encounters a work authorization question")
def given_work_auth(dctx: DynCtx) -> None:
    dctx.llm_steps = [
        ToolCall(name="goto", arguments={"url": "https://example.test/jobs/1"}),
        ToolCall(name="fill", arguments={"field": "full_name", "value": "Jane"}),
        ToolCall(name="fill", arguments={"field": "email", "value": "jane@test.com"}),
        ToolCall(name="ask_user", arguments={"question": "Are you authorized to work in the US?"}),
        ToolCall(name="fill", arguments={"field": "work_auth", "value": "Yes, US Citizen"}),
        ToolCall(name="done", arguments={"status": "success"}),
    ]
    dctx.user_responses = ["Yes, US Citizen"]


@given("the LLM agent encounters a salary expectation question")
def given_salary(dctx: DynCtx) -> None:
    dctx.llm_steps = [
        ToolCall(name="goto", arguments={"url": "https://example.test/jobs/1"}),
        ToolCall(name="ask_user", arguments={"question": "What is your expected salary for this role?"}),
        ToolCall(name="fill", arguments={"field": "salary", "value": "120000"}),
        ToolCall(name="done", arguments={"status": "success"}),
    ]
    dctx.user_responses = ["120000"]


@given("the LLM agent encounters an essay question")
def given_essay(dctx: DynCtx) -> None:
    dctx.llm_steps = [
        ToolCall(name="goto", arguments={"url": "https://example.test/jobs/1"}),
        ToolCall(name="ask_user", arguments={"question": "Why do you want to work at Acme Corp?"}),
        ToolCall(name="fill", arguments={"field": "essay_why", "value": "I admire the engineering culture"}),
        ToolCall(name="done", arguments={"status": "success"}),
    ]
    dctx.user_responses = ["I admire the engineering culture"]


@given("the LLM agent encounters a notice period question")
def given_notice(dctx: DynCtx) -> None:
    dctx.llm_steps = [
        ToolCall(name="goto", arguments={"url": "https://example.test/jobs/1"}),
        ToolCall(name="ask_user", arguments={"question": "What is your notice period?"}),
        ToolCall(name="fill", arguments={"field": "notice_period", "value": "2 weeks"}),
        ToolCall(name="done", arguments={"status": "success"}),
    ]
    dctx.user_responses = ["2 weeks"]


@given("the LLM agent fills only static fields")
def given_static_only(dctx: DynCtx) -> None:
    dctx.llm_steps = [
        ToolCall(name="goto", arguments={"url": "https://example.test/jobs/1"}),
        ToolCall(name="fill", arguments={"field": "full_name", "value": "Jane"}),
        ToolCall(name="fill", arguments={"field": "email", "value": "jane@test.com"}),
        ToolCall(name="upload_file", arguments={"field": "resume", "file_type": "resume"}),
        ToolCall(name="done", arguments={"status": "success"}),
    ]


# -- When -------------------------------------------------------------------


@when("the agent runs the task")
def when_run(dctx: DynCtx) -> None:
    llm = ScriptedLLMClient(dctx.llm_steps)
    tools = FakeBrowserTools(user_responses=dctx.user_responses)
    dctx.tools = tools
    agent = BrowserAgent(llm=llm, browser_tools=tools, logger=InMemoryLogger())
    dctx.result = asyncio.run(agent.execute_task(AgentTask(objective="Apply")))


# -- Then -------------------------------------------------------------------


@then(parsers.parse('the agent outcome is "{status}"'))
def then_outcome(dctx: DynCtx, status: str) -> None:
    assert dctx.result is not None
    assert dctx.result.status == status


@then(parsers.parse('the agent asked "{question}"'))
def then_asked(dctx: DynCtx, question: str) -> None:
    assert dctx.tools is not None
    questions = dctx.tools.ask_user_questions()
    assert any(question in q for q in questions), f"Expected '{question}' in {questions}"


@then(parsers.parse('the agent filled "{field}" with "{value}"'))
def then_filled(dctx: DynCtx, field: str, value: str) -> None:
    assert dctx.tools is not None
    filled = dctx.tools.filled_fields()
    assert filled.get(field) == value, f"Expected {field}={value}, got {filled}"


@then("the agent did not ask the user anything")
def then_no_ask(dctx: DynCtx) -> None:
    assert dctx.tools is not None
    assert len(dctx.tools.ask_user_questions()) == 0
