from __future__ import annotations

from dataclasses import replace
from datetime import timezone

from domain.models import (
    CommonAnswers,
    JobApplicationRecord,
    JobApplicationStatus,
    JobPostingRef,
    ResumeData,
    RunContext,
    UserProfile,
)
from domain.ports import (
    BrowserSessionPort,
    ClockPort,
    CredentialRepositoryPort,
    IdGeneratorPort,
    JobApplicationRepositoryPort,
    LoggerPort,
    UserInteractionPort,
)
from domain.services.account_flow import AccountFlowService
from domain.services.captcha import CaptchaHandler
from domain.services.debug import DebugRunManager
from domain.services.work_authorization import WorkAuthorizationService


class JobApplicationAgent:
    """Orchestrates one complete job application attempt."""

    def __init__(
        self,
        *,
        job_repo: JobApplicationRepositoryPort,
        credential_repo: CredentialRepositoryPort,
        clock: ClockPort,
        id_generator: IdGeneratorPort,
        logger: LoggerPort,
        account_flow: AccountFlowService,
        captcha_handler: CaptchaHandler,
        work_auth_service: WorkAuthorizationService,
        debug_manager: DebugRunManager | None = None,
    ) -> None:
        self._job_repo = job_repo
        self._credential_repo = credential_repo
        self._clock = clock
        self._id_generator = id_generator
        self._logger = logger
        self._account_flow = account_flow
        self._captcha_handler = captcha_handler
        self._work_auth_service = work_auth_service
        self._debug_manager = debug_manager

    async def apply_to_job(
        self,
        *,
        browser: BrowserSessionPort,
        ui: UserInteractionPort,
        job: JobPostingRef,
        profile: UserProfile,
        resume_data: ResumeData,
        common_answers: CommonAnswers,
        run_context: RunContext,
    ) -> JobApplicationRecord:
        record = JobApplicationRecord(
            id=self._id_generator.new_correlation_id(),
            company_name=job.company_name,
            job_title=job.job_title,
            job_url=job.job_url,
            status=JobApplicationStatus.PENDING,
            debug_run_id=run_context.run_id if run_context.is_debug else None,
        )
        self._job_repo.add(record)
        if self._debug_manager is not None:
            self._debug_manager.start(run_context)

        try:
            await browser.goto(job.job_url)
            await browser.wait_for_load()
            await self._capture_debug_step(run_context, browser, "page_loaded")

            if await browser.detect_oauth_only_login():
                return await self._finalize_failure(
                    record,
                    ui,
                    "OAuth-only login cannot be automated",
                )

            await self._account_flow.ensure_access(
                browser=browser,
                ui=ui,
                job=job,
                profile=profile,
                credential_repo=self._credential_repo,
                id_generator=self._id_generator,
                clock=self._clock,
            )
            await self._capture_debug_step(run_context, browser, "account_flow")

            await self._fill_common_fields(browser, profile, resume_data, common_answers)
            await self._work_auth_service.answer_questions(browser, ui)
            await self._fill_personal_questions(browser, ui)
            await self._capture_debug_step(run_context, browser, "form_filled")

            captcha_result = await self._captcha_handler.handle_if_present(browser, ui)
            if not captcha_result.solved:
                return await self._finalize_failure(
                    record,
                    ui,
                    captcha_result.failure_reason or "Captcha handling failed",
                )
            await self._capture_debug_step(run_context, browser, "captcha_done")

            if run_context.is_debug:
                skipped = replace(
                    record,
                    status=JobApplicationStatus.SKIPPED,
                    failure_reason="Debug mode enabled: final submit skipped",
                )
                self._job_repo.update(skipped)
                await ui.send_info(
                    f"[DEBUG] Prepared application for {job.company_name} but skipped final submit.",
                )
                return skipped

            await browser.click_button("Apply")
            applied = replace(
                record,
                status=JobApplicationStatus.APPLIED,
                applied_at=self._clock.now().astimezone(timezone.utc),
            )
            self._job_repo.update(applied)
            await ui.send_info(
                f"Application submitted for {job.company_name} - {job.job_title}.",
            )
            return applied
        except Exception as exc:
            self._logger.error(
                "job_application_failed",
                job_url=job.job_url,
                company_name=job.company_name,
                error=str(exc),
            )
            return await self._finalize_failure(record, ui, str(exc))

    async def _finalize_failure(
        self,
        record: JobApplicationRecord,
        ui: UserInteractionPort,
        reason: str,
    ) -> JobApplicationRecord:
        failed = replace(record, status=JobApplicationStatus.FAILED, failure_reason=reason)
        self._job_repo.update(failed)
        await ui.send_info(
            f"Failed to apply for {record.company_name} - {record.job_title}. Reason: {reason}",
        )
        return failed

    async def _fill_common_fields(
        self,
        browser: BrowserSessionPort,
        profile: UserProfile,
        resume_data: ResumeData,
        common_answers: CommonAnswers,
    ) -> None:
        await browser.fill_input("full_name", profile.full_name)
        await browser.fill_input("email", profile.email)
        if profile.phone:
            await browser.fill_input("phone", profile.phone)
        if profile.address:
            await browser.fill_input("address", profile.address)

        await browser.upload_file("resume", resume_data.primary_resume_path)

        salary = common_answers.get("salary_expectation")
        if salary:
            await browser.fill_input("salary_expectation", salary)

    async def _fill_personal_questions(
        self,
        browser: BrowserSessionPort,
        ui: UserInteractionPort,
    ) -> None:
        question_provider = getattr(browser, "list_personal_questions", None)
        if not callable(question_provider):
            return

        questions = await question_provider()
        for item in questions:
            response = await ui.ask_free_text(item["id"], item["prompt"])
            await browser.fill_input(item["id"], response.text.strip())

    async def _capture_debug_step(
        self,
        run_context: RunContext,
        browser: BrowserSessionPort,
        step_name: str,
    ) -> None:
        if self._debug_manager is None:
            return
        await self._debug_manager.capture_step(run_context, browser, step_name)
