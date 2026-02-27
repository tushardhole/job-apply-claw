from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest

from domain.models import JobApplicationRecord, JobApplicationStatus
from domain.ports import JobApplicationRepositoryPort
from infra.persistence import SQLiteJobApplicationRepository


@pytest.fixture()
def repo(tmp_path: str) -> SQLiteJobApplicationRepository:
    db = os.path.join(tmp_path, "jobs.db")
    r = SQLiteJobApplicationRepository(db_path=db)
    yield r
    r.close()


def _make_record(**overrides: object) -> JobApplicationRecord:
    defaults: dict = dict(
        id="rec-1",
        company_name="Acme Inc",
        job_title="Software Engineer",
        job_url="https://acme.com/jobs/1",
        status=JobApplicationStatus.PENDING,
    )
    defaults.update(overrides)
    return JobApplicationRecord(**defaults)


# -- protocol conformance --------------------------------------------------

def test_conforms_to_job_application_repository_port(
    repo: SQLiteJobApplicationRepository,
) -> None:
    assert isinstance(repo, JobApplicationRepositoryPort)


# -- add / get --------------------------------------------------------------

def test_list_all_empty_initially(repo: SQLiteJobApplicationRepository) -> None:
    assert repo.list_all() == []


def test_add_and_get(repo: SQLiteJobApplicationRepository) -> None:
    record = _make_record()
    repo.add(record)
    loaded = repo.get("rec-1")
    assert loaded is not None
    assert loaded.id == "rec-1"
    assert loaded.company_name == "Acme Inc"
    assert loaded.status is JobApplicationStatus.PENDING


def test_get_returns_none_for_missing(repo: SQLiteJobApplicationRepository) -> None:
    assert repo.get("nonexistent") is None


def test_add_with_applied_at_timestamp(repo: SQLiteJobApplicationRepository) -> None:
    ts = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    record = _make_record(
        status=JobApplicationStatus.APPLIED,
        applied_at=ts,
    )
    repo.add(record)
    loaded = repo.get("rec-1")
    assert loaded is not None
    assert loaded.applied_at == ts


def test_add_with_failure_reason(repo: SQLiteJobApplicationRepository) -> None:
    record = _make_record(
        status=JobApplicationStatus.FAILED,
        failure_reason="Captcha unresolvable",
    )
    repo.add(record)
    loaded = repo.get("rec-1")
    assert loaded is not None
    assert loaded.failure_reason == "Captcha unresolvable"


def test_add_with_debug_run_id(repo: SQLiteJobApplicationRepository) -> None:
    record = _make_record(debug_run_id="run-42")
    repo.add(record)
    loaded = repo.get("rec-1")
    assert loaded is not None
    assert loaded.debug_run_id == "run-42"


def test_none_and_empty_string_are_not_collapsed(
    repo: SQLiteJobApplicationRepository,
) -> None:
    repo.add(_make_record(id="rec-none", failure_reason=None, debug_run_id=None))
    repo.add(_make_record(id="rec-empty", failure_reason="", debug_run_id=""))
    rec_none = repo.get("rec-none")
    rec_empty = repo.get("rec-empty")
    assert rec_none is not None and rec_empty is not None
    assert rec_none.failure_reason is None
    assert rec_none.debug_run_id is None
    assert rec_empty.failure_reason == ""
    assert rec_empty.debug_run_id == ""


# -- update -----------------------------------------------------------------

def test_update_status(repo: SQLiteJobApplicationRepository) -> None:
    repo.add(_make_record())
    updated = JobApplicationRecord(
        id="rec-1",
        company_name="Acme Inc",
        job_title="Software Engineer",
        job_url="https://acme.com/jobs/1",
        status=JobApplicationStatus.APPLIED,
        applied_at=datetime(2025, 7, 1, tzinfo=timezone.utc),
    )
    repo.update(updated)
    loaded = repo.get("rec-1")
    assert loaded is not None
    assert loaded.status is JobApplicationStatus.APPLIED
    assert loaded.applied_at == datetime(2025, 7, 1, tzinfo=timezone.utc)


# -- list_all ---------------------------------------------------------------

def test_list_all_returns_all_records(repo: SQLiteJobApplicationRepository) -> None:
    ts1 = datetime(2025, 6, 1, tzinfo=timezone.utc)
    ts2 = datetime(2025, 7, 1, tzinfo=timezone.utc)
    repo.add(_make_record(id="rec-1", applied_at=ts1))
    repo.add(
        _make_record(
            id="rec-2",
            company_name="Other Corp",
            job_title="Data Engineer",
            job_url="https://other.com/2",
            applied_at=ts2,
        )
    )
    records = repo.list_all()
    assert len(records) == 2
    ids = {r.id for r in records}
    assert ids == {"rec-1", "rec-2"}


# -- persistence across reopens --------------------------------------------

def test_data_persists_across_reopens(tmp_path: str) -> None:
    db = os.path.join(tmp_path, "jobs_persist.db")

    repo1 = SQLiteJobApplicationRepository(db_path=db)
    repo1.add(_make_record())
    repo1.close()

    repo2 = SQLiteJobApplicationRepository(db_path=db)
    loaded = repo2.get("rec-1")
    assert loaded is not None
    assert loaded.company_name == "Acme Inc"
    repo2.close()


def test_context_manager_support(tmp_path: str) -> None:
    db = os.path.join(tmp_path, "ctx_jobs.db")
    with SQLiteJobApplicationRepository(db_path=db) as repo1:
        repo1.add(_make_record())
    with SQLiteJobApplicationRepository(db_path=db) as repo2:
        assert repo2.get("rec-1") is not None


# -- duplicate add raises ---------------------------------------------------

def test_add_duplicate_raises(repo: SQLiteJobApplicationRepository) -> None:
    repo.add(_make_record())
    with pytest.raises(Exception):
        repo.add(_make_record())
