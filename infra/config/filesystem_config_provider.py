from __future__ import annotations

import asyncio
import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from domain.models import AppConfig, ResumeData, UserProfile


@dataclass(frozen=True)
class ConnectivityResult:
    """Outcome of validate_connectivity() — errors list plus bot info on success."""

    errors: list[str]
    bot_username: str | None = None

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0


_REQUIRED_CONFIG_KEYS = {"BOT_TOKEN", "TELEGRAM_CHAT_ID", "OPENAI_KEY", "OPENAI_BASE_URL"}
_REQUIRED_PROFILE_KEYS = {"name", "email"}
_PLACEHOLDER_PATTERN = re.compile(r"^YOUR_", re.IGNORECASE)
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_PATTERN = re.compile(r"^\+?[\d\s\-()]{7,}$")


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

        config_data = self._validate_json_file(config_path, _REQUIRED_CONFIG_KEYS, errors)
        profile_data = self._validate_json_file(profile_path, _REQUIRED_PROFILE_KEYS, errors)

        if config_data is not None:
            errors.extend(self._validate_config_formats(config_data))
        if profile_data is not None:
            errors.extend(self._validate_profile_formats(profile_data))

        resume = self._config_dir / "resume" / "resume.pdf"
        if not resume.is_file():
            errors.append(f"Resume not found at {resume}. Place your resume.pdf in the resume/ folder.")

        cover_letter = self._config_dir / "cover_letter" / "cover_letter.pdf"
        if not cover_letter.is_file():
            errors.append(f"Cover letter not found at {cover_letter}. Place your cover_letter.pdf in the cover_letter/ folder.")

        return errors

    @staticmethod
    def _validate_config_formats(data: dict) -> list[str]:
        errors: list[str] = []
        bot_token = data.get("BOT_TOKEN", "")
        if not bot_token or _PLACEHOLDER_PATTERN.search(str(bot_token)):
            errors.append("BOT_TOKEN is a placeholder. Get a real token from @BotFather on Telegram.")

        chat_id = str(data.get("TELEGRAM_CHAT_ID", ""))
        if not chat_id.lstrip("-").isdigit():
            errors.append("TELEGRAM_CHAT_ID must be numeric. Send /start to your bot and check the chat ID.")

        openai_key = str(data.get("OPENAI_KEY", ""))
        if "YOUR" in openai_key.upper():
            errors.append("OPENAI_KEY is a placeholder. Set your real OpenAI API key.")
        elif not openai_key.startswith("sk-") or len(openai_key) < 10:
            errors.append("OPENAI_KEY must start with 'sk-' and be at least 10 characters.")

        base_url = str(data.get("OPENAI_BASE_URL", ""))
        if not base_url.startswith("https://"):
            errors.append("OPENAI_BASE_URL must start with 'https://'.")

        debug_mode = data.get("debug_mode")
        if debug_mode is not None and not isinstance(debug_mode, bool):
            errors.append("debug_mode must be a boolean (true/false), not a string.")

        return errors

    @staticmethod
    def _validate_profile_formats(data: dict) -> list[str]:
        errors: list[str] = []
        name = data.get("name", "")
        if not name or name == "Your Full Name":
            errors.append("profile.json: name is a placeholder. Enter your real name.")

        email = data.get("email", "")
        if not _EMAIL_PATTERN.match(email):
            errors.append(f"profile.json: email '{email}' is not a valid email address.")
        elif email == "your@email.com":
            errors.append("profile.json: email is a placeholder. Enter your real email.")

        phone = data.get("phone")
        if phone is not None and not _PHONE_PATTERN.match(str(phone)):
            errors.append(f"profile.json: phone '{phone}' is not a valid phone number.")

        return errors

    async def validate_connectivity(self) -> ConnectivityResult:
        """Verify Telegram bot token and OpenAI API key work over the network."""
        errors: list[str] = []
        bot_username: str | None = None
        config = self.get_config()

        bot_username, tg_err = await asyncio.to_thread(
            self._check_telegram, config.bot_token,
        )
        if tg_err:
            errors.append(tg_err)

        openai_err = await asyncio.to_thread(
            self._check_openai, config.openai_key, config.openai_base_url,
        )
        if openai_err:
            errors.append(openai_err)

        return ConnectivityResult(errors=errors, bot_username=bot_username)

    @staticmethod
    def _check_telegram(bot_token: str) -> tuple[str | None, str | None]:
        url = f"https://api.telegram.org/bot{bot_token}/getMe"
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=15) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            if payload.get("ok"):
                username = payload.get("result", {}).get("username", "unknown")
                return username, None
            return None, f"Telegram BOT_TOKEN rejected: {payload}"
        except urllib.error.HTTPError as exc:
            return None, (
                f"Telegram BOT_TOKEN is invalid: {exc.code} {exc.reason}. "
                "Get a valid token from @BotFather."
            )
        except Exception as exc:
            return None, f"Telegram connectivity failed: {exc}"

    @staticmethod
    def _check_openai(api_key: str, base_url: str) -> str | None:
        url = f"{base_url.rstrip('/')}/models"
        try:
            req = urllib.request.Request(url, method="GET")
            req.add_header("Authorization", f"Bearer {api_key}")
            with urllib.request.urlopen(req, timeout=15) as resp:
                resp.read()
            return None
        except urllib.error.HTTPError as exc:
            if exc.code == 401:
                return (
                    "OpenAI API key rejected: 401 Unauthorized. "
                    "Check your OPENAI_KEY in config.json."
                )
            return f"OpenAI API error: {exc.code} {exc.reason}."
        except Exception as exc:
            return f"OpenAI connectivity failed: {exc}"

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
    def _validate_json_file(
        path: Path,
        required_keys: set[str],
        errors: list[str],
    ) -> dict | None:
        """Validate a JSON file exists and has required keys.

        Returns the parsed dict on success, or None if the file
        is missing or unparseable.
        """
        if not path.is_file():
            errors.append(f"Missing file: {path}")
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"Cannot read {path}: {exc}")
            return None
        missing = required_keys - set(data.keys())
        if missing:
            errors.append(f"{path.name} missing keys: {', '.join(sorted(missing))}")
            return None
        return data
