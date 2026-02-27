"""Infrastructure adapters – concrete implementations of domain ports."""

from .browser import MockBrowserSession, PlaywrightBrowserSession
from .config import FileSystemConfigProvider
from .interaction import ConsoleUserInteraction
from .logs import FileSystemDebugArtifactStore
from .persistence import (
    SQLiteConfigRepository,
    SQLiteCredentialRepository,
    SQLiteJobApplicationRepository,
    SQLiteOnboardingRepository,
)
from .runtime import StructuredLogger, SystemClock, UuidIdGenerator
from .telegram import TelegramBotConfig, TelegramUserInteraction

__all__ = [
    "PlaywrightBrowserSession",
    "MockBrowserSession",
    "FileSystemConfigProvider",
    "ConsoleUserInteraction",
    "FileSystemDebugArtifactStore",
    "SQLiteConfigRepository",
    "SQLiteOnboardingRepository",
    "SQLiteJobApplicationRepository",
    "SQLiteCredentialRepository",
    "SystemClock",
    "UuidIdGenerator",
    "StructuredLogger",
    "TelegramBotConfig",
    "TelegramUserInteraction",
]

