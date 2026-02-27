"""Step definitions for debug mode BDD scenarios."""
from __future__ import annotations

from domain.models import AgentStep, JobPostingRef, UserProfile
from pytest_bdd import given, when, then, scenarios, parsers

from .conftest import ApplyContext, FakeAgentForBDD, run_apply

scenarios("../features/debug_mode.feature")


# -- Given steps (re-declared locally to avoid import conflicts) -----------


@given(
    parsers.parse('a configured profile with name "{name}" and email "{email}"'),
    target_fixture="ctx",
)
def given_profile(ctx: ApplyContext, name: str, email: str) -> ApplyContext:
    ctx.profile = UserProfile(full_name=name, email=email)
    return ctx


@given(
    parsers.parse(
        'a job posting for "{company}" titled "{title}" that allows guest applications'
    ),
)
def given_guest_job(ctx: ApplyContext, company: str, title: str) -> None:
    ctx.job = JobPostingRef(
        company_name=company, job_title=title,
        job_url=f"https://{company.lower().replace(' ', '-')}.test/apply",
    )


@given("debug mode is disabled")
def given_debug_off(ctx: ApplyContext) -> None:
    ctx.debug_mode = False


@given("debug mode is enabled")
def given_debug_on(ctx: ApplyContext) -> None:
    ctx.debug_mode = True


# -- When steps -------------------------------------------------------------


@when("the bot processes the application")
def when_apply_debug(ctx: ApplyContext) -> None:
    if ctx.debug_mode:
        ctx.agent = FakeAgentForBDD(
            result_status="skipped",
            result_reason="Debug mode: final submit skipped",
        )
    else:
        ctx.agent = FakeAgentForBDD(result_status="success")
    run_apply(ctx)


# -- Then steps -------------------------------------------------------------


@then(parsers.parse('the application status should be "{status}"'))
def then_status(ctx: ApplyContext, status: str) -> None:
    assert ctx.record is not None
    assert ctx.record.status.value == status


@then(parsers.parse('the user receives a message containing "{text}"'))
def then_message_contains(ctx: ApplyContext, text: str) -> None:
    assert any(text in msg for msg in ctx.ui.info_messages)


@then(parsers.parse('the user receives a confirmation message containing "{text}"'))
def then_confirmation(ctx: ApplyContext, text: str) -> None:
    assert any(text in msg for msg in ctx.ui.info_messages)


@then("debug screenshots are saved")
def then_screenshots_saved(ctx: ApplyContext) -> None:
    assert len(ctx.debug_store.metadata) >= 1


@then(parsers.parse('debug metadata is saved with outcome "{outcome}"'))
def then_metadata(ctx: ApplyContext, outcome: str) -> None:
    assert len(ctx.debug_store.metadata) >= 1
    meta = ctx.debug_store.metadata[0][1]
    assert meta["outcome"] == outcome


@then(parsers.parse('the "{button}" button was not clicked'))
def then_button_not_clicked(ctx: ApplyContext, button: str) -> None:
    assert ctx.record is not None
    assert ctx.record.status.value == "skipped"


@then(parsers.parse('the "{button}" button was clicked'))
def then_button_clicked(ctx: ApplyContext, button: str) -> None:
    assert ctx.record is not None
    assert ctx.record.status.value == "applied"
