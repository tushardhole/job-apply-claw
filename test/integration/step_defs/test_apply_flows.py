"""Step definitions for job application flow BDD scenarios."""
from __future__ import annotations

from pytest_bdd import given, when, then, scenarios, parsers

from domain.models import JobPostingRef, UserProfile
from test.mocks import FakeBrowserSession, FakeUserInteraction

from .conftest import ApplyContext, run_apply

scenarios("../features/guest_apply.feature")
scenarios("../features/login_required.feature")
scenarios("../features/login_with_otp.feature")
scenarios("../features/account_exists.feature")
scenarios("../features/text_captcha.feature")
scenarios("../features/image_captcha.feature")


# -- Given steps ------------------------------------------------------------


@given(
    parsers.parse('a configured profile with name "{name}" and email "{email}"'),
    target_fixture="ctx",
)
def given_profile(ctx, name: str, email: str) -> ApplyContext:
    ctx.profile = UserProfile(full_name=name, email=email)
    return ctx


@given(parsers.parse('the profile has phone "{phone}" and address "{address}"'))
def given_profile_details(ctx: ApplyContext, phone: str, address: str) -> None:
    ctx.profile = UserProfile(
        full_name=ctx.profile.full_name,
        email=ctx.profile.email,
        phone=phone,
        address=address,
    )


@given(
    parsers.parse(
        'a job posting for "{company}" titled "{title}" that allows guest applications'
    ),
)
def given_guest_job(ctx: ApplyContext, company: str, title: str) -> None:
    ctx.browser = FakeBrowserSession(login_required=False, guest_apply_available=True)
    ctx.job = JobPostingRef(company_name=company, job_title=title, job_url=f"https://{company.lower().replace(' ', '-')}.test/apply")


@given(parsers.parse('a job posting for "{company}" titled "{title}" that requires login'))
def given_login_job(ctx: ApplyContext, company: str, title: str) -> None:
    ctx.browser = FakeBrowserSession(login_required=True, guest_apply_available=False)
    ctx.job = JobPostingRef(company_name=company, job_title=title, job_url=f"https://{company.lower().replace(' ', '-')}.test/apply")


@given(
    parsers.parse('a job posting for "{company}" titled "{title}" with OAuth-only login'),
)
def given_oauth_job(ctx: ApplyContext, company: str, title: str) -> None:
    ctx.browser = FakeBrowserSession(oauth_only_login=True)
    ctx.job = JobPostingRef(company_name=company, job_title=title, job_url=f"https://{company.lower().replace(' ', '-')}.test/apply")


@given(
    parsers.parse(
        'a job posting for "{company}" titled "{title}" that requires login with OTP'
    ),
)
def given_otp_job(ctx: ApplyContext, company: str, title: str) -> None:
    ctx.browser = FakeBrowserSession(
        login_required=True,
        guest_apply_available=False,
        otp_required=True,
    )
    ctx.job = JobPostingRef(company_name=company, job_title=title, job_url=f"https://{company.lower().replace(' ', '-')}.test/apply")


@given(parsers.parse('the user will provide OTP "{otp}"'))
def given_user_otp(ctx: ApplyContext, otp: str) -> None:
    ctx.ui = FakeUserInteraction(free_text_answers={"account_otp": otp})


@given(
    parsers.parse(
        'a job posting for "{company}" titled "{title}" where account already exists'
    ),
)
def given_account_exists_job(ctx: ApplyContext, company: str, title: str) -> None:
    ctx.browser = FakeBrowserSession(
        login_required=True,
        guest_apply_available=False,
        account_already_exists=True,
    )
    ctx.job = JobPostingRef(company_name=company, job_title=title, job_url=f"https://{company.lower().replace(' ', '-')}.test/apply")


@given(parsers.parse('the user will provide password reset code "{code}"'))
def given_reset_code(ctx: ApplyContext, code: str) -> None:
    ctx.ui = FakeUserInteraction(free_text_answers={"password_reset_code": code})


@given(parsers.parse('a job posting for "{company}" titled "{title}" with a text captcha'))
def given_text_captcha_job(ctx: ApplyContext, company: str, title: str) -> None:
    ctx.browser = FakeBrowserSession(captcha_present=True, image_captcha=False)
    ctx.job = JobPostingRef(company_name=company, job_title=title, job_url=f"https://{company.lower().replace(' ', '-')}.test/apply")


@given(parsers.parse('the user will solve the captcha with "{answer}"'))
def given_captcha_answer(ctx: ApplyContext, answer: str) -> None:
    ctx.ui = FakeUserInteraction(free_text_answers={"captcha_text": answer})


@given(
    parsers.parse('a job posting for "{company}" titled "{title}" with an image captcha'),
)
def given_image_captcha_job(ctx: ApplyContext, company: str, title: str) -> None:
    ctx.browser = FakeBrowserSession(captcha_present=True, image_captcha=True)
    ctx.job = JobPostingRef(company_name=company, job_title=title, job_url=f"https://{company.lower().replace(' ', '-')}.test/apply")


@given("debug mode is disabled")
def given_debug_off(ctx: ApplyContext) -> None:
    ctx.debug_mode = False


@given("debug mode is enabled")
def given_debug_on(ctx: ApplyContext) -> None:
    ctx.debug_mode = True


# -- When steps -------------------------------------------------------------


@when("the bot processes the application")
def when_apply(ctx: ApplyContext) -> None:
    run_apply(ctx)


# -- Then steps -------------------------------------------------------------


@then(parsers.parse('the application status should be "{status}"'))
def then_status(ctx: ApplyContext, status: str) -> None:
    assert ctx.record is not None
    assert ctx.record.status.value == status


@then(parsers.parse('the user receives a confirmation message containing "{text}"'))
def then_confirmation(ctx: ApplyContext, text: str) -> None:
    assert any(text in msg for msg in ctx.ui.info_messages)


@then("the resume was uploaded")
def then_resume_uploaded(ctx: ApplyContext) -> None:
    assert "resume" in ctx.browser.uploaded_files


@then(parsers.parse('the browser filled "{field}" with "{value}"'))
def then_filled(ctx: ApplyContext, field: str, value: str) -> None:
    assert ctx.browser.filled_inputs.get(field) == value


@then(parsers.parse('an account credential is stored for "{company}"'))
def then_credential_stored(ctx: ApplyContext, company: str) -> None:
    creds = ctx.credential_repo.list_all()
    assert len(creds) >= 1
    assert any(company.lower().replace(" ", "-") in c.tenant for c in creds)


@then(parsers.parse('the failure reason contains "{text}"'))
def then_failure_reason(ctx: ApplyContext, text: str) -> None:
    assert ctx.record is not None
    assert ctx.record.failure_reason is not None
    assert text in ctx.record.failure_reason
