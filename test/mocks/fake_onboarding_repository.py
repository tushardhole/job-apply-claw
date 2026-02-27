from __future__ import annotations

from domain import CommonAnswers, OnboardingRepositoryPort, ResumeData, UserProfile


class InMemoryOnboardingRepository:
    """
    Simple in-memory implementation of ``OnboardingRepositoryPort``.

    Intended for use in unit and integration tests.
    """

    def __init__(self) -> None:
        self._user_profile: UserProfile | None = None
        self._resume_data: ResumeData | None = None
        self._common_answers: CommonAnswers = CommonAnswers()

    # User profile ---------------------------------------------------------
    def get_user_profile(self) -> UserProfile | None:
        return self._user_profile

    def save_user_profile(self, profile: UserProfile) -> None:
        self._user_profile = profile

    # Resume data ----------------------------------------------------------
    def get_resume_data(self) -> ResumeData | None:
        return self._resume_data

    def save_resume_data(self, data: ResumeData) -> None:
        self._resume_data = data

    # Common answers -------------------------------------------------------
    def get_common_answers(self) -> CommonAnswers:
        return self._common_answers

    def save_common_answers(self, answers: CommonAnswers) -> None:
        self._common_answers = answers

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            f"InMemoryOnboardingRepository("
            f"user_profile={self._user_profile!r}, "
            f"resume_data={self._resume_data!r}, "
            f"common_answers={self._common_answers!r})"
        )


_repo_protocol_check: OnboardingRepositoryPort
_repo_protocol_check = InMemoryOnboardingRepository()
