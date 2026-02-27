"""Step definitions for Telegram bot command BDD scenarios."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import pytest
from pytest_bdd import given, when, then, scenarios, parsers

from domain.models import AppConfig, UserProfile
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

scenarios("../features/telegram_commands.feature")


@dataclass
class BotContext:
    bot: TelegramBot = None  # type: ignore[assignment]
    sent: list[str] = field(default_factory=list)
    update_counter: int = 100


def _make_bot(*, browser: FakeBrowserSession | None = None) -> BotContext:
    config = AppConfig(
        bot_token="tok",
        telegram_chat_id="42",
        openai_key="sk",
        openai_base_url="https://api.test/v1",
    )
    provider = InMemoryConfigProvider(
        config=config,
        profile=UserProfile(full_name="Test", email="t@t.com"),
    )
    bctx = BotContext()
    b = browser or FakeBrowserSession()
    bot = TelegramBot(
        config_provider=provider,
        job_repo=InMemoryJobApplicationRepository(),
        credential_repo=InMemoryCredentialRepository(),
        clock=FixedClock(datetime(2025, 6, 1, tzinfo=timezone.utc)),
        id_generator=SequentialIdGenerator(),
        logger=InMemoryLogger(),
        browser_factory=lambda: b,
    )
    bot._chat_id = "42"
    bot._bot_token = "tok"

    async def fake_send(text: str) -> None:
        bctx.sent.append(text)

    async def fake_get_updates() -> list[dict[str, Any]]:
        return []

    bot._send_message = fake_send  # type: ignore[attr-defined]
    bot._get_updates = fake_get_updates  # type: ignore[attr-defined]

    bctx.bot = bot
    return bctx


def _process(bctx: BotContext, text: str) -> None:
    bctx.update_counter += 1
    update = {
        "update_id": bctx.update_counter,
        "message": {"chat": {"id": 42}, "text": text},
    }

    async def _run() -> None:
        await bctx.bot._handle_update(update)

    asyncio.run(_run())


@pytest.fixture()
def bot_ctx() -> BotContext:
    return _make_bot()


@given("a running Telegram bot", target_fixture="bot_ctx")
def given_bot() -> BotContext:
    return _make_bot()


@given("a running Telegram bot with a guest-apply browser", target_fixture="bot_ctx")
def given_bot_with_browser() -> BotContext:
    return _make_bot(browser=FakeBrowserSession(login_required=False, guest_apply_available=True))


@when(parsers.parse('the user sends "{text}"'))
def when_user_sends(bot_ctx: BotContext, text: str) -> None:
    _process(bot_ctx, text)


@then(parsers.parse('the bot acknowledges with "{text}"'))
def then_ack(bot_ctx: BotContext, text: str) -> None:
    assert any(text in m for m in bot_ctx.sent), f"Expected '{text}' in {bot_ctx.sent}"


@then(parsers.parse('the last stored URL is "{url}"'))
def then_stored_url(bot_ctx: BotContext, url: str) -> None:
    assert bot_ctx.bot._last_url == url


@then(parsers.parse('the bot responds with "{text}"'))
def then_responds(bot_ctx: BotContext, text: str) -> None:
    assert any(text in m for m in bot_ctx.sent), f"Expected '{text}' in {bot_ctx.sent}"
