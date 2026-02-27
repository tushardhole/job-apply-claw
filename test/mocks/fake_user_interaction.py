from __future__ import annotations

from typing import Sequence

from domain.models import ChoiceQuestionResponse, FreeTextQuestionResponse


class FakeUserInteraction:
    """
    Test double for ``UserInteractionPort``.

    Answers can be pre-seeded per ``question_id`` using ``free_text_answers``.
    """

    def __init__(
        self,
        free_text_answers: dict[str, str] | None = None,
        choice_answers: dict[str, list[str]] | None = None,
    ) -> None:
        self.free_text_answers: dict[str, str] = free_text_answers or {}
        self.choice_answers: dict[str, list[str]] = choice_answers or {}
        self.info_messages: list[str] = []
        self.free_text_calls: list[str] = []
        self.choice_calls: list[tuple[str, list[str], bool]] = []
        self.image_prompts: list[str] = []

    async def send_info(self, message: str) -> None:
        self.info_messages.append(message)

    async def ask_free_text(
        self,
        question_id: str,
        prompt: str,
    ) -> FreeTextQuestionResponse:
        self.free_text_calls.append(question_id)
        answer = self.free_text_answers.get(question_id, "")
        return FreeTextQuestionResponse(question_id=question_id, text=answer)

    async def ask_choice(
        self,
        question_id: str,
        prompt: str,
        options: Sequence[str],
        allow_multiple: bool = False,
    ) -> ChoiceQuestionResponse:
        opts_list = list(options)
        self.choice_calls.append((question_id, opts_list, allow_multiple))

        if question_id in self.choice_answers:
            selected = self.choice_answers[question_id]
        elif allow_multiple:
            selected = opts_list
        else:
            selected = [opts_list[0]] if opts_list else []

        return ChoiceQuestionResponse(
            question_id=question_id,
            selected_options=selected,
        )

    async def send_image_and_ask_text(
        self,
        question_id: str,
        image_bytes: bytes,
        prompt: str,
    ) -> FreeTextQuestionResponse:
        self.image_prompts.append(prompt)
        answer = self.free_text_answers.get(question_id, "decoded")
        return FreeTextQuestionResponse(question_id=question_id, text=answer)

