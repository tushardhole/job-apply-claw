import asyncio

import pytest

from domain.models import CommonAnswers, ResumeData, UserProfile
from domain.services import (
    OnboardingService,
    OnboardingSummary,
    OnboardingValidationError,
)
from test.mocks.fake_onboarding_repository import InMemoryOnboardingRepository
from test.mocks.fake_user_interaction import FakeUserInteraction


def _default_answers() -> dict[str, str]:
    return {
        "full_name": "Ada Lovelace",
        "email": "ada@example.com",
        "phone": "",
        "address": "London",
        "primary_resume_path": "/tmp/resume.pdf",
        "additional_resume_paths": "/tmp/alt1.pdf, ",
        "cover_letter_paths": "",
        "skills": "python, automation",
        "salary_expectation": "120000",
    }


def test_ensure_onboarding_complete_collects_and_persists_new_data() -> None:
    repo = InMemoryOnboardingRepository()
    ui = FakeUserInteraction(free_text_answers=_default_answers())
    service = OnboardingService(repo=repo, ui=ui)

    async def main() -> OnboardingSummary:
        return await service.ensure_onboarding_complete()

    summary = asyncio.run(main())

    assert isinstance(summary, OnboardingSummary)
    assert summary.profile == UserProfile(
        full_name="Ada Lovelace",
        email="ada@example.com",
        phone=None,
        address="London",
    )
    assert summary.resume_data == ResumeData(
        primary_resume_path="/tmp/resume.pdf",
        additional_resume_paths=("/tmp/alt1.pdf",),
        cover_letter_paths=(),
        skills=("python", "automation"),
    )
    assert summary.common_answers.get("salary_expectation") == "120000"

    assert repo.get_user_profile() == summary.profile
    assert repo.get_resume_data() is not None
    assert repo.get_common_answers().answers == summary.common_answers.answers


def test_ensure_onboarding_complete_reuses_existing_data() -> None:
    repo = InMemoryOnboardingRepository()
    existing_profile = UserProfile(
        full_name="Existing User",
        email="existing@example.com",
    )
    existing_resume = ResumeData(
        primary_resume_path="/path/resume.pdf",
        additional_resume_paths=("extra.pdf",),
        cover_letter_paths=(),
        skills=("python",),
    )
    repo.save_user_profile(existing_profile)
    repo.save_resume_data(existing_resume)
    repo.save_common_answers(
        CommonAnswers(answers={"salary_expectation": "100000"}),
    )

    ui = FakeUserInteraction(free_text_answers={})
    service = OnboardingService(repo=repo, ui=ui)

    async def main() -> OnboardingSummary:
        return await service.ensure_onboarding_complete()

    summary = asyncio.run(main())

    assert summary.profile == existing_profile
    assert summary.resume_data == existing_resume
    assert summary.common_answers.answers == {"salary_expectation": "100000"}

    # No additional free-text questions should have been asked
    assert ui.free_text_calls == []


def test_validation_error_for_missing_required_fields() -> None:
    answers = _default_answers()
    answers["full_name"] = ""

    repo = InMemoryOnboardingRepository()
    ui = FakeUserInteraction(free_text_answers=answers)
    service = OnboardingService(repo=repo, ui=ui)

    async def main() -> None:
        await service.ensure_onboarding_complete()

    with pytest.raises(OnboardingValidationError):
        asyncio.run(main())


def test_validation_error_for_invalid_existing_resume_data() -> None:
    repo = InMemoryOnboardingRepository()
    repo.save_user_profile(UserProfile(full_name="Ada Lovelace", email="ada@example.com"))
    repo.save_resume_data(ResumeData(primary_resume_path=""))
    repo.save_common_answers(CommonAnswers(answers={"salary_expectation": "120000"}))

    ui = FakeUserInteraction(free_text_answers={})
    service = OnboardingService(repo=repo, ui=ui)

    async def main() -> None:
        await service.ensure_onboarding_complete()

    with pytest.raises(OnboardingValidationError):
        asyncio.run(main())
