from __future__ import annotations

from datetime import datetime
from typing import Any

from domain import ClockPort, IdGeneratorPort, LoggerPort
from domain.models import RunContext
from domain.ports import DebugArtifactStorePort


class FixedClock:
    def __init__(self, now_value: datetime) -> None:
        self._now = now_value

    def now(self) -> datetime:
        return self._now


class SequentialIdGenerator:
    def __init__(self) -> None:
        self._counter = 0

    def new_run_id(self) -> str:
        self._counter += 1
        return f"run-{self._counter}"

    def new_correlation_id(self) -> str:
        self._counter += 1
        return f"id-{self._counter}"


class InMemoryLogger:
    def __init__(self) -> None:
        self.events: list[tuple[str, str, dict[str, Any]]] = []

    def info(self, message: str, **fields: Any) -> None:
        self.events.append(("info", message, fields))

    def warning(self, message: str, **fields: Any) -> None:
        self.events.append(("warning", message, fields))

    def error(self, message: str, **fields: Any) -> None:
        self.events.append(("error", message, fields))


class InMemoryDebugArtifactStore:
    def __init__(self) -> None:
        self.saved: list[tuple[str, str, bytes]] = []

    def ensure_run_directory(self, run_context: RunContext) -> str:
        return run_context.log_directory or f"logs/run_{run_context.run_id}"

    def save_screenshot(
        self,
        run_context: RunContext,
        step_name: str,
        image_bytes: bytes,
    ) -> str:
        self.saved.append((run_context.run_id, step_name, image_bytes))
        return f"logs/run_{run_context.run_id}/{step_name}.png"


_clock_check: ClockPort = FixedClock(datetime(2025, 1, 1))
_id_check: IdGeneratorPort = SequentialIdGenerator()
_logger_check: LoggerPort = InMemoryLogger()
_debug_store_check: DebugArtifactStorePort = InMemoryDebugArtifactStore()
