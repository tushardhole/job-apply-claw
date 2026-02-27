from __future__ import annotations

import sqlite3
from typing import Sequence

from domain.models import JobApplicationRecord, JobApplicationStatus
from ._datetime import dt_to_iso, iso_to_dt


class SQLiteJobApplicationRepository:
    """
    SQLite-backed implementation of ``JobApplicationRepositoryPort``.

    Stores job application records with full lifecycle tracking.
    """

    _SCHEMA_SQL = """\
    CREATE TABLE IF NOT EXISTS applied_jobs (
        id             TEXT PRIMARY KEY,
        company_name   TEXT NOT NULL,
        job_title      TEXT NOT NULL,
        job_url        TEXT NOT NULL,
        status         TEXT NOT NULL,
        applied_at     TEXT,
        failure_reason TEXT,
        debug_run_id   TEXT
    );
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        self._conn = sqlite3.connect(db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(self._SCHEMA_SQL)

    def __enter__(self) -> "SQLiteJobApplicationRepository":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def add(self, record: JobApplicationRecord) -> None:
        self._conn.execute(
            "INSERT INTO applied_jobs "
            "(id, company_name, job_title, job_url, status, applied_at, failure_reason, debug_run_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            self._record_to_row(record),
        )
        self._conn.commit()

    def update(self, record: JobApplicationRecord) -> None:
        self._conn.execute(
            "UPDATE applied_jobs SET "
            "company_name=?, job_title=?, job_url=?, status=?, "
            "applied_at=?, failure_reason=?, debug_run_id=? "
            "WHERE id=?",
            (
                record.company_name,
                record.job_title,
                record.job_url,
                record.status.value,
                dt_to_iso(record.applied_at),
                record.failure_reason,
                record.debug_run_id,
                record.id,
            ),
        )
        self._conn.commit()

    def get(self, record_id: str) -> JobApplicationRecord | None:
        row = self._conn.execute(
            "SELECT id, company_name, job_title, job_url, status, "
            "applied_at, failure_reason, debug_run_id "
            "FROM applied_jobs WHERE id = ?",
            (record_id,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_record(row)

    def list_all(self) -> Sequence[JobApplicationRecord]:
        rows = self._conn.execute(
            "SELECT id, company_name, job_title, job_url, status, "
            "applied_at, failure_reason, debug_run_id "
            "FROM applied_jobs ORDER BY applied_at DESC",
        ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def close(self) -> None:
        self._conn.close()

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _record_to_row(
        r: JobApplicationRecord,
    ) -> tuple[str, str, str, str, str, str | None, str | None, str | None]:
        return (
            r.id,
            r.company_name,
            r.job_title,
            r.job_url,
            r.status.value,
            dt_to_iso(r.applied_at),
            r.failure_reason,
            r.debug_run_id,
        )

    @staticmethod
    def _row_to_record(row: tuple[object, ...]) -> JobApplicationRecord:
        return JobApplicationRecord(
            id=str(row[0]),
            company_name=str(row[1]),
            job_title=str(row[2]),
            job_url=str(row[3]),
            status=JobApplicationStatus(row[4]),
            applied_at=iso_to_dt(row[5] if isinstance(row[5], str) else None),
            failure_reason=row[6] if isinstance(row[6], str) else None,
            debug_run_id=row[7] if isinstance(row[7], str) else None,
        )
