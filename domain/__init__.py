"""
Domain layer package.

This package contains pure business logic models and ports that are
independent of any specific infrastructure or frameworks.
"""

from .models import (  # noqa: F401
    AccountCredential,
    AgentResult,
    AgentStep,
    AgentTask,
    AppConfig,
    ChoiceQuestionResponse,
    CommonAnswers,
    FreeTextQuestionResponse,
    JobApplicationRecord,
    JobApplicationStatus,
    JobPostingRef,
    LLMToolResponse,
    ResumeData,
    RunContext,
    ToolCall,
    ToolDefinition,
    UserProfile,
)
from .ports import (  # noqa: F401
    BrowserAgentPort,
    BrowserSessionPort,
    BrowserToolsPort,
    ClockPort,
    ConfigProviderPort,
    ConfigRepositoryPort,
    CredentialRepositoryPort,
    DebugArtifactStorePort,
    IdGeneratorPort,
    JobApplicationRepositoryPort,
    LLMClientPort,
    LoggerPort,
    OnboardingRepositoryPort,
    UserInteractionPort,
)

__all__ = [
    # Models
    "AppConfig",
    "UserProfile",
    "ResumeData",
    "CommonAnswers",
    "FreeTextQuestionResponse",
    "ChoiceQuestionResponse",
    "JobPostingRef",
    "JobApplicationStatus",
    "JobApplicationRecord",
    "AccountCredential",
    "RunContext",
    "ToolDefinition",
    "ToolCall",
    "LLMToolResponse",
    "AgentStep",
    "AgentTask",
    "AgentResult",
    # Ports
    "OnboardingRepositoryPort",
    "ConfigRepositoryPort",
    "ConfigProviderPort",
    "JobApplicationRepositoryPort",
    "CredentialRepositoryPort",
    "UserInteractionPort",
    "BrowserSessionPort",
    "BrowserToolsPort",
    "BrowserAgentPort",
    "LLMClientPort",
    "ClockPort",
    "IdGeneratorPort",
    "LoggerPort",
    "DebugArtifactStorePort",
]

