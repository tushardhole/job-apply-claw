from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest

from domain.models import AccountCredential
from domain.ports import CredentialRepositoryPort
from infra.persistence import SQLiteCredentialRepository


@pytest.fixture()
def repo(tmp_path: str) -> SQLiteCredentialRepository:
    db = os.path.join(tmp_path, "creds.db")
    r = SQLiteCredentialRepository(db_path=db)
    yield r
    r.close()


def _make_credential(**overrides: object) -> AccountCredential:
    now = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    defaults: dict = dict(
        id="cred-1",
        portal="greenhouse",
        tenant="company-a",
        email="user@example.com",
        password="s3cret",
        created_at=now,
        updated_at=now,
    )
    defaults.update(overrides)
    return AccountCredential(**defaults)


# -- protocol conformance --------------------------------------------------

def test_conforms_to_credential_repository_port(
    repo: SQLiteCredentialRepository,
) -> None:
    assert isinstance(repo, CredentialRepositoryPort)


# -- upsert / get ----------------------------------------------------------

def test_list_all_empty_initially(repo: SQLiteCredentialRepository) -> None:
    assert repo.list_all() == []


def test_upsert_and_get(repo: SQLiteCredentialRepository) -> None:
    cred = _make_credential()
    repo.upsert(cred)
    loaded = repo.get("greenhouse", "company-a", "user@example.com")
    assert loaded is not None
    assert loaded.id == "cred-1"
    assert loaded.password == "s3cret"
    assert loaded.portal == "greenhouse"
    assert loaded.tenant == "company-a"


def test_get_returns_none_for_missing(repo: SQLiteCredentialRepository) -> None:
    assert repo.get("nope", "nope", "nope@x.com") is None


def test_upsert_updates_existing(repo: SQLiteCredentialRepository) -> None:
    now = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    later = datetime(2025, 7, 1, 12, 0, 0, tzinfo=timezone.utc)
    repo.upsert(_make_credential())
    repo.upsert(
        _make_credential(
            id="cred-1-updated",
            password="new-secret",
            updated_at=later,
        )
    )
    loaded = repo.get("greenhouse", "company-a", "user@example.com")
    assert loaded is not None
    assert loaded.id == "cred-1-updated"
    assert loaded.password == "new-secret"
    assert loaded.updated_at == later


# -- list_all ---------------------------------------------------------------

def test_list_all_returns_all(repo: SQLiteCredentialRepository) -> None:
    repo.upsert(_make_credential())
    repo.upsert(
        _make_credential(
            id="cred-2",
            portal="workday",
            tenant="company-b",
            email="other@example.com",
        )
    )
    creds = repo.list_all()
    assert len(creds) == 2
    ids = {c.id for c in creds}
    assert ids == {"cred-1", "cred-2"}


# -- timestamps roundtrip ---------------------------------------------------

def test_timestamps_survive_roundtrip(repo: SQLiteCredentialRepository) -> None:
    ts = datetime(2025, 3, 14, 9, 26, 53, tzinfo=timezone.utc)
    cred = _make_credential(created_at=ts, updated_at=ts)
    repo.upsert(cred)
    loaded = repo.get("greenhouse", "company-a", "user@example.com")
    assert loaded is not None
    assert loaded.created_at == ts
    assert loaded.updated_at == ts


# -- persistence across reopens --------------------------------------------

def test_data_persists_across_reopens(tmp_path: str) -> None:
    db = os.path.join(tmp_path, "creds_persist.db")

    repo1 = SQLiteCredentialRepository(db_path=db)
    repo1.upsert(_make_credential())
    repo1.close()

    repo2 = SQLiteCredentialRepository(db_path=db)
    loaded = repo2.get("greenhouse", "company-a", "user@example.com")
    assert loaded is not None
    assert loaded.password == "s3cret"
    repo2.close()


def test_context_manager_support(tmp_path: str) -> None:
    db = os.path.join(tmp_path, "ctx_creds.db")
    with SQLiteCredentialRepository(db_path=db) as repo1:
        repo1.upsert(_make_credential())
    with SQLiteCredentialRepository(db_path=db) as repo2:
        loaded = repo2.get("greenhouse", "company-a", "user@example.com")
        assert loaded is not None
