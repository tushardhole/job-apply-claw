from __future__ import annotations

from domain import ConfigRepositoryPort


class InMemoryConfigRepository:
    """Simple in-memory implementation of ``ConfigRepositoryPort``."""

    def __init__(self) -> None:
        self._config: dict[str, str] = {}

    def get_config_value(self, key: str) -> str | None:
        return self._config.get(key)

    def set_config_value(self, key: str, value: str) -> None:
        self._config[key] = value


_repo_protocol_check: ConfigRepositoryPort
_repo_protocol_check = InMemoryConfigRepository()
