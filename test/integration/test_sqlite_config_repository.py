from __future__ import annotations

import os

import pytest

from domain import ConfigRepositoryPort
from infra.persistence import SQLiteConfigRepository


@pytest.fixture()
def repo(tmp_path: str) -> SQLiteConfigRepository:
    db = os.path.join(tmp_path, "config.db")
    r = SQLiteConfigRepository(db_path=db)
    yield r
    r.close()


def test_conforms_to_config_repository_port(repo: SQLiteConfigRepository) -> None:
    assert isinstance(repo, ConfigRepositoryPort)


def test_get_config_value_returns_none_for_missing(repo: SQLiteConfigRepository) -> None:
    assert repo.get_config_value("nonexistent") is None


def test_set_and_get_config_value(repo: SQLiteConfigRepository) -> None:
    repo.set_config_value("BOT_TOKEN", "tok-123")
    assert repo.get_config_value("BOT_TOKEN") == "tok-123"


def test_set_config_value_overwrites(repo: SQLiteConfigRepository) -> None:
    repo.set_config_value("key", "old")
    repo.set_config_value("key", "new")
    assert repo.get_config_value("key") == "new"


def test_multiple_config_values(repo: SQLiteConfigRepository) -> None:
    repo.set_config_value("key_a", "alpha")
    repo.set_config_value("key_b", "beta")
    assert repo.get_config_value("key_a") == "alpha"
    assert repo.get_config_value("key_b") == "beta"


def test_profiles_are_isolated(tmp_path: str) -> None:
    db = os.path.join(tmp_path, "multi_config.db")
    alice = SQLiteConfigRepository(db_path=db, profile_id="alice")
    bob = SQLiteConfigRepository(db_path=db, profile_id="bob")
    alice.set_config_value("theme", "dark")
    bob.set_config_value("theme", "light")
    assert alice.get_config_value("theme") == "dark"
    assert bob.get_config_value("theme") == "light"
    alice.close()
    bob.close()


def test_data_persists_across_reopens(tmp_path: str) -> None:
    db = os.path.join(tmp_path, "persist_config.db")
    with SQLiteConfigRepository(db_path=db) as repo1:
        repo1.set_config_value("token", "abc")
    with SQLiteConfigRepository(db_path=db) as repo2:
        assert repo2.get_config_value("token") == "abc"
