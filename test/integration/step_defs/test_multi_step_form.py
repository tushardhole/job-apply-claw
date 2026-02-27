"""Step definitions for multi-step form BDD scenarios.

Tests that the LLM agent correctly distinguishes intermediate
navigation buttons (Next, Continue, Save & Continue) from the
final Submit Application button.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

import pytest
from pytest_bdd import given, when, then, scenarios, parsers

from domain.models import AgentTask, ToolCall, UserProfile
from infra.agent import BrowserAgent
from test.mocks import FakeBrowserTools, InMemoryLogger, ScriptedLLMClient

scenarios("../features/multi_step_form.feature")


@dataclass
class MultiStepCtx:
    profile: UserProfile | None = None
    llm_steps: list[ToolCall] = field(default_factory=list)
    task: AgentTask | None = None
    result: object = None
    tools: FakeBrowserTools | None = None


@pytest.fixture()
def msctx() -> MultiStepCtx:
    return MultiStepCtx()


# -- Given ------------------------------------------------------------------


@given(
    parsers.parse('a profile for multi-step with name "{name}" and email "{email}"'),
    target_fixture="msctx",
)
def given_profile(name: str, email: str) -> MultiStepCtx:
    ctx = MultiStepCtx()
    ctx.profile = UserProfile(full_name=name, email=email)
    return ctx


@given("the LLM agent will navigate a 3-step form")
def given_3step_form(msctx: MultiStepCtx) -> None:
    msctx.llm_steps = [
        ToolCall(name="goto", arguments={"url": "https://example.test/apply"}),
        # Step 1: Personal info
        ToolCall(name="fill", arguments={"field": "full_name", "value": "Jane"}),
        ToolCall(name="fill", arguments={"field": "email", "value": "jane@test.com"}),
        ToolCall(name="click", arguments={"target": "Next"}),
        # Step 2: Experience
        ToolCall(name="upload_file", arguments={"field": "resume", "file_type": "resume"}),
        ToolCall(name="click", arguments={"target": "Next"}),
        # Step 3: Review & Submit
        ToolCall(name="page_snapshot", arguments={}),
        ToolCall(name="click", arguments={"target": "Submit Application"}),
        ToolCall(name="done", arguments={"status": "success", "reason": "Application submitted"}),
    ]


@given("the LLM agent will navigate a 3-step form in debug mode")
def given_3step_debug(msctx: MultiStepCtx) -> None:
    msctx.llm_steps = [
        ToolCall(name="goto", arguments={"url": "https://example.test/apply"}),
        ToolCall(name="fill", arguments={"field": "full_name", "value": "Jane"}),
        ToolCall(name="click", arguments={"target": "Next"}),
        ToolCall(name="upload_file", arguments={"field": "resume", "file_type": "resume"}),
        ToolCall(name="click", arguments={"target": "Next"}),
        ToolCall(name="page_snapshot", arguments={}),
        ToolCall(name="done", arguments={"status": "skipped", "reason": "Debug mode: final submit skipped"}),
    ]
    msctx.task = AgentTask(objective="Apply", debug=True)


@given("the LLM agent will use Save and Continue buttons")
def given_save_continue(msctx: MultiStepCtx) -> None:
    msctx.llm_steps = [
        ToolCall(name="goto", arguments={"url": "https://example.test/apply"}),
        ToolCall(name="fill", arguments={"field": "full_name", "value": "Jane"}),
        ToolCall(name="click", arguments={"target": "Save & Continue"}),
        ToolCall(name="fill", arguments={"field": "experience", "value": "5 years"}),
        ToolCall(name="click", arguments={"target": "Save & Continue"}),
        ToolCall(name="click", arguments={"target": "Submit Application"}),
        ToolCall(name="done", arguments={"status": "success"}),
    ]


@given("the LLM agent encounters a review page before submit")
def given_review_page(msctx: MultiStepCtx) -> None:
    msctx.llm_steps = [
        ToolCall(name="goto", arguments={"url": "https://example.test/apply"}),
        ToolCall(name="fill", arguments={"field": "full_name", "value": "Jane"}),
        ToolCall(name="click", arguments={"target": "Next"}),
        ToolCall(name="page_snapshot", arguments={}),
        ToolCall(name="click", arguments={"target": "Submit Application"}),
        ToolCall(name="done", arguments={"status": "success"}),
    ]


# -- When -------------------------------------------------------------------


@when("the multi-step agent runs")
def when_run(msctx: MultiStepCtx) -> None:
    llm = ScriptedLLMClient(msctx.llm_steps)
    tools = FakeBrowserTools()
    msctx.tools = tools
    agent = BrowserAgent(llm=llm, browser_tools=tools, logger=InMemoryLogger())
    task = msctx.task or AgentTask(objective="Apply to job")
    msctx.result = asyncio.run(agent.execute_task(task))


# -- Then -------------------------------------------------------------------


@then(parsers.parse('the multi-step result is "{status}"'))
def then_result(msctx: MultiStepCtx, status: str) -> None:
    assert msctx.result is not None
    assert msctx.result.status == status


@then(parsers.parse('the agent clicked "{target}" {count:d} times'))
def then_clicked_count(msctx: MultiStepCtx, target: str, count: int) -> None:
    assert msctx.tools is not None
    targets = msctx.tools.clicked_targets()
    actual = targets.count(target)
    assert actual == count, f"Expected {count} clicks on '{target}', got {actual} in {targets}"


@then(parsers.parse('the agent did not click "{target}"'))
def then_not_clicked(msctx: MultiStepCtx, target: str) -> None:
    assert msctx.tools is not None
    targets = msctx.tools.clicked_targets()
    assert target not in targets, f"Did not expect click on '{target}', but found in {targets}"
