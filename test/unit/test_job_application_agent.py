from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from domain.models import CommonAnswers, JobApplicationStatus, JobPostingRef, ResumeData, RunContext, UserProfile
from domain.services import (
    AccountFlowService,
    CaptchaHandler,
    DebugRunManager,
    JobApplicationAgent,
    WorkAuthorizationQuestion,
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


def _build_agent(debug_store: InMemoryDebugArtifactStore | None = None) -> tuple[JobApplicationAgent, InMemoryJobApplicationRepository, InMemoryCredentialRepository]:
    job_repo = InMemoryJobApplicationRepository()
    cred_repo = InMemoryCredentialRepository()
    debug_manager = DebugRunManager(debug_store) if debug_store is not None else None
    agent = JobApplicationAgent(
        job_repo=job_repo,
        credential_repo=cred_repo,
        clock=FixedClock(datetime(2025, 1, 1, tzinfo=timezone.utc)),
        id_generator=SequentialIdGenerator(),
        logger=InMemoryLogger(),
        account_flow=AccountFlowService(),
        captcha_handler=CaptchaHandler(),
        work_auth_service=WorkAuthorizationService(),
        debug_manager=debug_manager,
    )
    return agent, job_repo, cred_repo


def _default_payload() -> tuple[JobPostingRef, UserProfile, ResumeData, CommonAnswers]:
    return (
        JobPostingRef(
            company_name="Acme",
            job_title="Backend Engineer",
            job_url="https://example.test/jobs/1",
            job_board_type="greenhouse",
        ),
        UserProfile(full_name="Ada Lovelace", email="ada@example.com", phone="123"),
        ResumeData(primary_resume_path="/tmp/resume.pdf"),
        CommonAnswers(answers={"salary_expectation": "120000"}),
    )


def test_guest_happy_path_submits_application() -> None:
    agent, repo, _ = _build_agent()
    browser = FakeBrowserSession(login_required=False, guest_apply_available=True)
    ui = FakeUserInteraction()
    job, profile, resume_data, common_answers = _default_payload()

    async def main() -> None:
        record = await agent.apply_to_job(
            browser=browser,
            ui=ui,
            job=job,
            profile=profile,
            resume_data=resume_data,
            common_answers=common_answers,
            run_context=RunContext(run_id="run-1", is_debug=False),
        )
        assert record.status is JobApplicationStatus.APPLIED
        assert record.applied_at is not None

    asyncio.run(main())
    saved = repo.list_all()[0]
    assert saved.status is JobApplicationStatus.APPLIED
    assert browser.uploaded_files["resume"] == "/tmp/resume.pdf"
    assert "Apply" in browser.clicked_buttons
    assert any("Application submitted" in message for message in ui.info_messages)


def test_oauth_only_flow_fails_cleanly() -> None:
    agent, repo, _ = _build_agent()
    browser = FakeBrowserSession(oauth_only_login=True)
    ui = FakeUserInteraction()
    job, profile, resume_data, common_answers = _default_payload()

    async def main() -> None:
        record = await agent.apply_to_job(
            browser=browser,
            ui=ui,
            job=job,
            profile=profile,
            resume_data=resume_data,
            common_answers=common_answers,
            run_context=RunContext(run_id="run-2", is_debug=False),
        )
        assert record.status is JobApplicationStatus.FAILED
        assert "OAuth-only" in (record.failure_reason or "")

    asyncio.run(main())
    assert repo.list_all()[0].status is JobApplicationStatus.FAILED


def test_login_required_creates_account_and_stores_credentials() -> None:
    agent, _, cred_repo = _build_agent()
    browser = FakeBrowserSession(login_required=True, guest_apply_available=False)
    ui = FakeUserInteraction()
    job, profile, resume_data, common_answers = _default_payload()

    async def main() -> None:
        await agent.apply_to_job(
            browser=browser,
            ui=ui,
            job=job,
            profile=profile,
            resume_data=resume_data,
            common_answers=common_answers,
            run_context=RunContext(run_id="run-3", is_debug=False),
        )

    asyncio.run(main())
    creds = cred_repo.list_all()
    assert len(creds) == 1
    assert creds[0].email == "ada@example.com"
    assert "Create Account" in browser.clicked_buttons


def test_work_authorization_and_personal_questions_ask_user() -> None:
    agent, _, _ = _build_agent()
    browser = FakeBrowserSession(
        work_auth_questions=[
            WorkAuthorizationQuestion(
                question_id="work_auth_us",
                prompt="Are you authorized to work in the US?",
                options=["Yes", "No"],
            )
        ],
        personal_questions=[
            {"id": "proud_project", "prompt": "Tell us about a project you are proud of."}
        ],
    )
    ui = FakeUserInteraction(
        free_text_answers={"proud_project": "I built a resilient data pipeline."},
        choice_answers={"work_auth_us": ["Yes"]},
    )
    job, profile, resume_data, common_answers = _default_payload()

    async def main() -> None:
        await agent.apply_to_job(
            browser=browser,
            ui=ui,
            job=job,
            profile=profile,
            resume_data=resume_data,
            common_answers=common_answers,
            run_context=RunContext(run_id="run-4", is_debug=False),
        )

    asyncio.run(main())
    assert browser.selected_options["work_auth_us"] == "Yes"
    assert browser.filled_inputs["proud_project"] == "I built a resilient data pipeline."


def test_debug_mode_skips_final_submit_and_captures_screenshots() -> None:
    debug_store = InMemoryDebugArtifactStore()
    agent, repo, _ = _build_agent(debug_store=debug_store)
    browser = FakeBrowserSession()
    ui = FakeUserInteraction()
    job, profile, resume_data, common_answers = _default_payload()

    async def main() -> None:
        record = await agent.apply_to_job(
            browser=browser,
            ui=ui,
            job=job,
            profile=profile,
            resume_data=resume_data,
            common_answers=common_answers,
            run_context=RunContext(run_id="run-5", is_debug=True),
        )
        assert record.status is JobApplicationStatus.SKIPPED

    asyncio.run(main())
    saved = repo.list_all()[0]
    assert saved.status is JobApplicationStatus.SKIPPED
    assert "Apply" not in browser.clicked_buttons
    assert len(debug_store.saved) >= 3
    step_names = [s[1] for s in debug_store.saved]
    assert "pre_submit" in step_names
    assert len(debug_store.metadata) == 1
    meta = debug_store.metadata[0][1]
    assert meta["outcome"] == "skipped"
    assert meta["mode"] == "debug"
