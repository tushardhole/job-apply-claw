from __future__ import annotations

from abc import abstractmethod
from datetime import datetime
from typing import Any, Protocol, Sequence, runtime_checkable

from domain.models import (
    AccountCredential,
    ChoiceQuestionResponse,
    CommonAnswers,
    FreeTextQuestionResponse,
    JobApplicationRecord,
    JobPostingRef,
    ResumeData,
    RunContext,
    UserProfile,
)


@runtime_checkable
class OnboardingRepositoryPort(Protocol):
    """Persistence for onboarding-related data."""

    @abstractmethod
    def get_user_profile(self) -> UserProfile | None:
        ...

    @abstractmethod
    def save_user_profile(self, profile: UserProfile) -> None:
        ...

    @abstractmethod
    def get_resume_data(self) -> ResumeData | None:
        ...

    @abstractmethod
    def save_resume_data(self, data: ResumeData) -> None:
        ...

    @abstractmethod
    def get_common_answers(self) -> CommonAnswers:
        ...

    @abstractmethod
    def save_common_answers(self, answers: CommonAnswers) -> None:
        ...

@runtime_checkable
class ConfigRepositoryPort(Protocol):
    """Persistence for runtime and integration configuration values."""

    @abstractmethod
    def get_config_value(self, key: str) -> str | None:
        ...

    @abstractmethod
    def set_config_value(self, key: str, value: str) -> None:
        ...


@runtime_checkable
class JobApplicationRepositoryPort(Protocol):
    """Store and query job application records."""

    @abstractmethod
    def add(self, record: JobApplicationRecord) -> None:
        ...

    @abstractmethod
    def update(self, record: JobApplicationRecord) -> None:
        ...

    @abstractmethod
    def get(self, record_id: str) -> JobApplicationRecord | None:
        ...

    @abstractmethod
    def list_all(self) -> Sequence[JobApplicationRecord]:
        ...


@runtime_checkable
class CredentialRepositoryPort(Protocol):
    """Store and query credentials for job boards and company accounts."""

    @abstractmethod
    def upsert(self, credential: AccountCredential) -> None:
        ...

    @abstractmethod
    def get(
        self,
        portal: str,
        tenant: str,
        email: str,
    ) -> AccountCredential | None:
        ...

    @abstractmethod
    def list_all(self) -> Sequence[AccountCredential]:
        ...


@runtime_checkable
class UserInteractionPort(Protocol):
    """
    High-level user interaction abstraction (e.g. Telegram).

    All methods are asynchronous to make it easy to integrate with
    async-first messaging libraries.
    """

    async def send_info(self, message: str) -> None:
        ...

    async def ask_free_text(
        self,
        question_id: str,
        prompt: str,
    ) -> FreeTextQuestionResponse:
        ...

    async def ask_choice(
        self,
        question_id: str,
        prompt: str,
        options: Sequence[str],
        allow_multiple: bool = False,
    ) -> ChoiceQuestionResponse:
        ...

    async def send_image_and_ask_text(
        self,
        question_id: str,
        image_bytes: bytes,
        prompt: str,
    ) -> FreeTextQuestionResponse:
        ...


@runtime_checkable
class BrowserSessionPort(Protocol):
    """
    High-level browser automation primitives used by job board strategies.

    The concrete implementation is expected to wrap tools such as
    Playwright or Selenium.
    """

    async def goto(self, url: str) -> None:
        ...

    async def wait_for_load(self) -> None:
        ...

    async def click_button(self, label_or_selector: str) -> None:
        ...

    async def fill_input(self, label_or_selector: str, value: str) -> None:
        ...

    async def select_option(self, label_or_selector: str, value: str) -> None:
        ...

    async def upload_file(self, label_or_selector: str, path: str) -> None:
        ...

    async def detect_login_required(self) -> bool:
        ...

    async def detect_guest_apply_available(self) -> bool:
        ...

    async def detect_captcha_present(self) -> bool:
        ...

    async def detect_oauth_only_login(self) -> bool:
        ...

    async def detect_job_board_type(self, ref: JobPostingRef) -> str | None:
        ...

    async def take_screenshot(self, step_name: str) -> bytes:
        ...


@runtime_checkable
class LLMClientPort(Protocol):
    """Thin abstraction over an LLM text completion API."""

    async def complete(
        self,
        prompt: str,
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        ...


@runtime_checkable
class ClockPort(Protocol):
    """Time source for deterministic and easily testable code."""

    def now(self) -> datetime:
        ...


@runtime_checkable
class IdGeneratorPort(Protocol):
    """Generation of stable identifiers for runs and records."""

    def new_run_id(self) -> str:
        ...

    def new_correlation_id(self) -> str:
        ...


@runtime_checkable
class LoggerPort(Protocol):
    """Structured, testable logging abstraction."""

    def info(self, message: str, **fields: Any) -> None:
        ...

    def warning(self, message: str, **fields: Any) -> None:
        ...

    def error(self, message: str, **fields: Any) -> None:
        ...


__all__ = [
    "OnboardingRepositoryPort",
    "ConfigRepositoryPort",
    "JobApplicationRepositoryPort",
    "CredentialRepositoryPort",
    "UserInteractionPort",
    "BrowserSessionPort",
    "LLMClientPort",
    "ClockPort",
    "IdGeneratorPort",
    "LoggerPort",
]

