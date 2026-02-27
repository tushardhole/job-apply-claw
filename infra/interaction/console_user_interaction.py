from __future__ import annotations

import asyncio
from typing import Sequence

from domain.models import ChoiceQuestionResponse, FreeTextQuestionResponse


class ConsoleUserInteraction:
    """Simple stdin/stdout implementation of UserInteractionPort."""

    async def send_info(self, message: str) -> None:
        print(message)

    async def ask_free_text(
        self,
        question_id: str,
        prompt: str,
    ) -> FreeTextQuestionResponse:
        text = await asyncio.to_thread(input, f"{prompt}\n> ")
        return FreeTextQuestionResponse(question_id=question_id, text=text)

    async def ask_choice(
        self,
        question_id: str,
        prompt: str,
        options: Sequence[str],
        allow_multiple: bool = False,
    ) -> ChoiceQuestionResponse:
        print(prompt)
        for idx, option in enumerate(options, start=1):
            print(f"{idx}. {option}")
        raw = await asyncio.to_thread(
            input,
            "> Select option number"
            + ("s (comma-separated): " if allow_multiple else ": "),
        )
        if allow_multiple:
            selected = []
            indexes = [item.strip() for item in raw.split(",") if item.strip()]
            for item in indexes:
                if item.isdigit() and 1 <= int(item) <= len(options):
                    selected.append(options[int(item) - 1])
        else:
            if raw.isdigit() and 1 <= int(raw) <= len(options):
                selected = [options[int(raw) - 1]]
            else:
                selected = [options[0]] if options else []
        return ChoiceQuestionResponse(question_id=question_id, selected_options=selected)

    async def send_image_and_ask_text(
        self,
        question_id: str,
        image_bytes: bytes,
        prompt: str,
    ) -> FreeTextQuestionResponse:
        print(f"{prompt}\n(Received image bytes: {len(image_bytes)})")
        text = await asyncio.to_thread(input, "> ")
        return FreeTextQuestionResponse(question_id=question_id, text=text)
