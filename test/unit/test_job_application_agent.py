"""Unit tests for the refactored JobApplicationAgent.

The agent now delegates to BrowserAgentPort (LLM browser agent).
Tests use ScriptedLLMClient + FakeBrowserTools via a thin FakeAgent.
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
    UserProfile,
)
from domain.services import DebugRunManager, JobApplicationAgent
from test.mocks import (
    FakeUserInteraction,
    FixedClock,
    InMemoryCredentialRepository,
    InMemoryDebugArtifactStore,
    InMemoryJobApplicationRepository,
    InMemoryLogger,
    SequentialIdGenerator,
)


class _FakeAgent:
    """Inline BrowserAgentPort that returns a pre-configured result."""

    def __init__(self, result: AgentResult) -> None:
        self._result = result
        self.executed_task: AgentTask | None = None

    async def execute_task(self, task: AgentTask) -> AgentResult:
        self.executed_task = task
        return self._result


class _FailingAgent:
    """Agent that raises an exception."""

    async def execute_task(self, task: AgentTask) -> AgentResult:
        raise RuntimeError("Browser crashed")


def _build(
    debug_store: InMemoryDebugArtifactStore | None = None,
) -> tuple[JobApplicationAgent, InMemoryJobApplicationRepository, InMemoryCredentialRepository]:
    job_repo = InMemoryJobApplicationRepository()
    cred_repo = InMemoryCredentialRepository()
    debug_manager = DebugRunManager(debug_store) if debug_store else None
    orchestrator = JobApplicationAgent(
        job_repo=job_repo,
        credential_repo=cred_repo,
        clock=FixedClock(datetime(2025, 1, 1, tzinfo=timezone.utc)),
        id_generator=SequentialIdGenerator(),
        logger=InMemoryLogger(),
        debug_manager=debug_manager,
    )
    return orchestrator, job_repo, cred_repo


def _defaults() -> tuple[JobPostingRef, UserProfile, ResumeData]:
    return (
        JobPostingRef(
            company_name="Acme",
            job_title="Backend Engineer",
            job_url="https://example.test/jobs/1",
            job_board_type="greenhouse",
        ),
        UserProfile(full_name="Ada Lovelace", email="ada@example.com", phone="123"),
        ResumeData(primary_resume_path="/tmp/resume.pdf"),
    )


def test_success_flow() -> None:
    orchestrator, repo, _ = _build()
    job, profile, resume = _defaults()
    fake_agent = _FakeAgent(AgentResult(status="success"))
    ui = FakeUserInteraction()

    async def run() -> None:
        record = await orchestrator.apply_to_job(
            agent=fake_agent,
            ui=ui,
            job=job,
            profile=profile,
            resume_data=resume,
            run_context=RunContext(run_id="r1"),
        )
        assert record.status is JobApplicationStatus.APPLIED
        assert record.applied_at is not None

    asyncio.run(run())
    assert repo.list_all()[0].status is JobApplicationStatus.APPLIED
    assert any("submitted" in m.lower() for m in ui.info_messages)


def test_skipped_flow_debug_mode() -> None:
    debug_store = InMemoryDebugArtifactStore()
    orchestrator, repo, _ = _build(debug_store=debug_store)
    job, profile, resume = _defaults()
    fake_agent = _FakeAgent(AgentResult(
        status="skipped",
        reason="Debug mode: final submit skipped",
    ))
    ui = FakeUserInteraction()

    async def run() -> None:
        record = await orchestrator.apply_to_job(
            agent=fake_agent,
            ui=ui,
            job=job,
            profile=profile,
            resume_data=resume,
            run_context=RunContext(run_id="r2", is_debug=True),
        )
        assert record.status is JobApplicationStatus.SKIPPED

    asyncio.run(run())
    assert repo.list_all()[0].status is JobApplicationStatus.SKIPPED
    assert any("skipped" in m.lower() for m in ui.info_messages)
    assert len(debug_store.metadata) == 1
    assert debug_store.metadata[0][1]["outcome"] == "skipped"


def test_failed_flow() -> None:
    orchestrator, repo, _ = _build()
    job, profile, resume = _defaults()
    fake_agent = _FakeAgent(AgentResult(status="failed", reason="Image captcha"))
    ui = FakeUserInteraction()

    async def run() -> None:
        record = await orchestrator.apply_to_job(
            agent=fake_agent,
            ui=ui,
            job=job,
            profile=profile,
            resume_data=resume,
            run_context=RunContext(run_id="r3"),
        )
        assert record.status is JobApplicationStatus.FAILED
        assert record.failure_reason == "Image captcha"

    asyncio.run(run())


def test_agent_exception_records_failure() -> None:
    orchestrator, repo, _ = _build()
    job, profile, resume = _defaults()
    ui = FakeUserInteraction()

    async def run() -> None:
        record = await orchestrator.apply_to_job(
            agent=_FailingAgent(),
            ui=ui,
            job=job,
            profile=profile,
            resume_data=resume,
            run_context=RunContext(run_id="r4"),
        )
        assert record.status is JobApplicationStatus.FAILED
        assert "Browser crashed" in (record.failure_reason or "")

    asyncio.run(run())


def test_task_context_includes_profile_and_job() -> None:
    orchestrator, _, _ = _build()
    job, profile, resume = _defaults()
    fake_agent = _FakeAgent(AgentResult(status="success"))

    async def run() -> None:
        await orchestrator.apply_to_job(
            agent=fake_agent,
            ui=FakeUserInteraction(),
            job=job,
            profile=profile,
            resume_data=resume,
            run_context=RunContext(run_id="r5"),
        )

    asyncio.run(run())
    task = fake_agent.executed_task
    assert task is not None
    assert task.context["profile"]["full_name"] == "Ada Lovelace"
    assert task.context["job_url"] == "https://example.test/jobs/1"
    assert task.context["company"] == "Acme"
    assert task.context["resume_available"] is True
