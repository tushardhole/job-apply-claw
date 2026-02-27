from __future__ import annotations

import sqlite3

_DEFAULT_PROFILE_ID = "default"


class SQLiteConfigRepository:
    """SQLite-backed implementation of ``ConfigRepositoryPort``."""

    _SCHEMA_SQL = """\
    CREATE TABLE IF NOT EXISTS config (
        profile_id TEXT NOT NULL,
        key        TEXT NOT NULL,
        value      TEXT NOT NULL,
        PRIMARY KEY (profile_id, key)
    );
    """

    def __init__(
        self,
        db_path: str = ":memory:",
        profile_id: str = _DEFAULT_PROFILE_ID,
    ) -> None:
        self._conn = sqlite3.connect(db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(self._SCHEMA_SQL)
        self._profile_id = profile_id

    def __enter__(self) -> "SQLiteConfigRepository":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def get_config_value(self, key: str) -> str | None:
        row = self._conn.execute(
            "SELECT value FROM config WHERE profile_id = ? AND key = ?",
            (self._profile_id, key),
        ).fetchone()
        return row[0] if row else None

    def set_config_value(self, key: str, value: str) -> None:
        self._conn.execute(
            "INSERT INTO config (profile_id, key, value) VALUES (?, ?, ?) "
            "ON CONFLICT(profile_id, key) DO UPDATE SET value=excluded.value",
            (self._profile_id, key, value),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
