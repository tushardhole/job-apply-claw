from __future__ import annotations

from typing import Any, Mapping

from domain import CommonAnswers, OnboardingRepositoryPort, UserProfile


class InMemoryOnboardingRepository:
    """
    Simple in-memory implementation of ``OnboardingRepositoryPort``.

    Intended for use in unit and integration tests.
    """

    def __init__(self) -> None:
        self._user_profile: UserProfile | None = None
        self._resume_data: dict[str, Any] | None = None
        self._common_answers: CommonAnswers = CommonAnswers()
        self._config: dict[str, str] = {}

    # User profile ---------------------------------------------------------
    def get_user_profile(self) -> UserProfile | None:
        return self._user_profile

    def save_user_profile(self, profile: UserProfile) -> None:
        self._user_profile = profile

    # Resume data ----------------------------------------------------------
    def get_resume_data(self) -> Mapping[str, Any] | None:
        return self._resume_data

    def save_resume_data(self, data: Mapping[str, Any]) -> None:
        self._resume_data = dict(data)

    # Common answers -------------------------------------------------------
    def get_common_answers(self) -> CommonAnswers:
        return self._common_answers

    def save_common_answers(self, answers: CommonAnswers) -> None:
        self._common_answers = answers

    # Config values --------------------------------------------------------
    def get_config_value(self, key: str) -> str | None:
        return self._config.get(key)

    def set_config_value(self, key: str, value: str) -> None:
        self._config[key] = value

    # For type-checkers: declare that we satisfy the protocol
    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            f"InMemoryOnboardingRepository("
            f"user_profile={self._user_profile!r}, "
            f"resume_data={self._resume_data!r}, "
            f"common_answers={self._common_answers!r})"
        )


# Ensure the class conforms to the protocol at type-check time.
_repo_protocol_check: OnboardingRepositoryPort
_repo_protocol_check = InMemoryOnboardingRepository()

