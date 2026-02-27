"""Shared fixtures and context for BDD step definitions."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import pytest

from domain.models import (
    AgentResult,
    AgentStep,
    AgentTask,
    JobApplicationRecord,
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


class FakeAgentForBDD:
    """Configurable fake BrowserAgentPort for BDD scenarios."""

    def __init__(
        self,
        result_status: str = "success",
        result_reason: str | None = None,
        steps: list[AgentStep] | None = None,
        data: dict[str, Any] | None = None,
    ) -> None:
        self.result_status = result_status
        self.result_reason = result_reason
        self.steps = steps or []
        self.data = data or {}
        self.executed_task: AgentTask | None = None

    async def execute_task(self, task: AgentTask) -> AgentResult:
        self.executed_task = task
        return AgentResult(
            status=self.result_status,
            reason=self.result_reason,
            steps_taken=self.steps,
            data=self.data,
        )


@dataclass
class ApplyContext:
    """Holds mutable state shared across BDD steps."""

    profile: UserProfile = None  # type: ignore[assignment]
    agent: FakeAgentForBDD = field(default_factory=FakeAgentForBDD)
    ui: FakeUserInteraction = field(default_factory=FakeUserInteraction)
    job_repo: InMemoryJobApplicationRepository = field(
        default_factory=InMemoryJobApplicationRepository,
    )
    credential_repo: InMemoryCredentialRepository = field(
        default_factory=InMemoryCredentialRepository,
    )
    debug_store: InMemoryDebugArtifactStore = field(
        default_factory=InMemoryDebugArtifactStore,
    )
    job: JobPostingRef | None = None
    debug_mode: bool = False
    record: JobApplicationRecord | None = None


@pytest.fixture()
def ctx() -> ApplyContext:
    return ApplyContext()


def run_apply(ctx: ApplyContext) -> None:
    """Execute the job application agent synchronously for tests."""
    clock = FixedClock(datetime(2025, 6, 1, tzinfo=timezone.utc))
    ids = SequentialIdGenerator()
    logger = InMemoryLogger()

    debug_manager: DebugRunManager | None = None
    if ctx.debug_mode:
        debug_manager = DebugRunManager(ctx.debug_store)

    orchestrator = JobApplicationAgent(
        job_repo=ctx.job_repo,
        credential_repo=ctx.credential_repo,
        clock=clock,
        id_generator=ids,
        logger=logger,
        debug_manager=debug_manager,
    )

    run_context = RunContext(
        run_id=ids.new_run_id(),
        is_debug=ctx.debug_mode,
    )

    async def _apply() -> JobApplicationRecord:
        return await orchestrator.apply_to_job(
            agent=ctx.agent,
            ui=ctx.ui,
            job=ctx.job,  # type: ignore[arg-type]
            profile=ctx.profile,
            resume_data=_default_resume_data(),
            run_context=run_context,
        )

    ctx.record = asyncio.run(_apply())


def _default_resume_data() -> ResumeData:
    return ResumeData(
        primary_resume_path="/fake/resume.pdf",
        cover_letter_paths=("/fake/cover_letter.pdf",),
    )
