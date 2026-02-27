from __future__ import annotations

import argparse
import asyncio
from datetime import timezone
from typing import Sequence

from domain.models import JobPostingRef, ResumeData, RunContext
from domain.services import DebugRunManager, JobApplicationAgent, OnboardingService
from infra.agent import BrowserAgent
from infra.browser import PlaywrightBrowserTools
from infra.config import FileSystemConfigProvider
from infra.interaction import ConsoleUserInteraction
from infra.llm import OpenAIToolCallingClient
from infra.logs import FileSystemDebugArtifactStore
from infra.persistence import (
    SQLiteConfigRepository,
    SQLiteCredentialRepository,
    SQLiteJobApplicationRepository,
    SQLiteOnboardingRepository,
)
from infra.runtime import StructuredLogger, SystemClock, UuidIdGenerator
from infra.telegram import TelegramBot, TelegramBotConfig, TelegramUserInteraction


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="job-apply-cli")
    parser.add_argument("--db-path", default="job_apply_claw.db")
    sub = parser.add_subparsers(dest="command", required=True)

    start_p = sub.add_parser("start", help="Start the Telegram bot listener")
    start_p.add_argument("--config-dir", default="./config", help="Path to config folder")
    start_p.add_argument("--headless", action="store_true", default=True)
    start_p.add_argument("--no-headless", dest="headless", action="store_false")
    start_p.add_argument(
        "--skip-connectivity",
        action="store_true",
        help="Skip Telegram/OpenAI connectivity checks on startup",
    )

    sub.add_parser("onboard")

    apply_p = sub.add_parser("apply-url")
    apply_p.add_argument("job_url")
    apply_p.add_argument("--company", required=True)
    apply_p.add_argument("--title", required=True)
    apply_p.add_argument("--config-dir", default="./config")
    apply_p.add_argument("--debug", action="store_true")
    apply_p.add_argument("--debug-artifacts-dir", default="logs")
    apply_p.add_argument("--interaction", choices=["console", "telegram"], default="console")
    apply_p.add_argument("--headless", action="store_true", default=True)
    apply_p.add_argument("--no-headless", dest="headless", action="store_false")

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

    if args.command == "start":
        return _handle_start(args, job_repo, credential_repo, logger, clock, ids)

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
        return _handle_apply(args, job_repo, credential_repo, logger, clock, ids)

    raise SystemExit(f"Unsupported command: {args.command}")


def _handle_start(
    args: argparse.Namespace,
    job_repo: SQLiteJobApplicationRepository,
    credential_repo: SQLiteCredentialRepository,
    logger: StructuredLogger,
    clock: SystemClock,
    ids: UuidIdGenerator,
) -> int:
    config_provider = FileSystemConfigProvider(args.config_dir)

    errors = config_provider.validate()
    if errors:
        print("Config validation failed:")
        for err in errors:
            print(f"  - {err}")
        return 1

    cfg = config_provider.get_config()
    profile = config_provider.get_profile()
    print(f"Config OK: bot_token=***{cfg.bot_token[-4:]}, chat_id={cfg.telegram_chat_id}")
    print(f"Profile: {profile.full_name} ({profile.email})")
    print(f"Debug mode: {'ON' if cfg.debug_mode else 'OFF'}")

    if not args.skip_connectivity:
        print("Verifying API connectivity...")
        conn_result = asyncio.run(config_provider.validate_connectivity())
        if not conn_result.ok:
            print("Connectivity check failed:")
            for err in conn_result.errors:
                print(f"  - {err}")
            return 1
        print(f"Telegram bot: @{conn_result.bot_username}")
        print("OpenAI API: connected")
    else:
        print("Skipping connectivity checks (--skip-connectivity)")

    print("Starting Telegram bot listener...")

    def _make_agent() -> BrowserAgent:
        fresh_cfg = config_provider.get_config()
        llm = OpenAIToolCallingClient(
            api_key=fresh_cfg.openai_key,
            base_url=fresh_cfg.openai_base_url,
        )
        # PlaywrightBrowserTools will be created per-apply inside the bot
        # since it needs a Playwright page. The agent_factory creates a
        # BrowserAgent that the bot will use; the tools must be wired
        # when a real page is available.
        # For now, return a BrowserAgent with a placeholder — the real
        # wiring happens in the TelegramBot._handle_apply once we have
        # a Playwright page.
        return BrowserAgent(llm=llm, browser_tools=_PlaceholderTools(), logger=logger)

    bot = TelegramBot(
        config_provider=config_provider,
        job_repo=job_repo,
        credential_repo=credential_repo,
        clock=clock,
        id_generator=ids,
        logger=logger,
        agent_factory=_make_agent,
    )
    asyncio.run(bot.run())
    return 0


def _handle_apply(
    args: argparse.Namespace,
    job_repo: SQLiteJobApplicationRepository,
    credential_repo: SQLiteCredentialRepository,
    logger: StructuredLogger,
    clock: SystemClock,
    ids: UuidIdGenerator,
) -> int:
    config_provider = FileSystemConfigProvider(args.config_dir)
    errors = config_provider.validate()
    if errors:
        print("Config validation failed:")
        for err in errors:
            print(f"  - {err}")
        return 1

    cfg = config_provider.get_config()
    profile = config_provider.get_profile()
    resume_data = config_provider.get_resume_data()

    if args.interaction == "telegram":
        token = cfg.bot_token
        chat_id = cfg.telegram_chat_id
        ui = TelegramUserInteraction(TelegramBotConfig(bot_token=token, chat_id=chat_id))
    else:
        ui = ConsoleUserInteraction()

    run_context = RunContext(run_id=ids.new_run_id(), is_debug=args.debug)
    artifact_store = FileSystemDebugArtifactStore(base_dir=args.debug_artifacts_dir)

    orchestrator = JobApplicationAgent(
        job_repo=job_repo,
        credential_repo=credential_repo,
        clock=clock,
        id_generator=ids,
        logger=logger,
        debug_manager=DebugRunManager(artifact_store) if args.debug else None,
    )

    async def _run() -> int:
        from playwright.async_api import async_playwright

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=args.headless)
            page = await browser.new_page()

            tools = PlaywrightBrowserTools(
                page=page,
                ui=ui,
                resume_path=config_provider.get_resume_path(),
                cover_letter_path=config_provider.get_cover_letter_path(),
            )
            llm = OpenAIToolCallingClient(
                api_key=cfg.openai_key,
                base_url=cfg.openai_base_url,
            )
            agent = BrowserAgent(llm=llm, browser_tools=tools, logger=logger)

            try:
                record = await orchestrator.apply_to_job(
                    agent=agent,
                    ui=ui,
                    job=JobPostingRef(
                        company_name=args.company,
                        job_title=args.title,
                        job_url=args.job_url,
                    ),
                    profile=profile,
                    resume_data=resume_data,
                    run_context=run_context,
                )
                print(f"result={record.status.value} reason={record.failure_reason or '-'}")
                return 0
            finally:
                await browser.close()

    return asyncio.run(_run())


class _PlaceholderTools:
    """Placeholder BrowserToolsPort for startup agent factory.

    The real tools are wired when a Playwright page is available.
    """

    def available_tools(self):
        from infra.browser.playwright_tools import TOOL_DEFINITIONS
        return list(TOOL_DEFINITIONS)

    async def execute(self, tool_call):
        raise RuntimeError("PlaceholderTools cannot execute — real tools not wired yet")


if __name__ == "__main__":
    raise SystemExit(main())
