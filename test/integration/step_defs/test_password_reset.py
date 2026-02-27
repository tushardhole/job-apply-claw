"""Step definitions for password reset BDD scenarios.

Uses ScriptedLLMClient + FakeBrowserTools to test the BrowserAgent
loop with deterministic, pre-programmed tool call sequences.
"""
from __future__ import annotations

import asyncio

from pytest_bdd import given, when, then, scenarios, parsers

from domain.models import AgentTask, ToolCall, UserProfile
from infra.agent import BrowserAgent
from test.mocks import FakeBrowserTools, InMemoryLogger, ScriptedLLMClient

scenarios("../features/password_reset.feature")


# -- shared state -----------------------------------------------------------

class PasswordResetContext:
    def __init__(self) -> None:
        self.profile: UserProfile | None = None
        self.llm_steps: list[ToolCall] = []
        self.user_responses: list[str] = []
        self.page_snapshots: list[str] = []
        self.task: AgentTask | None = None
        self.result = None
        self.tools: FakeBrowserTools | None = None


_ctx_store: dict[str, PasswordResetContext] = {}


import pytest

@pytest.fixture()
def pw_ctx() -> PasswordResetContext:
    ctx = PasswordResetContext()
    _ctx_store["current"] = ctx
    return ctx


# -- Given steps ------------------------------------------------------------

@given(
    parsers.parse('a configured profile with name "{name}" and email "{email}"'),
    target_fixture="pw_ctx",
)
def given_profile(pw_ctx: PasswordResetContext, name: str, email: str) -> PasswordResetContext:
    pw_ctx = PasswordResetContext()
    pw_ctx.profile = UserProfile(full_name=name, email=email)
    _ctx_store["current"] = pw_ctx
    return pw_ctx


@given("the LLM agent will perform a code-based password reset")
def given_code_based_reset(pw_ctx: PasswordResetContext) -> None:
    pw_ctx.llm_steps = [
        ToolCall(name="goto", arguments={"url": "https://example.test/jobs/1"}),
        ToolCall(name="click", arguments={"target": "Login"}),
        ToolCall(name="click", arguments={"target": "Forgot Password"}),
        ToolCall(name="fill", arguments={"field": "email", "value": "jane@test.com"}),
        ToolCall(name="click", arguments={"target": "Send Reset Code"}),
        ToolCall(name="ask_user", arguments={"question": "Enter the reset code from your email"}),
        ToolCall(name="fill", arguments={"field": "reset_code", "value": "RESET-ABC"}),
        ToolCall(name="fill", arguments={"field": "new_password", "value": "NewPass123!"}),
        ToolCall(name="fill", arguments={"field": "confirm_password", "value": "NewPass123!"}),
        ToolCall(name="click", arguments={"target": "Reset Password"}),
        ToolCall(name="done", arguments={"status": "success", "reason": "Password reset and applied"}),
    ]
    pw_ctx.user_responses = ["RESET-ABC"]


@given("the LLM agent will perform a link-based password reset")
def given_link_based_reset(pw_ctx: PasswordResetContext) -> None:
    pw_ctx.llm_steps = [
        ToolCall(name="goto", arguments={"url": "https://example.test/jobs/1"}),
        ToolCall(name="click", arguments={"target": "Login"}),
        ToolCall(name="click", arguments={"target": "Forgot Password"}),
        ToolCall(name="fill", arguments={"field": "email", "value": "jane@test.com"}),
        ToolCall(name="click", arguments={"target": "Send Reset Link"}),
        ToolCall(name="ask_user", arguments={"question": "Paste the reset link from your email"}),
        ToolCall(name="goto", arguments={"url": "https://portal.test/reset?token=xyz"}),
        ToolCall(name="fill", arguments={"field": "new_password", "value": "NewPass123!"}),
        ToolCall(name="fill", arguments={"field": "confirm_password", "value": "NewPass123!"}),
        ToolCall(name="click", arguments={"target": "Set New Password"}),
        ToolCall(name="done", arguments={"status": "success", "reason": "Password reset via link and applied"}),
    ]
    pw_ctx.user_responses = ["https://portal.test/reset?token=xyz"]


@given("the LLM agent resets password and lands on login page")
def given_reset_lands_on_login(pw_ctx: PasswordResetContext) -> None:
    pw_ctx.llm_steps = [
        ToolCall(name="goto", arguments={"url": "https://example.test/jobs/1"}),
        ToolCall(name="click", arguments={"target": "Forgot Password"}),
        ToolCall(name="ask_user", arguments={"question": "Enter reset code"}),
        ToolCall(name="fill", arguments={"field": "reset_code", "value": "CODE123"}),
        ToolCall(name="fill", arguments={"field": "new_password", "value": "NewPass123!"}),
        ToolCall(name="click", arguments={"target": "Reset Password"}),
        ToolCall(name="page_snapshot", arguments={}),
        ToolCall(name="fill", arguments={"field": "email", "value": "jane@test.com"}),
        ToolCall(name="fill", arguments={"field": "password", "value": "NewPass123!"}),
        ToolCall(name="click", arguments={"target": "Log In"}),
        ToolCall(name="goto", arguments={"url": "https://example.test/jobs/1"}),
        ToolCall(name="done", arguments={"status": "success"}),
    ]
    pw_ctx.user_responses = ["CODE123"]
    pw_ctx.page_snapshots = [
        "Login page",
        "Login page with email and password fields",
    ]


@given("the LLM agent resets password and lands on dashboard")
def given_reset_lands_on_dashboard(pw_ctx: PasswordResetContext) -> None:
    pw_ctx.llm_steps = [
        ToolCall(name="goto", arguments={"url": "https://example.test/jobs/1"}),
        ToolCall(name="click", arguments={"target": "Forgot Password"}),
        ToolCall(name="ask_user", arguments={"question": "Enter reset code"}),
        ToolCall(name="fill", arguments={"field": "reset_code", "value": "CODE456"}),
        ToolCall(name="fill", arguments={"field": "new_password", "value": "NewPass123!"}),
        ToolCall(name="click", arguments={"target": "Reset Password"}),
        ToolCall(name="page_snapshot", arguments={}),
        ToolCall(name="goto", arguments={"url": "https://example.test/jobs/1"}),
        ToolCall(name="done", arguments={"status": "success"}),
    ]
    pw_ctx.user_responses = ["CODE456"]
    pw_ctx.page_snapshots = ["Dashboard - Welcome back!"]


@given("the LLM agent resets password without confirm field")
def given_reset_no_confirm(pw_ctx: PasswordResetContext) -> None:
    pw_ctx.llm_steps = [
        ToolCall(name="goto", arguments={"url": "https://example.test/jobs/1"}),
        ToolCall(name="click", arguments={"target": "Forgot Password"}),
        ToolCall(name="ask_user", arguments={"question": "Reset code"}),
        ToolCall(name="fill", arguments={"field": "reset_code", "value": "R1"}),
        ToolCall(name="fill", arguments={"field": "new_password", "value": "NewPass123!"}),
        ToolCall(name="click", arguments={"target": "Reset"}),
        ToolCall(name="done", arguments={"status": "success"}),
    ]
    pw_ctx.user_responses = ["R1"]


@given("the LLM agent retries after invalid reset code")
def given_retry_reset(pw_ctx: PasswordResetContext) -> None:
    pw_ctx.llm_steps = [
        ToolCall(name="goto", arguments={"url": "https://example.test/jobs/1"}),
        ToolCall(name="click", arguments={"target": "Forgot Password"}),
        ToolCall(name="ask_user", arguments={"question": "Enter reset code"}),
        ToolCall(name="fill", arguments={"field": "reset_code", "value": "WRONG"}),
        ToolCall(name="click", arguments={"target": "Submit"}),
        ToolCall(name="page_snapshot", arguments={}),
        ToolCall(name="ask_user", arguments={"question": "Invalid code. Please enter a new reset code"}),
        ToolCall(name="fill", arguments={"field": "reset_code", "value": "CORRECT"}),
        ToolCall(name="click", arguments={"target": "Submit"}),
        ToolCall(name="done", arguments={"status": "success"}),
    ]
    pw_ctx.user_responses = ["WRONG", "CORRECT"]
    pw_ctx.page_snapshots = ["Error: Invalid reset code. Please try again."]


@given("the LLM agent times out during password reset")
def given_timeout_reset(pw_ctx: PasswordResetContext) -> None:
    pw_ctx.llm_steps = [
        ToolCall(name="goto", arguments={"url": "https://example.test/jobs/1"}),
        ToolCall(name="click", arguments={"target": "Forgot Password"}),
        ToolCall(name="wait", arguments={"seconds": 2}),
    ]
    pw_ctx.task = AgentTask(objective="Apply", max_steps=3)


@given("the LLM agent resets password in debug mode")
def given_debug_reset(pw_ctx: PasswordResetContext) -> None:
    pw_ctx.llm_steps = [
        ToolCall(name="goto", arguments={"url": "https://example.test/jobs/1"}),
        ToolCall(name="click", arguments={"target": "Forgot Password"}),
        ToolCall(name="ask_user", arguments={"question": "Reset code"}),
        ToolCall(name="fill", arguments={"field": "reset_code", "value": "DBG1"}),
        ToolCall(name="fill", arguments={"field": "new_password", "value": "NewPass123!"}),
        ToolCall(name="click", arguments={"target": "Reset Password"}),
        ToolCall(name="done", arguments={"status": "skipped", "reason": "Debug mode: final submit skipped"}),
    ]
    pw_ctx.user_responses = ["DBG1"]
    pw_ctx.task = AgentTask(objective="Apply", debug=True)


# -- When steps -------------------------------------------------------------


@when("the agent executes the task")
def when_execute(pw_ctx: PasswordResetContext) -> None:
    llm = ScriptedLLMClient(pw_ctx.llm_steps)
    tools = FakeBrowserTools(
        user_responses=pw_ctx.user_responses,
        page_snapshots=pw_ctx.page_snapshots or None,
    )
    pw_ctx.tools = tools
    agent = BrowserAgent(llm=llm, browser_tools=tools, logger=InMemoryLogger())
    task = pw_ctx.task or AgentTask(objective="Apply to job")
    pw_ctx.result = asyncio.run(agent.execute_task(task))


# -- Then steps -------------------------------------------------------------


@then(parsers.parse('the agent result status is "{status}"'))
def then_status(pw_ctx: PasswordResetContext, status: str) -> None:
    assert pw_ctx.result is not None
    assert pw_ctx.result.status == status


@then(parsers.parse('the agent asked the user for "{question}"'))
def then_asked_user(pw_ctx: PasswordResetContext, question: str) -> None:
    assert pw_ctx.tools is not None
    questions = pw_ctx.tools.ask_user_questions()
    assert any(question in q for q in questions), f"Expected question containing '{question}' in {questions}"


@then(parsers.parse('the agent filled "{field}" with "{value}"'))
def then_filled(pw_ctx: PasswordResetContext, field: str, value: str) -> None:
    assert pw_ctx.tools is not None
    filled = pw_ctx.tools.filled_fields()
    assert filled.get(field) == value, f"Expected {field}={value}, got {filled}"


@then(parsers.parse('the agent visited "{url}"'))
def then_visited(pw_ctx: PasswordResetContext, url: str) -> None:
    assert pw_ctx.tools is not None
    urls = pw_ctx.tools.visited_urls()
    assert url in urls, f"Expected {url} in {urls}"


@then(parsers.parse('the agent asked the user {count:d} times'))
def then_asked_count(pw_ctx: PasswordResetContext, count: int) -> None:
    assert pw_ctx.tools is not None
    actual = len(pw_ctx.tools.ask_user_questions())
    assert actual == count, f"Expected {count} ask_user calls, got {actual}"


@then(parsers.parse('the agent failure reason contains "{text}"'))
def then_failure_reason(pw_ctx: PasswordResetContext, text: str) -> None:
    assert pw_ctx.result is not None
    reason = pw_ctx.result.reason or ""
    assert text in reason, f"Expected '{text}' in reason '{reason}'"
