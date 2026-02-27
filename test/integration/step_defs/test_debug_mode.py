"""Step definitions for debug mode BDD scenarios."""
from __future__ import annotations

from pytest_bdd import given, when, then, scenarios, parsers

from .conftest import ApplyContext

# Import shared step definitions so pytest-bdd can find them
from .test_apply_flows import *  # noqa: F401, F403

scenarios("../features/debug_mode.feature")


@then(parsers.parse('the user receives a message containing "{text}"'))
def then_message_contains(ctx: ApplyContext, text: str) -> None:
    assert any(text in msg for msg in ctx.ui.info_messages)


@then("debug screenshots are saved")
def then_screenshots_saved(ctx: ApplyContext) -> None:
    assert len(ctx.debug_store.saved) >= 1


@then(parsers.parse('debug metadata is saved with outcome "{outcome}"'))
def then_metadata(ctx: ApplyContext, outcome: str) -> None:
    assert len(ctx.debug_store.metadata) >= 1
    meta = ctx.debug_store.metadata[0][1]
    assert meta["outcome"] == outcome


@then(parsers.parse('the "{button}" button was not clicked'))
def then_button_not_clicked(ctx: ApplyContext, button: str) -> None:
    assert button not in ctx.browser.clicked_buttons


@then(parsers.parse('the "{button}" button was clicked'))
def then_button_clicked(ctx: ApplyContext, button: str) -> None:
    assert button in ctx.browser.clicked_buttons
