from __future__ import annotations

import asyncio
import json
import re
import urllib.parse
import urllib.request
from typing import Any, Callable, Sequence

from domain.models import (
    ChoiceQuestionResponse,
    CommonAnswers,
    FreeTextQuestionResponse,
    JobPostingRef,
    RunContext,
)
from domain.ports import (
    BrowserSessionPort,
    ClockPort,
    ConfigProviderPort,
    CredentialRepositoryPort,
    IdGeneratorPort,
    JobApplicationRepositoryPort,
    LoggerPort,
)
from domain.services.account_flow import AccountFlowService
from domain.services.captcha import CaptchaHandler
from domain.services.debug import DebugRunManager
from domain.services.job_application import JobApplicationAgent
from domain.services.work_authorization import WorkAuthorizationService
from infra.logs import FileSystemDebugArtifactStore

from .bot_api import TelegramApiError

_URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)


BrowserFactory = Callable[[], BrowserSessionPort]


class TelegramBot:
    """Long-running Telegram bot that listens for commands and orchestrates job applications.

    Implements ``UserInteractionPort`` so that mid-flow questions
    (salary, work auth, captcha, OTP, etc.) are routed back to the
    same Telegram chat.
    """

    def __init__(
        self,
        *,
        config_provider: ConfigProviderPort,
        job_repo: JobApplicationRepositoryPort,
        credential_repo: CredentialRepositoryPort,
        clock: ClockPort,
        id_generator: IdGeneratorPort,
        logger: LoggerPort,
        browser_factory: BrowserFactory,
    ) -> None:
        self._config_provider = config_provider
        self._job_repo = job_repo
        self._credential_repo = credential_repo
        self._clock = clock
        self._id_generator = id_generator
        self._logger = logger
        self._browser_factory = browser_factory

        self._offset = 0
        self._last_url: str | None = None
        self._applying = False
        self._bot_token: str = ""
        self._chat_id: str = ""

    # -- main loop ----------------------------------------------------------

    async def run(self) -> None:
        cfg = self._config_provider.get_config()
        self._bot_token = cfg.bot_token
        self._chat_id = cfg.telegram_chat_id

        self._logger.info("telegram_bot_started", chat_id=self._chat_id)
        await self._send_message("Bot started. Send a job URL, then /apply.")

        while True:
            updates = await self._get_updates()
            for update in updates:
                await self._handle_update(update)

    async def _handle_update(self, update: dict[str, Any]) -> None:
        update_id = int(update.get("update_id", 0))
        self._offset = max(self._offset, update_id + 1)
        text = self._extract_text(update)
        if text is None:
            return

        if text.startswith("/apply"):
            await self._handle_apply()
        elif text.startswith("/status"):
            await self._handle_status()
        elif text.startswith("/debug"):
            await self._handle_debug_toggle(text)
        elif text.startswith("/help"):
            await self._handle_help()
        elif _URL_PATTERN.match(text):
            self._last_url = text.split()[0]
            await self._send_message(f"URL received: {self._last_url}\nSend /apply to start.")
        else:
            await self._send_message(
                "Unrecognized message. Send a job URL or /help for commands."
            )

    # -- command handlers ---------------------------------------------------

    async def _handle_apply(self) -> None:
        if self._last_url is None:
            await self._send_message("No URL stored. Send a job URL first.")
            return
        if self._applying:
            await self._send_message("An application is already in progress.")
            return

        self._applying = True
        url = self._last_url
        self._last_url = None

        try:
            cfg = self._config_provider.get_config()
            self._bot_token = cfg.bot_token
            self._chat_id = cfg.telegram_chat_id

            profile = self._config_provider.get_profile()
            resume_data = self._config_provider.get_resume_data()

            run_id = self._id_generator.new_run_id()
            run_context = RunContext(
                run_id=run_id,
                is_debug=cfg.debug_mode,
            )

            debug_manager: DebugRunManager | None = None
            if cfg.debug_mode:
                debug_manager = DebugRunManager(FileSystemDebugArtifactStore())

            agent = JobApplicationAgent(
                job_repo=self._job_repo,
                credential_repo=self._credential_repo,
                clock=self._clock,
                id_generator=self._id_generator,
                logger=self._logger,
                account_flow=AccountFlowService(),
                captcha_handler=CaptchaHandler(),
                work_auth_service=WorkAuthorizationService(),
                debug_manager=debug_manager,
            )

            job = JobPostingRef(
                company_name=self._extract_company_name(url),
                job_title="",
                job_url=url,
            )

            browser = self._browser_factory()
            launch = getattr(browser, "launch", None)
            if callable(launch):
                await launch()

            try:
                await self._send_message(f"Starting application for {url} ...")
                record = await agent.apply_to_job(
                    browser=browser,
                    ui=self,
                    job=job,
                    profile=profile,
                    resume_data=resume_data,
                    common_answers=CommonAnswers(),
                    run_context=run_context,
                )
                status_msg = (
                    f"Result: {record.status.value}\n"
                    f"Company: {record.company_name}\n"
                    f"URL: {record.job_url}"
                )
                if record.failure_reason:
                    status_msg += f"\nReason: {record.failure_reason}"
                await self._send_message(status_msg)
            finally:
                close = getattr(browser, "close", None)
                if callable(close):
                    await close()
        except Exception as exc:
            self._logger.error("apply_command_failed", error=str(exc))
            await self._send_message(f"Application failed: {exc}")
        finally:
            self._applying = False

    async def _handle_status(self) -> None:
        records = self._job_repo.list_all()
        if not records:
            await self._send_message("No applications yet.")
            return
        lines = [f"- [{r.status.value}] {r.company_name}: {r.job_url}" for r in records[-10:]]
        await self._send_message("Recent applications:\n" + "\n".join(lines))

    async def _handle_debug_toggle(self, text: str) -> None:
        cfg = self._config_provider.get_config()
        await self._send_message(
            f"Debug mode is currently {'ON' if cfg.debug_mode else 'OFF'}.\n"
            "Toggle it by editing debug_mode in config.json."
        )

    async def _handle_help(self) -> None:
        await self._send_message(
            "Commands:\n"
            "  Send a job URL — stores it for /apply\n"
            "  /apply — apply to the last URL\n"
            "  /status — list recent applications\n"
            "  /debug — show debug mode status\n"
            "  /help — this message"
        )

    # -- UserInteractionPort ------------------------------------------------

    async def send_info(self, message: str) -> None:
        await self._send_message(message)

    async def ask_free_text(
        self,
        question_id: str,
        prompt: str,
    ) -> FreeTextQuestionResponse:
        await self._send_message(f"[Question: {question_id}]\n{prompt}")
        text = await self._wait_for_user_text()
        return FreeTextQuestionResponse(question_id=question_id, text=text)

    async def ask_choice(
        self,
        question_id: str,
        prompt: str,
        options: Sequence[str],
        allow_multiple: bool = False,
    ) -> ChoiceQuestionResponse:
        if not options:
            return ChoiceQuestionResponse(question_id=question_id, selected_options=[])
        options_text = "\n".join(f"  {i}. {opt}" for i, opt in enumerate(options, 1))
        await self._send_message(
            f"[Question: {question_id}]\n{prompt}\n{options_text}\n"
            "Reply with the option text."
        )
        reply = await self._wait_for_user_text()
        if allow_multiple:
            picked = [item.strip() for item in reply.split(",") if item.strip()]
            selected = [item for item in options if item in picked]
        else:
            selected = [reply] if reply in options else [options[0]]
        return ChoiceQuestionResponse(question_id=question_id, selected_options=selected)

    async def send_image_and_ask_text(
        self,
        question_id: str,
        image_bytes: bytes,
        prompt: str,
    ) -> FreeTextQuestionResponse:
        await self._send_photo(image_bytes, caption=prompt)
        text = await self._wait_for_user_text()
        return FreeTextQuestionResponse(question_id=question_id, text=text)

    # -- Telegram API helpers -----------------------------------------------

    async def _wait_for_user_text(self) -> str:
        while True:
            updates = await self._get_updates()
            for update in updates:
                update_id = int(update.get("update_id", 0))
                self._offset = max(self._offset, update_id + 1)
                text = self._extract_text(update)
                if text is not None:
                    return text
            await asyncio.sleep(1)

    async def _get_updates(self) -> list[dict[str, Any]]:
        params = {
            "offset": str(self._offset),
            "timeout": "30",
            "allowed_updates": json.dumps(["message"]),
        }
        data = await self._api_post("getUpdates", params)
        if not isinstance(data, list):
            return []
        return [item for item in data if isinstance(item, dict)]

    async def _send_message(self, text: str) -> None:
        await self._api_post("sendMessage", {"chat_id": self._chat_id, "text": text})

    async def _send_photo(self, image_bytes: bytes, caption: str) -> None:
        await asyncio.to_thread(self._sync_send_photo, image_bytes, caption)

    async def _api_post(self, method: str, params: dict[str, str]) -> Any:
        return await asyncio.to_thread(self._sync_api_post, method, params)

    def _sync_api_post(self, method: str, params: dict[str, str]) -> Any:
        url = f"https://api.telegram.org/bot{self._bot_token}/{method}"
        body = urllib.parse.urlencode(params).encode("utf-8")
        req = urllib.request.Request(url, data=body, method="POST")
        with urllib.request.urlopen(req, timeout=60) as resp:  # nosec B310
            payload = json.loads(resp.read().decode("utf-8"))
        if not payload.get("ok", False):
            raise TelegramApiError(str(payload))
        return payload.get("result")

    def _sync_send_photo(self, image_bytes: bytes, caption: str) -> None:
        boundary = "----tgbotboundary"
        url = f"https://api.telegram.org/bot{self._bot_token}/sendPhoto"
        parts = [
            f"--{boundary}\r\n".encode(),
            b'Content-Disposition: form-data; name="chat_id"\r\n\r\n',
            f"{self._chat_id}\r\n".encode(),
            f"--{boundary}\r\n".encode(),
            b'Content-Disposition: form-data; name="caption"\r\n\r\n',
            f"{caption}\r\n".encode(),
            f"--{boundary}\r\n".encode(),
            b'Content-Disposition: form-data; name="photo"; filename="screenshot.png"\r\n'
            b"Content-Type: image/png\r\n\r\n",
            image_bytes,
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
        body = b"".join(parts)
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
        with urllib.request.urlopen(req, timeout=60) as resp:  # nosec B310
            payload = json.loads(resp.read().decode("utf-8"))
        if not payload.get("ok", False):
            raise TelegramApiError(str(payload))

    # -- helpers ------------------------------------------------------------

    def _extract_text(self, update: dict[str, Any]) -> str | None:
        message = update.get("message", {})
        chat = message.get("chat", {})
        if str(chat.get("id", "")) != str(self._chat_id):
            return None
        text = message.get("text")
        if isinstance(text, str) and text.strip():
            return text.strip()
        return None

    @staticmethod
    def _extract_company_name(url: str) -> str:
        from urllib.parse import urlparse

        host = urlparse(url).hostname or "unknown"
        parts = host.replace("www.", "").split(".")
        return parts[0].title() if parts else "Unknown"
