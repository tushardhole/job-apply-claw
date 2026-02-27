"""Step definitions for config validation BDD scenarios."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from pytest_bdd import given, when, then, scenarios, parsers

from infra.config import FileSystemConfigProvider

scenarios("../features/config_validation.feature")


def _valid_config() -> dict:
    return {
        "BOT_TOKEN": "tok-123",
        "TELEGRAM_CHAT_ID": "999",
        "OPENAI_KEY": "sk-abc",
        "OPENAI_BASE_URL": "https://api.example.com/v1",
    }


def _valid_profile() -> dict:
    return {"name": "Jane", "email": "jane@test.com"}


def _place_files(base: Path, *, config: bool = True, profile: bool = True, resume: bool = True, cover_letter: bool = True) -> None:
    if config:
        (base / "config.json").write_text(json.dumps(_valid_config()))
    if profile:
        (base / "profile.json").write_text(json.dumps(_valid_profile()))
    if resume:
        d = base / "resume"
        d.mkdir(parents=True, exist_ok=True)
        (d / "resume.pdf").write_bytes(b"%PDF-1.4 fake")
    if cover_letter:
        d = base / "cover_letter"
        d.mkdir(parents=True, exist_ok=True)
        (d / "cover_letter.pdf").write_bytes(b"%PDF-1.4 fake")


@pytest.fixture()
def config_ctx(tmp_path: Path) -> dict:
    return {"tmp_path": tmp_path, "errors": []}


@given("a complete config folder with all required files", target_fixture="config_ctx")
def given_complete(tmp_path: Path) -> dict:
    _place_files(tmp_path)
    return {"tmp_path": tmp_path, "errors": []}


@given("a config folder without config.json", target_fixture="config_ctx")
def given_no_config_json(tmp_path: Path) -> dict:
    _place_files(tmp_path, config=False)
    return {"tmp_path": tmp_path, "errors": []}


@given("a config folder without profile.json", target_fixture="config_ctx")
def given_no_profile(tmp_path: Path) -> dict:
    _place_files(tmp_path, profile=False)
    return {"tmp_path": tmp_path, "errors": []}


@given("a config folder without resume PDF", target_fixture="config_ctx")
def given_no_resume(tmp_path: Path) -> dict:
    _place_files(tmp_path, resume=False)
    return {"tmp_path": tmp_path, "errors": []}


@given("a config folder with invalid JSON in config.json", target_fixture="config_ctx")
def given_invalid_json(tmp_path: Path) -> dict:
    _place_files(tmp_path)
    (tmp_path / "config.json").write_text("{bad")
    return {"tmp_path": tmp_path, "errors": []}


@given(
    parsers.parse('a config folder with config.json missing "{key}"'),
    target_fixture="config_ctx",
)
def given_missing_key(tmp_path: Path, key: str) -> dict:
    cfg = _valid_config()
    del cfg[key]
    _place_files(tmp_path)
    (tmp_path / "config.json").write_text(json.dumps(cfg))
    return {"tmp_path": tmp_path, "errors": []}


@when("the config is validated")
def when_validate(config_ctx: dict) -> None:
    provider = FileSystemConfigProvider(str(config_ctx["tmp_path"]))
    config_ctx["errors"] = provider.validate()


@then("validation passes with no errors")
def then_no_errors(config_ctx: dict) -> None:
    assert config_ctx["errors"] == []


@then(parsers.parse('validation reports an error containing "{text}"'))
def then_error_contains(config_ctx: dict, text: str) -> None:
    assert any(text in e for e in config_ctx["errors"]), (
        f"Expected error containing '{text}', got: {config_ctx['errors']}"
    )
