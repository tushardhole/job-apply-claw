"""Unit tests for TelegramBot command handling and UserInteractionPort."""
from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock

from domain.models import AppConfig, JobApplicationStatus, UserProfile
from infra.telegram.bot_listener import TelegramBot
from test.mocks import (
    FakeBrowserSession,
    FixedClock,
    InMemoryConfigProvider,
    InMemoryCredentialRepository,
    InMemoryJobApplicationRepository,
    InMemoryLogger,
    SequentialIdGenerator,
)

from datetime import datetime, timezone


def _make_bot(
    *,
    debug_mode: bool = False,
    browser: FakeBrowserSession | None = None,
) -> tuple[TelegramBot, _FakeTelegramTransport, InMemoryJobApplicationRepository]:
    config = AppConfig(
        bot_token="tok",
        telegram_chat_id="42",
        openai_key="sk",
        openai_base_url="https://api.test/v1",
        debug_mode=debug_mode,
    )
    profile = UserProfile(full_name="Test", email="t@t.com", phone="+1", address="123 St")
    provider = InMemoryConfigProvider(config=config, profile=profile)
    job_repo = InMemoryJobApplicationRepository()
    cred_repo = InMemoryCredentialRepository()
    clock = FixedClock(datetime(2025, 6, 1, tzinfo=timezone.utc))
    id_gen = SequentialIdGenerator()
    logger = InMemoryLogger()
    b = browser or FakeBrowserSession()

    bot = TelegramBot(
        config_provider=provider,
        job_repo=job_repo,
        credential_repo=cred_repo,
        clock=clock,
        id_generator=id_gen,
        logger=logger,
        browser_factory=lambda: b,
    )

    transport = _FakeTelegramTransport(bot)
    return bot, transport, job_repo


class _FakeTelegramTransport:
    """Replaces HTTP calls with in-memory message recording and scripted responses."""

    def __init__(self, bot: TelegramBot) -> None:
        self._bot = bot
        self.sent_messages: list[str] = []
        self._incoming: list[dict[str, Any]] = []
        self._update_counter = 100
        self._installed = False

    def enqueue_user_message(self, text: str) -> None:
        self._update_counter += 1
        self._incoming.append({
            "update_id": self._update_counter,
            "message": {
                "chat": {"id": 42},
                "text": text,
            },
        })

    def install(self) -> None:
        """Monkey-patch the bot's transport methods for test isolation."""
        if self._installed:
            return
        self._installed = True

        async def fake_send(text: str) -> None:
            self.sent_messages.append(text)

        async def fake_get_updates() -> list[dict[str, Any]]:
            msgs = list(self._incoming)
            self._incoming.clear()
            return msgs

        async def fake_send_photo(image_bytes: bytes, caption: str) -> None:
            self.sent_messages.append(f"[photo] {caption}")

        self._bot._send_message = fake_send  # type: ignore[attr-defined]
        self._bot._get_updates = fake_get_updates  # type: ignore[attr-defined]
        self._bot._send_photo = fake_send_photo  # type: ignore[attr-defined]

    async def process_update(self, text: str) -> None:
        """Simulate a user sending a message to the bot."""
        self.install()
        self.enqueue_user_message(text)
        updates = await self._bot._get_updates()
        for update in updates:
            await self._bot._handle_update(update)


# -- command tests ----------------------------------------------------------


def test_url_message_stores_url() -> None:
    bot, transport, _ = _make_bot()
    transport.install()
    bot._chat_id = "42"
    bot._bot_token = "tok"

    asyncio.run(transport.process_update("https://jobs.example.com/apply/123"))

    assert bot._last_url == "https://jobs.example.com/apply/123"
    assert any("URL received" in m for m in transport.sent_messages)


def test_apply_without_url_warns_user() -> None:
    bot, transport, _ = _make_bot()
    transport.install()
    bot._chat_id = "42"
    bot._bot_token = "tok"

    asyncio.run(transport.process_update("/apply"))

    assert any("No URL stored" in m for m in transport.sent_messages)


def test_help_command_returns_usage() -> None:
    bot, transport, _ = _make_bot()
    transport.install()
    bot._chat_id = "42"
    bot._bot_token = "tok"

    asyncio.run(transport.process_update("/help"))

    assert any("/apply" in m and "/status" in m for m in transport.sent_messages)


def test_status_with_no_records() -> None:
    bot, transport, _ = _make_bot()
    transport.install()
    bot._chat_id = "42"
    bot._bot_token = "tok"

    asyncio.run(transport.process_update("/status"))

    assert any("No applications" in m for m in transport.sent_messages)


def test_debug_command_shows_status() -> None:
    bot, transport, _ = _make_bot(debug_mode=True)
    transport.install()
    bot._chat_id = "42"
    bot._bot_token = "tok"

    asyncio.run(transport.process_update("/debug"))

    assert any("ON" in m for m in transport.sent_messages)


def test_unrecognized_message() -> None:
    bot, transport, _ = _make_bot()
    transport.install()
    bot._chat_id = "42"
    bot._bot_token = "tok"

    asyncio.run(transport.process_update("hello world"))

    assert any("Unrecognized" in m for m in transport.sent_messages)


# -- apply flow tests -------------------------------------------------------


def test_apply_runs_guest_flow_and_reports_result() -> None:
    browser = FakeBrowserSession(login_required=False, guest_apply_available=True)
    bot, transport, job_repo = _make_bot(browser=browser)
    transport.install()
    bot._chat_id = "42"
    bot._bot_token = "tok"

    async def run() -> None:
        await transport.process_update("https://jobs.example.com/guest")
        await transport.process_update("/apply")

    asyncio.run(run())

    records = job_repo.list_all()
    assert len(records) == 1
    assert records[0].status is JobApplicationStatus.APPLIED
    assert any("applied" in m.lower() for m in transport.sent_messages)


def test_apply_debug_mode_skips_submit() -> None:
    browser = FakeBrowserSession(login_required=False, guest_apply_available=True)
    bot, transport, job_repo = _make_bot(debug_mode=True, browser=browser)
    transport.install()
    bot._chat_id = "42"
    bot._bot_token = "tok"

    async def run() -> None:
        await transport.process_update("https://jobs.example.com/debug")
        await transport.process_update("/apply")

    asyncio.run(run())

    records = job_repo.list_all()
    assert len(records) == 1
    assert records[0].status is JobApplicationStatus.SKIPPED
    assert "Apply" not in browser.clicked_buttons


def test_status_shows_applied_jobs() -> None:
    browser = FakeBrowserSession()
    bot, transport, job_repo = _make_bot(browser=browser)
    transport.install()
    bot._chat_id = "42"
    bot._bot_token = "tok"

    async def run() -> None:
        await transport.process_update("https://acme.com/jobs/1")
        await transport.process_update("/apply")
        transport.sent_messages.clear()
        await transport.process_update("/status")

    asyncio.run(run())

    assert any("Acme" in m for m in transport.sent_messages)


def test_url_clears_after_apply() -> None:
    bot, transport, _ = _make_bot()
    transport.install()
    bot._chat_id = "42"
    bot._bot_token = "tok"

    async def run() -> None:
        await transport.process_update("https://jobs.example.com/1")
        await transport.process_update("/apply")
        transport.sent_messages.clear()
        await transport.process_update("/apply")

    asyncio.run(run())

    assert any("No URL stored" in m for m in transport.sent_messages)


def test_extract_company_name_from_url() -> None:
    assert TelegramBot._extract_company_name("https://www.acme.com/jobs/1") == "Acme"
    assert TelegramBot._extract_company_name("https://greenhouse.io/j/1") == "Greenhouse"
