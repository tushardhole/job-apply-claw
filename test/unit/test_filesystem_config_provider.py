from __future__ import annotations

import json
from pathlib import Path

import pytest

from domain.models import AppConfig, UserProfile
from infra.config import FileSystemConfigProvider


def _write_config(base: Path, data: dict) -> None:
    (base / "config.json").write_text(json.dumps(data))


def _write_profile(base: Path, data: dict) -> None:
    (base / "profile.json").write_text(json.dumps(data))


def _place_resume(base: Path) -> None:
    d = base / "resume"
    d.mkdir(parents=True, exist_ok=True)
    (d / "resume.pdf").write_bytes(b"%PDF-1.4 fake")


def _place_cover_letter(base: Path) -> None:
    d = base / "cover_letter"
    d.mkdir(parents=True, exist_ok=True)
    (d / "cover_letter.pdf").write_bytes(b"%PDF-1.4 fake")


def _valid_config() -> dict:
    return {
        "BOT_TOKEN": "tok-123",
        "TELEGRAM_CHAT_ID": "999",
        "OPENAI_KEY": "sk-abc",
        "OPENAI_BASE_URL": "https://api.example.com/v1",
        "debug_mode": True,
    }


def _valid_profile() -> dict:
    return {
        "name": "Jane",
        "email": "jane@test.com",
        "phone": "+1234",
        "address": "123 Main St",
        "skills": ["Python", "Go"],
        "linkedin_url": "https://linkedin.com/in/jane",
    }


def _setup_valid(tmp_path: Path) -> FileSystemConfigProvider:
    _write_config(tmp_path, _valid_config())
    _write_profile(tmp_path, _valid_profile())
    _place_resume(tmp_path)
    _place_cover_letter(tmp_path)
    return FileSystemConfigProvider(str(tmp_path))


# -- validate() tests ------------------------------------------------------


def test_validate_passes_with_complete_config(tmp_path: Path) -> None:
    provider = _setup_valid(tmp_path)
    assert provider.validate() == []


def test_validate_reports_missing_config_json(tmp_path: Path) -> None:
    _write_profile(tmp_path, _valid_profile())
    _place_resume(tmp_path)
    _place_cover_letter(tmp_path)
    provider = FileSystemConfigProvider(str(tmp_path))

    errors = provider.validate()
    assert any("config.json" in e for e in errors)


def test_validate_reports_missing_profile_json(tmp_path: Path) -> None:
    _write_config(tmp_path, _valid_config())
    _place_resume(tmp_path)
    _place_cover_letter(tmp_path)
    provider = FileSystemConfigProvider(str(tmp_path))

    errors = provider.validate()
    assert any("profile.json" in e for e in errors)


def test_validate_reports_invalid_json(tmp_path: Path) -> None:
    (tmp_path / "config.json").write_text("{bad json")
    _write_profile(tmp_path, _valid_profile())
    _place_resume(tmp_path)
    _place_cover_letter(tmp_path)
    provider = FileSystemConfigProvider(str(tmp_path))

    errors = provider.validate()
    assert any("Cannot read" in e for e in errors)


def test_validate_reports_missing_keys(tmp_path: Path) -> None:
    _write_config(tmp_path, {"BOT_TOKEN": "x"})
    _write_profile(tmp_path, {"name": "X"})
    _place_resume(tmp_path)
    _place_cover_letter(tmp_path)
    provider = FileSystemConfigProvider(str(tmp_path))

    errors = provider.validate()
    assert any("config.json missing keys" in e for e in errors)
    assert any("profile.json missing keys" in e for e in errors)


def test_validate_reports_missing_resume(tmp_path: Path) -> None:
    _write_config(tmp_path, _valid_config())
    _write_profile(tmp_path, _valid_profile())
    _place_cover_letter(tmp_path)
    provider = FileSystemConfigProvider(str(tmp_path))

    errors = provider.validate()
    assert any("Resume not found" in e for e in errors)


def test_validate_reports_missing_cover_letter(tmp_path: Path) -> None:
    _write_config(tmp_path, _valid_config())
    _write_profile(tmp_path, _valid_profile())
    _place_resume(tmp_path)
    provider = FileSystemConfigProvider(str(tmp_path))

    errors = provider.validate()
    assert any("Cover letter not found" in e for e in errors)


# -- get_config() tests ----------------------------------------------------


def test_get_config_returns_app_config(tmp_path: Path) -> None:
    provider = _setup_valid(tmp_path)
    cfg = provider.get_config()

    assert isinstance(cfg, AppConfig)
    assert cfg.bot_token == "tok-123"
    assert cfg.telegram_chat_id == "999"
    assert cfg.openai_key == "sk-abc"
    assert cfg.openai_base_url == "https://api.example.com/v1"
    assert cfg.debug_mode is True


def test_get_config_defaults_debug_mode_to_false(tmp_path: Path) -> None:
    config = _valid_config()
    del config["debug_mode"]
    _write_config(tmp_path, config)
    _write_profile(tmp_path, _valid_profile())
    _place_resume(tmp_path)
    _place_cover_letter(tmp_path)
    provider = FileSystemConfigProvider(str(tmp_path))

    assert provider.get_config().debug_mode is False


# -- get_profile() tests ---------------------------------------------------


def test_get_profile_returns_user_profile(tmp_path: Path) -> None:
    provider = _setup_valid(tmp_path)
    profile = provider.get_profile()

    assert isinstance(profile, UserProfile)
    assert profile.full_name == "Jane"
    assert profile.email == "jane@test.com"
    assert profile.phone == "+1234"
    assert profile.address == "123 Main St"


# -- get_resume_data() tests -----------------------------------------------


def test_get_resume_data_includes_paths_and_skills(tmp_path: Path) -> None:
    provider = _setup_valid(tmp_path)
    rd = provider.get_resume_data()

    assert rd.primary_resume_path.endswith("resume.pdf")
    assert rd.cover_letter_paths[0].endswith("cover_letter.pdf")
    assert "Python" in rd.skills


# -- hot-reload tests ------------------------------------------------------


def test_hot_reload_picks_up_config_changes(tmp_path: Path) -> None:
    provider = _setup_valid(tmp_path)
    assert provider.get_config().debug_mode is True

    updated = _valid_config()
    updated["debug_mode"] = False
    _write_config(tmp_path, updated)

    assert provider.get_config().debug_mode is False


def test_hot_reload_picks_up_profile_changes(tmp_path: Path) -> None:
    provider = _setup_valid(tmp_path)
    assert provider.get_profile().full_name == "Jane"

    updated = _valid_profile()
    updated["name"] = "Jane Doe"
    _write_profile(tmp_path, updated)

    assert provider.get_profile().full_name == "Jane Doe"
