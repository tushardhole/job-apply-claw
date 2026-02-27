"""
Reusable fakes and in-memory implementations for tests.
"""

from .fake_browser_session import FakeBrowserSession
from .fake_config_repository import InMemoryConfigRepository
from .fake_credential_repository import InMemoryCredentialRepository
from .fake_job_application_repository import InMemoryJobApplicationRepository
from .fake_onboarding_repository import InMemoryOnboardingRepository
from .fake_runtime import (
    FixedClock,
    InMemoryDebugArtifactStore,
    InMemoryLogger,
    SequentialIdGenerator,
)
from .fake_user_interaction import FakeUserInteraction

__all__ = [
    "FakeBrowserSession",
    "FakeUserInteraction",
    "InMemoryOnboardingRepository",
    "InMemoryConfigRepository",
    "InMemoryJobApplicationRepository",
    "InMemoryCredentialRepository",
    "FixedClock",
    "SequentialIdGenerator",
    "InMemoryLogger",
    "InMemoryDebugArtifactStore",
]

