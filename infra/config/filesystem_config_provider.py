from __future__ import annotations

import json
from pathlib import Path

from domain.models import AppConfig, ResumeData, UserProfile


_REQUIRED_CONFIG_KEYS = {"BOT_TOKEN", "TELEGRAM_CHAT_ID", "OPENAI_KEY", "OPENAI_BASE_URL"}
_REQUIRED_PROFILE_KEYS = {"name", "email"}


class FileSystemConfigProvider:
    """Reads config.json and profile.json from a config directory.

    Every public method re-reads from disk so that edits
    to the JSON files take effect without restarting the app.
    """

    def __init__(self, config_dir: str) -> None:
        self._config_dir = Path(config_dir)

    def validate(self) -> list[str]:
        errors: list[str] = []
        config_path = self._config_dir / "config.json"
        profile_path = self._config_dir / "profile.json"

        errors.extend(self._validate_json_file(config_path, _REQUIRED_CONFIG_KEYS))
        errors.extend(self._validate_json_file(profile_path, _REQUIRED_PROFILE_KEYS))

        resume = self._config_dir / "resume" / "resume.pdf"
        if not resume.is_file():
            errors.append(f"Resume not found at {resume}")

        cover_letter = self._config_dir / "cover_letter" / "cover_letter.pdf"
        if not cover_letter.is_file():
            errors.append(f"Cover letter not found at {cover_letter}")

        return errors

    def get_config(self) -> AppConfig:
        data = self._read_json("config.json")
        return AppConfig(
            bot_token=data["BOT_TOKEN"],
            telegram_chat_id=data["TELEGRAM_CHAT_ID"],
            openai_key=data["OPENAI_KEY"],
            openai_base_url=data["OPENAI_BASE_URL"],
            debug_mode=bool(data.get("debug_mode", False)),
        )

    def get_profile(self) -> UserProfile:
        data = self._read_json("profile.json")
        return UserProfile(
            full_name=data["name"],
            email=data["email"],
            phone=data.get("phone"),
            address=data.get("address"),
        )

    def get_resume_data(self) -> ResumeData:
        data = self._read_json("profile.json")
        return ResumeData(
            primary_resume_path=self.get_resume_path(),
            cover_letter_paths=(self.get_cover_letter_path(),),
            skills=tuple(data.get("skills", [])),
        )

    def get_resume_path(self) -> str:
        return str(self._config_dir / "resume" / "resume.pdf")

    def get_cover_letter_path(self) -> str:
        return str(self._config_dir / "cover_letter" / "cover_letter.pdf")

    # -- internal helpers ---------------------------------------------------

    def _read_json(self, filename: str) -> dict:
        path = self._config_dir / filename
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _validate_json_file(path: Path, required_keys: set[str]) -> list[str]:
        errors: list[str] = []
        if not path.is_file():
            errors.append(f"Missing file: {path}")
            return errors
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"Cannot read {path}: {exc}")
            return errors
        missing = required_keys - set(data.keys())
        if missing:
            errors.append(f"{path.name} missing keys: {', '.join(sorted(missing))}")
        return errors
