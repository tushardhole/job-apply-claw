from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Sequence

from domain.models import JobApplicationRecord, JobApplicationStatus


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
                _dt_to_iso(record.applied_at),
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
    def _record_to_row(r: JobApplicationRecord) -> tuple[str, ...]:
        return (
            r.id,
            r.company_name,
            r.job_title,
            r.job_url,
            r.status.value,
            _dt_to_iso(r.applied_at),
            r.failure_reason or "",
            r.debug_run_id or "",
        )

    @staticmethod
    def _row_to_record(row: tuple[object, ...]) -> JobApplicationRecord:
        return JobApplicationRecord(
            id=str(row[0]),
            company_name=str(row[1]),
            job_title=str(row[2]),
            job_url=str(row[3]),
            status=JobApplicationStatus(row[4]),
            applied_at=_iso_to_dt(str(row[5])) if row[5] else None,
            failure_reason=str(row[6]) if row[6] else None,
            debug_run_id=str(row[7]) if row[7] else None,
        )


def _dt_to_iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _iso_to_dt(s: str) -> datetime | None:
    if not s:
        return None
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt
