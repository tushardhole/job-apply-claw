from __future__ import annotations

from dataclasses import dataclass

from domain.models import CommonAnswers, ResumeData, UserProfile
from domain.ports import OnboardingRepositoryPort, UserInteractionPort
from domain.utils import split_csv


class OnboardingValidationError(ValueError):
    """Raised when collected onboarding data is incomplete or invalid."""


@dataclass(frozen=True)
class OnboardingSummary:
    """Snapshot of the key onboarding data the agent needs."""

    profile: UserProfile
    resume_data: ResumeData
    common_answers: CommonAnswers


class OnboardingService:
    """
    Orchestrates the interactive onboarding flow.

    The service is intentionally small and relies only on abstractions so it
    can be used from both CLI and future UI layers.
    """

    def __init__(
        self,
        repo: OnboardingRepositoryPort,
        ui: UserInteractionPort,
    ) -> None:
        self._repo = repo
        self._ui = ui

    async def ensure_onboarding_complete(self) -> OnboardingSummary:
        """
        Ensure that core onboarding data exists and is valid.

        If data is missing it will be collected via the ``UserInteractionPort``
        and persisted via the ``OnboardingRepositoryPort``.
        """
        profile = self._repo.get_user_profile()
        if profile is None:
            profile = await self._collect_user_profile()
            self._repo.save_user_profile(profile)
        else:
            self._validate_profile(profile)

        resume_data = self._repo.get_resume_data()
        if resume_data is None:
            resume_data = await self._collect_resume_data()
            self._repo.save_resume_data(resume_data)
        else:
            self._validate_resume_data(resume_data)

        common_answers = self._repo.get_common_answers()
        if not common_answers.answers:
            common_answers = await self._collect_common_answers(existing=common_answers)
            self._repo.save_common_answers(common_answers)

        return OnboardingSummary(
            profile=profile,
            resume_data=resume_data,
            common_answers=common_answers,
        )

    async def _collect_user_profile(self) -> UserProfile:
        await self._ui.send_info(
            "Let's set up your basic profile used for job applications.",
        )

        full_name_resp = await self._ui.ask_free_text(
            "full_name",
            "What is your full name?",
        )
        email_resp = await self._ui.ask_free_text(
            "email",
            "What email address should be used on applications?",
        )
        phone_resp = await self._ui.ask_free_text(
            "phone",
            "What phone number should be used? Leave blank to skip.",
        )
        address_resp = await self._ui.ask_free_text(
            "address",
            "What is your address (city, country or full mailing address)? "
            "Leave blank to skip.",
        )

        profile = UserProfile(
            full_name=full_name_resp.text.strip(),
            email=email_resp.text.strip(),
            phone=phone_resp.text.strip() or None,
            address=address_resp.text.strip() or None,
        )
        self._validate_profile(profile)
        return profile

    async def _collect_resume_data(self) -> ResumeData:
        await self._ui.send_info(
            "Now let's capture where your resume and cover letters live.",
        )

        primary_resp = await self._ui.ask_free_text(
            "primary_resume_path",
            "Path to your primary resume file "
            "(for example, '/home/user/resume.pdf'):",
        )
        additional_resp = await self._ui.ask_free_text(
            "additional_resume_paths",
            "Optional: additional resume paths separated by commas. "
            "Leave blank to skip.",
        )
        cover_resp = await self._ui.ask_free_text(
            "cover_letter_paths",
            "Optional: cover letter paths separated by commas. "
            "Leave blank to skip.",
        )
        skills_resp = await self._ui.ask_free_text(
            "skills",
            "Optional: list a few key skills separated by commas. "
            "Leave blank to skip.",
        )

        primary = primary_resp.text.strip()
        if not primary:
            raise OnboardingValidationError("primary_resume_path cannot be empty")

        resume = ResumeData(
            primary_resume_path=primary,
            additional_resume_paths=split_csv(additional_resp.text),
            cover_letter_paths=split_csv(cover_resp.text),
            skills=split_csv(skills_resp.text),
        )
        return resume

    async def _collect_common_answers(
        self,
        *,
        existing: CommonAnswers | None = None,
    ) -> CommonAnswers:
        base = dict(existing.answers if existing is not None else {})

        salary_resp = await self._ui.ask_free_text(
            "salary_expectation",
            "Optional: what is your typical annual salary expectation? "
            "Leave blank to skip.",
        )
        salary = salary_resp.text.strip()
        if salary:
            base["salary_expectation"] = salary

        return CommonAnswers(answers=base)

    def _validate_profile(self, profile: UserProfile) -> None:
        if not profile.full_name.strip():
            raise OnboardingValidationError("full_name cannot be empty")
        if not profile.email.strip():
            raise OnboardingValidationError("email cannot be empty")

    def _validate_resume_data(self, resume_data: ResumeData) -> None:
        if not resume_data.primary_resume_path.strip():
            raise OnboardingValidationError("primary_resume_path cannot be empty")

