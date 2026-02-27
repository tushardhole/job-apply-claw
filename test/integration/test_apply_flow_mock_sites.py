"""
Integration tests that exercise the full JobApplicationAgent pipeline
against mock browser scenarios matching the HTML mock site variations.

These tests use in-memory fakes so they run without Playwright installed.
The mock_sites HTML pages are verified to exist as fixtures for future
real-browser testing.
"""

from __future__ import annotations

import asyncio
import pathlib
from datetime import datetime, timezone

from domain.models import (
    CommonAnswers,
    JobApplicationStatus,
    JobPostingRef,
    ResumeData,
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
from test.fixtures import mock_cover_letter_path, mock_resume_path
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

_MOCK_SITES = pathlib.Path(__file__).parent / "mock_sites"


def _make_agent(
    debug: bool = False,
) -> tuple[
    JobApplicationAgent,
    InMemoryJobApplicationRepository,
    InMemoryCredentialRepository,
    InMemoryDebugArtifactStore | None,
]:
    job_repo = InMemoryJobApplicationRepository()
    cred_repo = InMemoryCredentialRepository()
    debug_store = InMemoryDebugArtifactStore() if debug else None
    agent = JobApplicationAgent(
        job_repo=job_repo,
        credential_repo=cred_repo,
        clock=FixedClock(datetime(2025, 6, 1, tzinfo=timezone.utc)),
        id_generator=SequentialIdGenerator(),
        logger=InMemoryLogger(),
        account_flow=AccountFlowService(),
        captcha_handler=CaptchaHandler(),
        work_auth_service=WorkAuthorizationService(),
        debug_manager=DebugRunManager(debug_store) if debug_store else None,
    )
    return agent, job_repo, cred_repo, debug_store


def _profile_and_resume() -> tuple[UserProfile, ResumeData, CommonAnswers]:
    return (
        UserProfile(full_name="Ada Lovelace", email="ada@example.com", phone="123"),
        ResumeData(
            primary_resume_path=mock_resume_path(),
            cover_letter_paths=(mock_cover_letter_path(),),
        ),
        CommonAnswers(answers={"salary_expectation": "120000"}),
    )


def test_mock_site_htmls_exist() -> None:
    expected = [
        "guest_apply.html",
        "login_required.html",
        "login_otp.html",
        "text_captcha.html",
        "image_captcha.html",
        "oauth_only.html",
        "account_exists.html",
    ]
    for name in expected:
        assert (_MOCK_SITES / name).exists(), f"Missing mock site: {name}"


def test_guest_apply_flow() -> None:
    agent, job_repo, _, _ = _make_agent()
    browser = FakeBrowserSession(login_required=False, guest_apply_available=True)
    ui = FakeUserInteraction()
    profile, resume_data, common = _profile_and_resume()
    job = JobPostingRef("Acme", "Engineer", "http://localhost/guest_apply.html", "mock")

    record = asyncio.run(agent.apply_to_job(
        browser=browser, ui=ui, job=job,
        profile=profile, resume_data=resume_data,
        common_answers=common, run_context=RunContext(run_id="int-1"),
    ))
    assert record.status is JobApplicationStatus.APPLIED
    assert "Apply" in browser.clicked_buttons


def test_login_required_flow() -> None:
    agent, _, cred_repo, _ = _make_agent()
    browser = FakeBrowserSession(login_required=True, guest_apply_available=False)
    ui = FakeUserInteraction()
    profile, resume_data, common = _profile_and_resume()
    job = JobPostingRef("Beta", "Developer", "http://localhost/login_required.html", "mock")

    record = asyncio.run(agent.apply_to_job(
        browser=browser, ui=ui, job=job,
        profile=profile, resume_data=resume_data,
        common_answers=common, run_context=RunContext(run_id="int-2"),
    ))
    assert record.status is JobApplicationStatus.APPLIED
    assert len(cred_repo.list_all()) == 1


def test_login_otp_flow() -> None:
    agent, _, _, _ = _make_agent()
    browser = FakeBrowserSession(
        login_required=True, guest_apply_available=False, otp_required=True,
    )
    ui = FakeUserInteraction(free_text_answers={"account_otp": "123456"})
    profile, resume_data, common = _profile_and_resume()
    job = JobPostingRef("Gamma", "SRE", "http://localhost/login_otp.html", "mock")

    record = asyncio.run(agent.apply_to_job(
        browser=browser, ui=ui, job=job,
        profile=profile, resume_data=resume_data,
        common_answers=common, run_context=RunContext(run_id="int-3"),
    ))
    assert record.status is JobApplicationStatus.APPLIED
    assert browser.filled_inputs["otp"] == "123456"


def test_account_exists_forgot_password_flow() -> None:
    agent, _, _, _ = _make_agent()
    browser = FakeBrowserSession(
        login_required=True, guest_apply_available=False,
        account_already_exists=True, otp_required=False,
    )
    ui = FakeUserInteraction(free_text_answers={"password_reset_code": "RESET-XYZ"})
    profile, resume_data, common = _profile_and_resume()
    job = JobPostingRef("Eta", "PM", "http://localhost/account_exists.html", "mock")

    record = asyncio.run(agent.apply_to_job(
        browser=browser, ui=ui, job=job,
        profile=profile, resume_data=resume_data,
        common_answers=common, run_context=RunContext(run_id="int-4"),
    ))
    assert record.status is JobApplicationStatus.APPLIED
    assert "Forgot Password" in browser.clicked_buttons
    assert browser.filled_inputs["password_reset_code"] == "RESET-XYZ"


def test_text_captcha_flow() -> None:
    agent, _, _, _ = _make_agent()
    browser = FakeBrowserSession(captcha_present=True, image_captcha=False)
    ui = FakeUserInteraction(free_text_answers={"captcha_text": "A1B2"})
    profile, resume_data, common = _profile_and_resume()
    job = JobPostingRef("Delta", "QA", "http://localhost/text_captcha.html", "mock")

    record = asyncio.run(agent.apply_to_job(
        browser=browser, ui=ui, job=job,
        profile=profile, resume_data=resume_data,
        common_answers=common, run_context=RunContext(run_id="int-5"),
    ))
    assert record.status is JobApplicationStatus.APPLIED
    assert browser.filled_inputs["captcha"] == "A1B2"


def test_image_captcha_fails_fast() -> None:
    agent, _, _, _ = _make_agent()
    browser = FakeBrowserSession(captcha_present=True, image_captcha=True)
    ui = FakeUserInteraction()
    profile, resume_data, common = _profile_and_resume()
    job = JobPostingRef("Zeta", "DS", "http://localhost/image_captcha.html", "mock")

    record = asyncio.run(agent.apply_to_job(
        browser=browser, ui=ui, job=job,
        profile=profile, resume_data=resume_data,
        common_answers=common, run_context=RunContext(run_id="int-6"),
    ))
    assert record.status is JobApplicationStatus.FAILED
    assert "Image-based captcha" in (record.failure_reason or "")


def test_oauth_only_fails_fast() -> None:
    agent, _, _, _ = _make_agent()
    browser = FakeBrowserSession(oauth_only_login=True)
    ui = FakeUserInteraction()
    profile, resume_data, common = _profile_and_resume()
    job = JobPostingRef("Epsilon", "FE", "http://localhost/oauth_only.html", "mock")

    record = asyncio.run(agent.apply_to_job(
        browser=browser, ui=ui, job=job,
        profile=profile, resume_data=resume_data,
        common_answers=common, run_context=RunContext(run_id="int-7"),
    ))
    assert record.status is JobApplicationStatus.FAILED
    assert "OAuth-only" in (record.failure_reason or "")


def test_debug_mode_with_guest_apply() -> None:
    agent, job_repo, _, debug_store = _make_agent(debug=True)
    browser = FakeBrowserSession()
    ui = FakeUserInteraction()
    profile, resume_data, common = _profile_and_resume()
    job = JobPostingRef("Acme", "Engineer", "http://localhost/guest_apply.html", "mock")

    record = asyncio.run(agent.apply_to_job(
        browser=browser, ui=ui, job=job,
        profile=profile, resume_data=resume_data,
        common_answers=common, run_context=RunContext(run_id="int-8", is_debug=True),
    ))
    assert record.status is JobApplicationStatus.SKIPPED
    assert "Apply" not in browser.clicked_buttons
    assert debug_store is not None
    assert len(debug_store.saved) >= 3
    assert len(debug_store.metadata) == 1


def test_local_server_serves_mock_pages(mock_site_server: str) -> None:
    import urllib.request

    resp = urllib.request.urlopen(f"{mock_site_server}/guest_apply.html")
    html = resp.read().decode()
    assert "Apply as Guest" in html
