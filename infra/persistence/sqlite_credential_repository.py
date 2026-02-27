from __future__ import annotations

import sqlite3
from typing import Sequence

from domain.models import AccountCredential
from ._datetime import dt_to_iso, iso_to_dt


class SQLiteCredentialRepository:
    """
    SQLite-backed implementation of ``CredentialRepositoryPort``.

    Stores job board account credentials. Passwords are stored as plain
    text in this implementation; a production deployment should layer
    encryption on top (e.g. via an ``EncryptionPort``).
    """

    _SCHEMA_SQL = """\
    CREATE TABLE IF NOT EXISTS credentials (
        id         TEXT PRIMARY KEY,
        portal     TEXT NOT NULL,
        tenant     TEXT NOT NULL,
        email      TEXT NOT NULL,
        password   TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE (portal, tenant, email)
    );
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        self._conn = sqlite3.connect(db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(self._SCHEMA_SQL)

    def __enter__(self) -> "SQLiteCredentialRepository":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def upsert(self, credential: AccountCredential) -> None:
        self._conn.execute(
            "INSERT INTO credentials "
            "(id, portal, tenant, email, password, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(portal, tenant, email) DO UPDATE SET "
            "id=excluded.id, password=excluded.password, updated_at=excluded.updated_at",
            (
                credential.id,
                credential.portal,
                credential.tenant,
                credential.email,
                credential.password,
                dt_to_iso(credential.created_at),
                dt_to_iso(credential.updated_at),
            ),
        )
        self._conn.commit()

    def get(
        self,
        portal: str,
        tenant: str,
        email: str,
    ) -> AccountCredential | None:
        row = self._conn.execute(
            "SELECT id, portal, tenant, email, password, created_at, updated_at "
            "FROM credentials WHERE portal = ? AND tenant = ? AND email = ?",
            (portal, tenant, email),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_credential(row)

    def list_all(self) -> Sequence[AccountCredential]:
        rows = self._conn.execute(
            "SELECT id, portal, tenant, email, password, created_at, updated_at "
            "FROM credentials ORDER BY updated_at DESC",
        ).fetchall()
        return [self._row_to_credential(r) for r in rows]

    def close(self) -> None:
        self._conn.close()

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _row_to_credential(row: tuple[object, ...]) -> AccountCredential:
        created_at = iso_to_dt(str(row[5]))
        updated_at = iso_to_dt(str(row[6]))
        if created_at is None or updated_at is None:
            raise ValueError("Credential timestamps must not be null")
        return AccountCredential(
            id=str(row[0]),
            portal=str(row[1]),
            tenant=str(row[2]),
            email=str(row[3]),
            password=str(row[4]),
            created_at=created_at,
            updated_at=updated_at,
        )
