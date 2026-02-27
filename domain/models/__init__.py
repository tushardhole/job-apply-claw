from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class UserProfile:
    """Basic user profile information used when applying to jobs.

    Work-authorization status is intentionally excluded here.
    It is country- and time-sensitive, so the bot should always
    ask the user at application time via ``WorkAuthorizationService``.
    """

    full_name: str
    email: str
    phone: str | None = None
    address: str | None = None


@dataclass(frozen=True)
class ResumeData:
    """References to resume and cover letter assets plus structured skills."""

    primary_resume_path: str
    additional_resume_paths: Sequence[str] = field(default_factory=tuple)
    cover_letter_paths: Sequence[str] = field(default_factory=tuple)
    skills: Sequence[str] = field(default_factory=tuple)


@dataclass(frozen=True)
class CommonAnswers:
    """
    Normalized answers to frequently asked questions in application forms.

    Keys are stable question identifiers such as ``\"salary_expectation\"``.
    """

    answers: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Freeze internal mapping to uphold dataclass immutability expectations.
        object.__setattr__(self, "answers", MappingProxyType(dict(self.answers)))

    def get(self, key: str, default: str | None = None) -> str | None:
        return self.answers.get(key, default)


@dataclass(frozen=True)
class JobPostingRef:
    """Lightweight reference to a job posting on a specific job board."""

    company_name: str
    job_title: str
    job_url: str
    job_board_type: str | None = None


class JobApplicationStatus(str, Enum):
    """High-level lifecycle states for a job application."""

    PENDING = "pending"
    APPLIED = "applied"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class JobApplicationRecord:
    """
    Persistent record of a single job application attempt.

    The concrete repository is responsible for generating and assigning
    stable identifiers.
    """

    id: str
    company_name: str
    job_title: str
    job_url: str
    status: JobApplicationStatus
    applied_at: datetime | None = None
    failure_reason: str | None = None
    debug_run_id: str | None = None


@dataclass(frozen=True)
class AccountCredential:
    """
    Credentials for a specific job board portal and tenant (company).

    The concrete repository is responsible for hashing or encrypting
    sensitive values before storage.
    """

    id: str
    portal: str  # e.g. "greenhouse"
    tenant: str  # e.g. "company-a"
    email: str
    password: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class RunContext:
    """
    Per-run context for orchestrating applications and debug sessions.

    The log directory is an abstract path; infra decides how it maps
    to the real filesystem.
    """

    run_id: str
    is_debug: bool = False
    log_directory: str | None = None


@dataclass(frozen=True)
class AppConfig:
    """Application-level configuration loaded from config.json."""

    bot_token: str
    telegram_chat_id: str
    openai_key: str
    openai_base_url: str
    debug_mode: bool = False


@dataclass(frozen=True)
class FreeTextQuestionResponse:
    """Structured response to a free-text question asked to the user."""

    question_id: str
    text: str


@dataclass(frozen=True)
class ChoiceQuestionResponse:
    """Structured response to a multiple-choice question."""

    question_id: str
    selected_options: Sequence[str]


@dataclass(frozen=True)
class ToolDefinition:
    """Schema for a browser tool the LLM agent can call."""

    name: str
    description: str
    parameters: dict[str, Any]


@dataclass(frozen=True)
class ToolCall:
    """A single tool invocation decided by the LLM."""

    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class LLMToolResponse:
    """Parsed response from an LLM that supports tool/function calling."""

    tool_calls: list[ToolCall] | None = None
    text: str | None = None
    finish_reason: str | None = None


@dataclass(frozen=True)
class AgentStep:
    """Record of one step executed in the browser-agent loop."""

    step_number: int
    tool_name: str
    tool_args: dict[str, Any]
    tool_result: str
    screenshot_bytes: bytes | None = None


@dataclass(frozen=True)
class AgentTask:
    """High-level task for the browser agent to execute."""

    objective: str
    context: dict[str, Any] = field(default_factory=dict)
    max_steps: int = 50
    debug: bool = False


@dataclass(frozen=True)
class AgentResult:
    """Outcome of a browser-agent task execution."""

    status: str  # "success" | "failed" | "skipped"
    reason: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    steps_taken: list[AgentStep] = field(default_factory=list)


__all__ = [
    "AppConfig",
    "UserProfile",
    "ResumeData",
    "CommonAnswers",
    "JobPostingRef",
    "JobApplicationStatus",
    "JobApplicationRecord",
    "AccountCredential",
    "RunContext",
    "FreeTextQuestionResponse",
    "ChoiceQuestionResponse",
    "ToolDefinition",
    "ToolCall",
    "LLMToolResponse",
    "AgentStep",
    "AgentTask",
    "AgentResult",
]

