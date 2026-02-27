from __future__ import annotations

from domain.models import AppConfig, ResumeData, UserProfile
from domain.ports import ConfigProviderPort


class InMemoryConfigProvider:
    """In-memory test double for ConfigProviderPort."""

    def __init__(
        self,
        *,
        config: AppConfig | None = None,
        profile: UserProfile | None = None,
        resume_path: str = "/fake/resume.pdf",
        cover_letter_path: str = "/fake/cover_letter.pdf",
        validation_errors: list[str] | None = None,
    ) -> None:
        self._config = config or AppConfig(
            bot_token="test-token",
            telegram_chat_id="123",
            openai_key="sk-test",
            openai_base_url="https://api.test/v1",
        )
        self._profile = profile or UserProfile(full_name="Test User", email="test@example.com")
        self._resume_path = resume_path
        self._cover_letter_path = cover_letter_path
        self._validation_errors = validation_errors or []

    def get_config(self) -> AppConfig:
        return self._config

    def get_profile(self) -> UserProfile:
        return self._profile

    def get_resume_path(self) -> str:
        return self._resume_path

    def get_cover_letter_path(self) -> str:
        return self._cover_letter_path

    def validate(self) -> list[str]:
        return list(self._validation_errors)


_provider_check: ConfigProviderPort = InMemoryConfigProvider()
