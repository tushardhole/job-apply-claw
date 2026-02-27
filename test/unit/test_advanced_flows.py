from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from domain.models import CommonAnswers, JobApplicationStatus, JobPostingRef, ResumeData, RunContext, UserProfile
from domain.services import (
    AccountFlowService,
    CaptchaHandler,
    JobApplicationAgent,
    WorkAuthorizationService,
)
from test.mocks import (
    FakeBrowserSession,
    FakeUserInteraction,
    FixedClock,
    InMemoryCredentialRepository,
    InMemoryJobApplicationRepository,
    InMemoryLogger,
    SequentialIdGenerator,
)


def _make_agent() -> JobApplicationAgent:
    return JobApplicationAgent(
        job_repo=InMemoryJobApplicationRepository(),
        credential_repo=InMemoryCredentialRepository(),
        clock=FixedClock(datetime(2025, 1, 1, tzinfo=timezone.utc)),
        id_generator=SequentialIdGenerator(),
        logger=InMemoryLogger(),
        account_flow=AccountFlowService(),
        captcha_handler=CaptchaHandler(),
        work_auth_service=WorkAuthorizationService(),
    )


def _payload() -> tuple[JobPostingRef, UserProfile, ResumeData, CommonAnswers]:
    return (
        JobPostingRef(
            company_name="Acme",
            job_title="Platform Engineer",
            job_url="https://example.test/jobs/2",
            job_board_type="workday",
        ),
        UserProfile(full_name="Ada Lovelace", email="ada@example.com"),
        ResumeData(primary_resume_path="/tmp/resume.pdf"),
        CommonAnswers(),
    )


def test_text_captcha_is_sent_to_user_and_filled_back() -> None:
    agent = _make_agent()
    browser = FakeBrowserSession(captcha_present=True)
    ui = FakeUserInteraction(free_text_answers={"captcha_text": "7A3P"})
    job, profile, resume_data, common_answers = _payload()

    async def main() -> None:
        record = await agent.apply_to_job(
            browser=browser,
            ui=ui,
            job=job,
            profile=profile,
            resume_data=resume_data,
            common_answers=common_answers,
            run_context=RunContext(run_id="run-captcha"),
        )
        assert record.status is JobApplicationStatus.APPLIED

    asyncio.run(main())
    assert browser.filled_inputs["captcha"] == "7A3P"
    assert len(ui.image_prompts) == 1


def test_image_captcha_causes_failure() -> None:
    agent = _make_agent()
    browser = FakeBrowserSession(captcha_present=True, image_captcha=True)
    ui = FakeUserInteraction()
    job, profile, resume_data, common_answers = _payload()

    async def main() -> None:
        record = await agent.apply_to_job(
            browser=browser,
            ui=ui,
            job=job,
            profile=profile,
            resume_data=resume_data,
            common_answers=common_answers,
            run_context=RunContext(run_id="run-image-captcha"),
        )
        assert record.status is JobApplicationStatus.FAILED
        assert "Image-based captcha" in (record.failure_reason or "")

    asyncio.run(main())


def test_otp_and_account_exists_paths_request_user_follow_up() -> None:
    agent = _make_agent()
    browser = FakeBrowserSession(
        login_required=True,
        guest_apply_available=False,
        otp_required=True,
        account_already_exists=True,
    )
    ui = FakeUserInteraction(
        free_text_answers={
            "account_otp": "123456",
            "password_reset_code": "RESET-TOKEN",
        }
    )
    job, profile, resume_data, common_answers = _payload()

    async def main() -> None:
        record = await agent.apply_to_job(
            browser=browser,
            ui=ui,
            job=job,
            profile=profile,
            resume_data=resume_data,
            common_answers=common_answers,
            run_context=RunContext(run_id="run-otp"),
        )
        assert record.status is JobApplicationStatus.APPLIED

    asyncio.run(main())
    assert browser.filled_inputs["otp"] == "123456"
    assert browser.filled_inputs["password_reset_code"] == "RESET-TOKEN"
    assert "Forgot Password" in browser.clicked_buttons
