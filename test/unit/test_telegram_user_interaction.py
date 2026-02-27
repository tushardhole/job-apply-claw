from __future__ import annotations

import asyncio
from typing import Any

from infra.telegram import TelegramBotConfig, TelegramUserInteraction


class FakeTelegramUserInteraction(TelegramUserInteraction):
    def __init__(self, replies: list[str]) -> None:
        super().__init__(TelegramBotConfig(bot_token="token", chat_id="42"))
        self._replies = replies
        self.sent_messages: list[str] = []
        self.sent_photos: int = 0

    async def _post(self, method: str, params: dict[str, str]) -> Any:
        if method == "sendMessage":
            self.sent_messages.append(params["text"])
        if method == "getUpdates":
            if self._replies:
                reply = self._replies.pop(0)
                return [
                    {
                        "update_id": 1,
                        "message": {"chat": {"id": 42}, "text": reply},
                    }
                ]
        return []

    async def _post_photo(self, image_bytes: bytes, caption: str) -> None:
        self.sent_photos += 1
        self.sent_messages.append(caption)


def test_free_text_roundtrip() -> None:
    ui = FakeTelegramUserInteraction(["hello"])

    async def main() -> None:
        resp = await ui.ask_free_text("q1", "Prompt")
        assert resp.text == "hello"

    asyncio.run(main())


def test_choice_defaults_to_first_when_invalid_reply() -> None:
    ui = FakeTelegramUserInteraction(["invalid"])

    async def main() -> None:
        resp = await ui.ask_choice("q2", "Pick", ["Yes", "No"])
        assert resp.selected_options == ["Yes"]

    asyncio.run(main())


def test_image_prompt_flow() -> None:
    ui = FakeTelegramUserInteraction(["captcha-answer"])

    async def main() -> None:
        resp = await ui.send_image_and_ask_text("captcha", b"x", "Solve this")
        assert resp.text == "captcha-answer"

    asyncio.run(main())
    assert ui.sent_photos == 1
