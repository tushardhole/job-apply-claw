from __future__ import annotations

from dataclasses import dataclass
from datetime import timezone

from domain.models import AccountCredential, JobPostingRef, UserProfile
from domain.ports import (
    BrowserSessionPort,
    ClockPort,
    CredentialRepositoryPort,
    IdGeneratorPort,
    UserInteractionPort,
)


@dataclass(frozen=True)
class AccountFlowResult:
    used_account: bool


class AccountFlowService:
    """
    Handles account creation and verification when guest apply is unavailable.
    """

    async def ensure_access(
        self,
        *,
        browser: BrowserSessionPort,
        ui: UserInteractionPort,
        job: JobPostingRef,
        profile: UserProfile,
        credential_repo: CredentialRepositoryPort,
        id_generator: IdGeneratorPort,
        clock: ClockPort,
    ) -> AccountFlowResult:
        login_required = await browser.detect_login_required()
        guest_available = await browser.detect_guest_apply_available()
        if not login_required or guest_available:
            return AccountFlowResult(used_account=False)

        password = f"auto-{id_generator.new_correlation_id()}"
        await browser.fill_input("email", profile.email)
        await browser.fill_input("password", password)

        submit_create = getattr(browser, "submit_account_creation", None)
        if callable(submit_create):
            await submit_create()
        else:
            await browser.click_button("Create Account")

        account_exists_detector = getattr(browser, "detect_account_already_exists", None)
        if callable(account_exists_detector) and await account_exists_detector():
            await browser.click_button("Forgot Password")
            reset_resp = await ui.ask_free_text(
                "password_reset_code",
                (
                    "Your account already exists. "
                    "Please share the password reset code or reset link token."
                ),
            )
            await browser.fill_input("password_reset_code", reset_resp.text.strip())

        otp_detector = getattr(browser, "detect_otp_required", None)
        if callable(otp_detector) and await otp_detector():
            otp_resp = await ui.ask_free_text(
                "account_otp",
                "Please share the one-time verification code sent to your email.",
            )
            await browser.fill_input("otp", otp_resp.text.strip())

        now = clock.now().astimezone(timezone.utc)
        credential_repo.upsert(
            AccountCredential(
                id=id_generator.new_correlation_id(),
                portal=job.job_board_type or "unknown",
                tenant=job.company_name.lower().replace(" ", "-"),
                email=profile.email,
                password=password,
                created_at=now,
                updated_at=now,
            )
        )
        return AccountFlowResult(used_account=True)
