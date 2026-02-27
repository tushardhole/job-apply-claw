from __future__ import annotations

import asyncio
import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Sequence

from domain.models import ChoiceQuestionResponse, FreeTextQuestionResponse


class TelegramApiError(RuntimeError):
    pass


@dataclass(frozen=True)
class TelegramBotConfig:
    bot_token: str
    chat_id: str
    poll_timeout_seconds: int = 30


class TelegramUserInteraction:
    """
    Telegram-backed implementation of UserInteractionPort.

    This implementation uses plain HTTP Bot API calls to avoid introducing
    mandatory third-party dependencies at this stage.
    """

    def __init__(self, config: TelegramBotConfig) -> None:
        self._config = config
        self._offset = 0

    async def send_info(self, message: str) -> None:
        await self._post("sendMessage", {"chat_id": self._config.chat_id, "text": message})

    async def ask_free_text(
        self,
        question_id: str,
        prompt: str,
    ) -> FreeTextQuestionResponse:
        await self.send_info(f"{prompt}\n(question: {question_id})")
        text = await self._wait_for_next_user_text()
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
        options_text = "\n".join(f"- {item}" for item in options)
        await self.send_info(
            f"{prompt}\nOptions:\n{options_text}\nReply with your choice text.",
        )
        reply = await self._wait_for_next_user_text()
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
        await self._post_photo(image_bytes, caption=prompt)
        text = await self._wait_for_next_user_text()
        return FreeTextQuestionResponse(question_id=question_id, text=text)

    async def _wait_for_next_user_text(self) -> str:
        while True:
            updates = await self._get_updates()
            for update in updates:
                update_id = int(update.get("update_id", 0))
                self._offset = max(self._offset, update_id + 1)
                message = update.get("message", {})
                chat = message.get("chat", {})
                if str(chat.get("id", "")) != str(self._config.chat_id):
                    continue
                text = message.get("text")
                if isinstance(text, str) and text.strip():
                    return text.strip()
            await asyncio.sleep(1)

    async def _get_updates(self) -> list[dict[str, Any]]:
        params = {
            "offset": str(self._offset),
            "timeout": str(self._config.poll_timeout_seconds),
            "allowed_updates": json.dumps(["message"]),
        }
        data = await self._post("getUpdates", params)
        if not isinstance(data, list):
            return []
        return [item for item in data if isinstance(item, dict)]

    async def _post(self, method: str, params: dict[str, str]) -> Any:
        return await asyncio.to_thread(self._sync_post, method, params)

    def _sync_post(self, method: str, params: dict[str, str]) -> Any:
        base = f"https://api.telegram.org/bot{self._config.bot_token}/{method}"
        body = urllib.parse.urlencode(params).encode("utf-8")
        req = urllib.request.Request(base, data=body, method="POST")
        with urllib.request.urlopen(req, timeout=60) as resp:  # nosec B310
            payload = json.loads(resp.read().decode("utf-8"))
        if not payload.get("ok", False):
            raise TelegramApiError(str(payload))
        return payload.get("result")

    async def _post_photo(self, image_bytes: bytes, caption: str) -> None:
        await asyncio.to_thread(self._sync_post_photo, image_bytes, caption)

    def _sync_post_photo(self, image_bytes: bytes, caption: str) -> None:
        boundary = "----cursorboundary"
        base = f"https://api.telegram.org/bot{self._config.bot_token}/sendPhoto"
        lines = []
        lines.append(f"--{boundary}\r\n".encode("utf-8"))
        lines.append(b'Content-Disposition: form-data; name="chat_id"\r\n\r\n')
        lines.append(f"{self._config.chat_id}\r\n".encode("utf-8"))
        lines.append(f"--{boundary}\r\n".encode("utf-8"))
        lines.append(b'Content-Disposition: form-data; name="caption"\r\n\r\n')
        lines.append(f"{caption}\r\n".encode("utf-8"))
        lines.append(f"--{boundary}\r\n".encode("utf-8"))
        lines.append(
            b'Content-Disposition: form-data; name="photo"; filename="captcha.png"\r\n'
            b"Content-Type: image/png\r\n\r\n"
        )
        lines.append(image_bytes)
        lines.append(b"\r\n")
        lines.append(f"--{boundary}--\r\n".encode("utf-8"))
        body = b"".join(lines)

        req = urllib.request.Request(base, data=body, method="POST")
        req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
        with urllib.request.urlopen(req, timeout=60) as resp:  # nosec B310
            payload = json.loads(resp.read().decode("utf-8"))
        if not payload.get("ok", False):
            raise TelegramApiError(str(payload))
