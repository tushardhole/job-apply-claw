"""Advanced flow tests for JobApplicationAgent using the LLM browser agent.

These test agent-reported outcomes (captcha failure, OTP flow, etc.)
mapped through the orchestrator.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from domain.models import (
    AgentResult,
    AgentStep,
    AgentTask,
    JobApplicationStatus,
    JobPostingRef,
    ResumeData,
    RunContext,
    ToolCall,
    UserProfile,
)
from domain.services import JobApplicationAgent
from test.mocks import (
    FakeUserInteraction,
    FixedClock,
    InMemoryCredentialRepository,
    InMemoryJobApplicationRepository,
    InMemoryLogger,
    SequentialIdGenerator,
)


class _FakeAgent:
    def __init__(self, result: AgentResult) -> None:
        self._result = result

    async def execute_task(self, task: AgentTask) -> AgentResult:
        return self._result


def _build() -> tuple[JobApplicationAgent, InMemoryJobApplicationRepository]:
    repo = InMemoryJobApplicationRepository()
    return (
        JobApplicationAgent(
            job_repo=repo,
            credential_repo=InMemoryCredentialRepository(),
            clock=FixedClock(datetime(2025, 1, 1, tzinfo=timezone.utc)),
            id_generator=SequentialIdGenerator(),
            logger=InMemoryLogger(),
        ),
        repo,
    )


def _defaults() -> tuple[JobPostingRef, UserProfile, ResumeData]:
    return (
        JobPostingRef(company_name="Acme", job_title="Platform Engineer",
                      job_url="https://example.test/jobs/2", job_board_type="workday"),
        UserProfile(full_name="Ada Lovelace", email="ada@example.com"),
        ResumeData(primary_resume_path="/tmp/resume.pdf"),
    )


def test_text_captcha_solved_by_agent() -> None:
    """Agent handles text captcha (ask_user + fill) and reports success."""
    orchestrator, repo = _build()
    job, profile, resume = _defaults()
    steps = [
        AgentStep(step_number=0, tool_name="ask_user", tool_args={"question": "Solve captcha"}, tool_result="7A3P"),
        AgentStep(step_number=1, tool_name="fill", tool_args={"field": "captcha", "value": "7A3P"}, tool_result="Filled captcha"),
    ]
    fake_agent = _FakeAgent(AgentResult(status="success", steps_taken=steps))

    async def run() -> None:
        record = await orchestrator.apply_to_job(
            agent=fake_agent, ui=FakeUserInteraction(),
            job=job, profile=profile, resume_data=resume,
            run_context=RunContext(run_id="r-captcha"),
        )
        assert record.status is JobApplicationStatus.APPLIED

    asyncio.run(run())


def test_image_captcha_reported_as_failure() -> None:
    """Agent detects image captcha and reports failure."""
    orchestrator, _ = _build()
    job, profile, resume = _defaults()
    fake_agent = _FakeAgent(AgentResult(
        status="failed",
        reason="Image-based captcha prevents automation",
    ))

    async def run() -> None:
        record = await orchestrator.apply_to_job(
            agent=fake_agent, ui=FakeUserInteraction(),
            job=job, profile=profile, resume_data=resume,
            run_context=RunContext(run_id="r-image-captcha"),
        )
        assert record.status is JobApplicationStatus.FAILED
        assert "captcha" in (record.failure_reason or "").lower()

    asyncio.run(run())


def test_otp_and_account_reset_handled_by_agent() -> None:
    """Agent handles OTP + password reset as part of its tool calls and reports success."""
    orchestrator, _ = _build()
    job, profile, resume = _defaults()
    steps = [
        AgentStep(step_number=0, tool_name="fill", tool_args={"field": "email", "value": "ada@example.com"}, tool_result="ok"),
        AgentStep(step_number=1, tool_name="click", tool_args={"target": "Create Account"}, tool_result="ok"),
        AgentStep(step_number=2, tool_name="click", tool_args={"target": "Forgot Password"}, tool_result="ok"),
        AgentStep(step_number=3, tool_name="ask_user", tool_args={"question": "Reset code"}, tool_result="RESET-TOKEN"),
        AgentStep(step_number=4, tool_name="fill", tool_args={"field": "reset_code", "value": "RESET-TOKEN"}, tool_result="ok"),
        AgentStep(step_number=5, tool_name="ask_user", tool_args={"question": "Enter OTP"}, tool_result="123456"),
        AgentStep(step_number=6, tool_name="fill", tool_args={"field": "otp", "value": "123456"}, tool_result="ok"),
    ]
    fake_agent = _FakeAgent(AgentResult(status="success", steps_taken=steps))

    async def run() -> None:
        record = await orchestrator.apply_to_job(
            agent=fake_agent, ui=FakeUserInteraction(),
            job=job, profile=profile, resume_data=resume,
            run_context=RunContext(run_id="r-otp"),
        )
        assert record.status is JobApplicationStatus.APPLIED

    asyncio.run(run())
    click_targets = [s.tool_args.get("target") for s in steps if s.tool_name == "click"]
    assert "Forgot Password" in click_targets
