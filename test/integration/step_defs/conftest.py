"""Shared fixtures and context for BDD step definitions."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import pytest

from domain.models import (
    CommonAnswers,
    JobApplicationRecord,
    JobPostingRef,
    RunContext,
    UserProfile,
)
from domain.services import (
    AccountFlowService,
    CaptchaHandler,
    DebugRunManager,
    JobApplicationAgent,
    WorkAuthorizationService,
)
from test.mocks import (
    FakeBrowserSession,
    FakeUserInteraction,
    FixedClock,
    InMemoryCredentialRepository,
    InMemoryDebugArtifactStore,
    InMemoryJobApplicationRepository,
    InMemoryLogger,
    SequentialIdGenerator,
)


@dataclass
class ApplyContext:
    """Holds mutable state shared across BDD steps."""

    profile: UserProfile = None  # type: ignore[assignment]
    browser: FakeBrowserSession = field(default_factory=FakeBrowserSession)
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

    agent = JobApplicationAgent(
        job_repo=ctx.job_repo,
        credential_repo=ctx.credential_repo,
        clock=clock,
        id_generator=ids,
        logger=logger,
        account_flow=AccountFlowService(),
        captcha_handler=CaptchaHandler(),
        work_auth_service=WorkAuthorizationService(),
        debug_manager=debug_manager,
    )

    run_context = RunContext(
        run_id=ids.new_run_id(),
        is_debug=ctx.debug_mode,
    )

    async def _apply() -> JobApplicationRecord:
        return await agent.apply_to_job(
            browser=ctx.browser,
            ui=ctx.ui,
            job=ctx.job,  # type: ignore[arg-type]
            profile=ctx.profile,
            resume_data=_default_resume_data(),
            common_answers=CommonAnswers(),
            run_context=run_context,
        )

    ctx.record = asyncio.run(_apply())


def _default_resume_data():
    from domain.models import ResumeData

    return ResumeData(
        primary_resume_path="/fake/resume.pdf",
        cover_letter_paths=("/fake/cover_letter.pdf",),
    )
