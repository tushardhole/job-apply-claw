from __future__ import annotations

import os

import pytest

from domain.models import CommonAnswers, ResumeData, UserProfile
from domain.ports import OnboardingRepositoryPort
from infra.persistence import SQLiteOnboardingRepository


@pytest.fixture()
def repo(tmp_path: str) -> SQLiteOnboardingRepository:
    db = os.path.join(tmp_path, "onboarding.db")
    r = SQLiteOnboardingRepository(db_path=db)
    yield r
    r.close()


# -- protocol conformance --------------------------------------------------

def test_conforms_to_onboarding_repository_port(repo: SQLiteOnboardingRepository) -> None:
    assert isinstance(repo, OnboardingRepositoryPort)


# -- user profile -----------------------------------------------------------

def test_get_user_profile_returns_none_initially(repo: SQLiteOnboardingRepository) -> None:
    assert repo.get_user_profile() is None


def test_save_and_get_user_profile(repo: SQLiteOnboardingRepository) -> None:
    profile = UserProfile(
        full_name="Ada Lovelace",
        email="ada@example.com",
        phone="+1-555-0100",
        address="123 Main St",
    )
    repo.save_user_profile(profile)
    loaded = repo.get_user_profile()
    assert loaded == profile


def test_save_user_profile_overwrites(repo: SQLiteOnboardingRepository) -> None:
    repo.save_user_profile(UserProfile(full_name="V1", email="v1@x.com"))
    repo.save_user_profile(UserProfile(full_name="V2", email="v2@x.com"))
    loaded = repo.get_user_profile()
    assert loaded is not None
    assert loaded.full_name == "V2"
    assert loaded.email == "v2@x.com"


def test_user_profile_with_nulls(repo: SQLiteOnboardingRepository) -> None:
    profile = UserProfile(full_name="Test", email="t@x.com")
    repo.save_user_profile(profile)
    loaded = repo.get_user_profile()
    assert loaded is not None
    assert loaded.phone is None
    assert loaded.address is None


# -- resume data ------------------------------------------------------------

def test_get_resume_data_returns_none_initially(repo: SQLiteOnboardingRepository) -> None:
    assert repo.get_resume_data() is None


def test_save_and_get_resume_data(repo: SQLiteOnboardingRepository) -> None:
    data = ResumeData(
        primary_resume_path="/home/user/resume.pdf",
        skills=("python", "sql"),
        cover_letter_paths=("/home/user/cover.docx",),
    )
    repo.save_resume_data(data)
    loaded = repo.get_resume_data()
    assert loaded == data


def test_save_resume_data_overwrites(repo: SQLiteOnboardingRepository) -> None:
    repo.save_resume_data(ResumeData(primary_resume_path="/v1.pdf"))
    repo.save_resume_data(
        ResumeData(primary_resume_path="/v2.pdf", skills=("java",))
    )
    loaded = repo.get_resume_data()
    assert loaded is not None
    assert loaded.primary_resume_path == "/v2.pdf"
    assert loaded.skills == ("java",)


def test_resume_data_empty_sequences(repo: SQLiteOnboardingRepository) -> None:
    data = ResumeData(primary_resume_path="/resume.pdf")
    repo.save_resume_data(data)
    loaded = repo.get_resume_data()
    assert loaded is not None
    assert loaded.additional_resume_paths == ()
    assert loaded.cover_letter_paths == ()
    assert loaded.skills == ()


# -- common answers ---------------------------------------------------------

def test_get_common_answers_empty_initially(repo: SQLiteOnboardingRepository) -> None:
    answers = repo.get_common_answers()
    assert answers.answers == {}


def test_save_and_get_common_answers(repo: SQLiteOnboardingRepository) -> None:
    answers = CommonAnswers(
        answers={"salary_expectation": "120000", "start_date": "immediately"}
    )
    repo.save_common_answers(answers)
    loaded = repo.get_common_answers()
    assert loaded.get("salary_expectation") == "120000"
    assert loaded.get("start_date") == "immediately"


def test_save_common_answers_replaces_all(repo: SQLiteOnboardingRepository) -> None:
    repo.save_common_answers(CommonAnswers(answers={"a": "1", "b": "2"}))
    repo.save_common_answers(CommonAnswers(answers={"c": "3"}))
    loaded = repo.get_common_answers()
    assert loaded.answers == {"c": "3"}


# -- config values ----------------------------------------------------------

def test_get_config_value_returns_none_for_missing(repo: SQLiteOnboardingRepository) -> None:
    assert repo.get_config_value("nonexistent") is None


def test_set_and_get_config_value(repo: SQLiteOnboardingRepository) -> None:
    repo.set_config_value("BOT_TOKEN", "tok-123")
    assert repo.get_config_value("BOT_TOKEN") == "tok-123"


def test_set_config_value_overwrites(repo: SQLiteOnboardingRepository) -> None:
    repo.set_config_value("key", "old")
    repo.set_config_value("key", "new")
    assert repo.get_config_value("key") == "new"


def test_multiple_config_values(repo: SQLiteOnboardingRepository) -> None:
    repo.set_config_value("key_a", "alpha")
    repo.set_config_value("key_b", "beta")
    assert repo.get_config_value("key_a") == "alpha"
    assert repo.get_config_value("key_b") == "beta"


# -- persistence across reopens --------------------------------------------

def test_data_persists_across_reopens(tmp_path: str) -> None:
    db = os.path.join(tmp_path, "persist.db")

    repo1 = SQLiteOnboardingRepository(db_path=db)
    repo1.save_user_profile(UserProfile(full_name="Persist", email="p@x.com"))
    repo1.set_config_value("token", "abc")
    repo1.save_common_answers(CommonAnswers(answers={"q": "a"}))
    repo1.save_resume_data(ResumeData(primary_resume_path="/r.pdf", skills=("go",)))
    repo1.close()

    repo2 = SQLiteOnboardingRepository(db_path=db)
    assert repo2.get_user_profile() == UserProfile(full_name="Persist", email="p@x.com")
    assert repo2.get_config_value("token") == "abc"
    assert repo2.get_common_answers().get("q") == "a"
    resume = repo2.get_resume_data()
    assert resume is not None
    assert resume.primary_resume_path == "/r.pdf"
    assert resume.skills == ("go",)
    repo2.close()


# -- multi-profile isolation -----------------------------------------------

def test_profiles_are_isolated(tmp_path: str) -> None:
    """Two profiles sharing the same DB file see their own data only."""
    db = os.path.join(tmp_path, "multi.db")

    alice = SQLiteOnboardingRepository(db_path=db, profile_id="alice")
    bob = SQLiteOnboardingRepository(db_path=db, profile_id="bob")

    alice.save_user_profile(UserProfile(full_name="Alice", email="alice@x.com"))
    bob.save_user_profile(UserProfile(full_name="Bob", email="bob@x.com"))

    assert alice.get_user_profile().full_name == "Alice"
    assert bob.get_user_profile().full_name == "Bob"

    alice.set_config_value("theme", "dark")
    bob.set_config_value("theme", "light")
    assert alice.get_config_value("theme") == "dark"
    assert bob.get_config_value("theme") == "light"

    alice.save_common_answers(CommonAnswers(answers={"salary": "100k"}))
    bob.save_common_answers(CommonAnswers(answers={"salary": "200k"}))
    assert alice.get_common_answers().get("salary") == "100k"
    assert bob.get_common_answers().get("salary") == "200k"

    alice.save_resume_data(ResumeData(primary_resume_path="/alice/resume.pdf"))
    bob.save_resume_data(ResumeData(primary_resume_path="/bob/resume.pdf"))
    assert alice.get_resume_data().primary_resume_path == "/alice/resume.pdf"
    assert bob.get_resume_data().primary_resume_path == "/bob/resume.pdf"

    alice.close()
    bob.close()


def test_default_profile_id_is_used_when_not_specified(tmp_path: str) -> None:
    db = os.path.join(tmp_path, "default.db")
    repo1 = SQLiteOnboardingRepository(db_path=db)
    repo1.save_user_profile(UserProfile(full_name="Default", email="d@x.com"))
    repo1.close()

    repo2 = SQLiteOnboardingRepository(db_path=db)
    assert repo2.get_user_profile().full_name == "Default"
    repo2.close()
