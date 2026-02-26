"""
Domain layer package.

This package contains pure business logic models and ports that are
independent of any specific infrastructure or frameworks.
"""

from .models import (  # noqa: F401
    AccountCredential,
    CommonAnswers,
    JobApplicationRecord,
    JobApplicationStatus,
    JobPostingRef,
    RunContext,
    UserProfile,
)
from .ports import (  # noqa: F401
    BrowserSessionPort,
    ClockPort,
    CredentialRepositoryPort,
    IdGeneratorPort,
    JobApplicationRepositoryPort,
    LLMClientPort,
    LoggerPort,
    OnboardingRepositoryPort,
    UserInteractionPort,
)

__all__ = [
    # Models
    "UserProfile",
    "CommonAnswers",
    "JobPostingRef",
    "JobApplicationStatus",
    "JobApplicationRecord",
    "AccountCredential",
    "RunContext",
    # Ports
    "OnboardingRepositoryPort",
    "JobApplicationRepositoryPort",
    "CredentialRepositoryPort",
    "UserInteractionPort",
    "BrowserSessionPort",
    "LLMClientPort",
    "ClockPort",
    "IdGeneratorPort",
    "LoggerPort",
]

