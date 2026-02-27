from __future__ import annotations

import argparse
import asyncio
from datetime import timezone
from typing import Sequence

from domain.models import CommonAnswers, JobPostingRef, RunContext
from domain.services import (
    AccountFlowService,
    CaptchaHandler,
    DebugRunManager,
    JobApplicationAgent,
    OnboardingService,
    WorkAuthorizationService,
)
from infra.interaction import ConsoleUserInteraction
from infra.logs import FileSystemDebugArtifactStore
from infra.persistence import (
    SQLiteConfigRepository,
    SQLiteCredentialRepository,
    SQLiteJobApplicationRepository,
    SQLiteOnboardingRepository,
)
from infra.runtime import StructuredLogger, SystemClock, UuidIdGenerator
from infra.telegram import TelegramBotConfig, TelegramUserInteraction


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="job-apply-cli")
    parser.add_argument("--db-path", default="job_apply_claw.db")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("onboard")

    apply_p = sub.add_parser("apply-url")
    apply_p.add_argument("job_url")
    apply_p.add_argument("--company", required=True)
    apply_p.add_argument("--title", required=True)
    apply_p.add_argument("--board-type", default="unknown")
    apply_p.add_argument("--debug", action="store_true")
    apply_p.add_argument("--debug-artifacts-dir", default="logs")
    apply_p.add_argument("--interaction", choices=["console", "telegram"], default="console")
    apply_p.add_argument("--browser", choices=["mock", "playwright"], default="mock")
    apply_p.add_argument("--headless", action="store_true", default=True)
    apply_p.add_argument("--no-headless", dest="headless", action="store_false")
    apply_p.add_argument("--mock-login-required", action="store_true")
    apply_p.add_argument("--mock-guest-apply", action="store_true")
    apply_p.add_argument("--mock-captcha-text", action="store_true")
    apply_p.add_argument("--mock-captcha-image", action="store_true")
    apply_p.add_argument("--mock-oauth-only", action="store_true")
    apply_p.add_argument("--mock-otp-required", action="store_true")
    apply_p.add_argument("--mock-account-exists", action="store_true")

    sub.add_parser("list-applied")
    sub.add_parser("list-credentials")

    config_p = sub.add_parser("config")
    config_p.add_argument("action", choices=["get", "set"])
    config_p.add_argument("key")
    config_p.add_argument("value", nargs="?")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    onboarding_repo = SQLiteOnboardingRepository(db_path=args.db_path)
    config_repo = SQLiteConfigRepository(db_path=args.db_path)
    job_repo = SQLiteJobApplicationRepository(db_path=args.db_path)
    credential_repo = SQLiteCredentialRepository(db_path=args.db_path)
    logger = StructuredLogger()
    clock = SystemClock()
    ids = UuidIdGenerator()

    if args.command == "onboard":
        ui = ConsoleUserInteraction()
        service = OnboardingService(repo=onboarding_repo, ui=ui)
        summary = asyncio.run(service.ensure_onboarding_complete())
        print(f"Onboarding complete for {summary.profile.full_name} ({summary.profile.email})")
        return 0

    if args.command == "config":
        if args.action == "get":
            print(config_repo.get_config_value(args.key))
            return 0
        if args.value is None:
            raise SystemExit("config set requires a value")
        config_repo.set_config_value(args.key, args.value)
        print(f"updated {args.key}")
        return 0

    if args.command == "list-applied":
        for rec in job_repo.list_all():
            applied = rec.applied_at.astimezone(timezone.utc).isoformat() if rec.applied_at else "-"
            reason = rec.failure_reason or "-"
            print(f"{rec.company_name} | {applied} | {rec.job_url} | {rec.status.value} | {reason}")
        return 0

    if args.command == "list-credentials":
        for cred in credential_repo.list_all():
            masked = cred.password[0] + ("*" * (len(cred.password) - 2)) + cred.password[-1]
            print(f"{cred.tenant} | {cred.email} | {masked}")
        return 0

    if args.command == "apply-url":
        return _handle_apply(args, onboarding_repo, config_repo, job_repo, credential_repo, logger, clock, ids)

    raise SystemExit(f"Unsupported command: {args.command}")


def _handle_apply(
    args: argparse.Namespace,
    onboarding_repo: SQLiteOnboardingRepository,
    config_repo: SQLiteConfigRepository,
    job_repo: SQLiteJobApplicationRepository,
    credential_repo: SQLiteCredentialRepository,
    logger: StructuredLogger,
    clock: SystemClock,
    ids: UuidIdGenerator,
) -> int:
    summary = asyncio.run(
        OnboardingService(
            repo=onboarding_repo,
            ui=ConsoleUserInteraction(),
        ).ensure_onboarding_complete()
    )
    if args.interaction == "telegram":
        token = config_repo.get_config_value("BOT_TOKEN")
        chat_id = config_repo.get_config_value("TELEGRAM_CHAT_ID")
        if not token or not chat_id:
            raise SystemExit("Missing BOT_TOKEN or TELEGRAM_CHAT_ID in config.")
        ui = TelegramUserInteraction(TelegramBotConfig(bot_token=token, chat_id=chat_id))
    else:
        ui = ConsoleUserInteraction()

    browser = _create_browser(args)
    run_context = RunContext(run_id=ids.new_run_id(), is_debug=args.debug)
    artifact_store = FileSystemDebugArtifactStore(base_dir=args.debug_artifacts_dir)
    agent = JobApplicationAgent(
        job_repo=job_repo,
        credential_repo=credential_repo,
        clock=clock,
        id_generator=ids,
        logger=logger,
        account_flow=AccountFlowService(),
        captcha_handler=CaptchaHandler(),
        work_auth_service=WorkAuthorizationService(),
        debug_manager=DebugRunManager(artifact_store),
    )

    async def _run() -> int:
        if hasattr(browser, "launch"):
            await browser.launch()
        try:
            record = await agent.apply_to_job(
                browser=browser,
                ui=ui,
                job=JobPostingRef(
                    company_name=args.company,
                    job_title=args.title,
                    job_url=args.job_url,
                    job_board_type=args.board_type,
                ),
                profile=summary.profile,
                resume_data=summary.resume_data,
                common_answers=summary.common_answers or CommonAnswers(),
                run_context=run_context,
            )
            print(f"result={record.status.value} reason={record.failure_reason or '-'}")
            return 0
        finally:
            if hasattr(browser, "close") and callable(browser.close):
                await browser.close()

    return asyncio.run(_run())


def _create_browser(args: argparse.Namespace) -> object:
    if args.browser == "playwright":
        from infra.browser import PlaywrightBrowserSession

        return PlaywrightBrowserSession(headless=args.headless)

    from infra.browser import MockBrowserSession

    return MockBrowserSession(
        login_required=args.mock_login_required,
        guest_apply_available=args.mock_guest_apply or not args.mock_login_required,
        captcha_present=args.mock_captcha_text or args.mock_captcha_image,
        image_captcha=args.mock_captcha_image,
        oauth_only_login=args.mock_oauth_only,
        otp_required=args.mock_otp_required,
        account_already_exists=args.mock_account_exists,
    )


if __name__ == "__main__":
    raise SystemExit(main())
