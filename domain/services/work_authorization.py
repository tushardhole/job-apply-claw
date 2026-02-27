from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from domain.ports import BrowserSessionPort, UserInteractionPort


@dataclass(frozen=True)
class WorkAuthorizationQuestion:
    question_id: str
    prompt: str
    options: Sequence[str]


class WorkAuthorizationService:
    """
    Ensures work authorization answers are always user-provided.

    Browser adapters can optionally expose:
    ``list_work_authorization_questions()`` that returns
    ``Sequence[WorkAuthorizationQuestion]``.
    """

    async def answer_questions(
        self,
        browser: BrowserSessionPort,
        ui: UserInteractionPort,
    ) -> None:
        question_provider = getattr(browser, "list_work_authorization_questions", None)
        if not callable(question_provider):
            return

        questions = await question_provider()
        for q in questions:
            response = await ui.ask_choice(
                q.question_id,
                q.prompt,
                list(q.options),
                allow_multiple=False,
            )
            selected = response.selected_options[0] if response.selected_options else ""
            if selected:
                await browser.select_option(q.question_id, selected)
