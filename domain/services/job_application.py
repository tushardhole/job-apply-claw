"""Thin orchestrator that delegates the real work to the LLM browser agent."""

from __future__ import annotations

from dataclasses import replace
from datetime import timezone

from domain.models import (
    AgentTask,
    JobApplicationRecord,
    JobApplicationStatus,
    JobPostingRef,
    ResumeData,
    RunContext,
    UserProfile,
)
from domain.ports import (
    BrowserAgentPort,
    ClockPort,
    CredentialRepositoryPort,
    IdGeneratorPort,
    JobApplicationRepositoryPort,
    LoggerPort,
    UserInteractionPort,
)
from domain.services.debug import DebugRunManager


class JobApplicationAgent:
    """Orchestrates one complete job application attempt.

    All browser interaction decisions are made by the LLM agent;
    this class handles bookkeeping (records, credentials, debug
    metadata) around the agent execution.
    """

    def __init__(
        self,
        *,
        job_repo: JobApplicationRepositoryPort,
        credential_repo: CredentialRepositoryPort,
        clock: ClockPort,
        id_generator: IdGeneratorPort,
        logger: LoggerPort,
        debug_manager: DebugRunManager | None = None,
    ) -> None:
        self._job_repo = job_repo
        self._credential_repo = credential_repo
        self._clock = clock
        self._id_generator = id_generator
        self._logger = logger
        self._debug_manager = debug_manager

    async def apply_to_job(
        self,
        *,
        agent: BrowserAgentPort,
        ui: UserInteractionPort,
        job: JobPostingRef,
        profile: UserProfile,
        resume_data: ResumeData,
        run_context: RunContext,
    ) -> JobApplicationRecord:
        started_at = self._clock.now().astimezone(timezone.utc)
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

        task = AgentTask(
            objective=f"Apply to {job.company_name} - {job.job_title} at {job.job_url}",
            context={
                "profile": {
                    "full_name": profile.full_name,
                    "email": profile.email,
                    "phone": profile.phone,
                    "address": profile.address,
                },
                "job_url": job.job_url,
                "company": job.company_name,
                "job_title": job.job_title,
                "resume_available": bool(resume_data.primary_resume_path),
                "cover_letter_available": bool(resume_data.cover_letter_paths),
            },
            max_steps=50,
            debug=run_context.is_debug,
        )

        try:
            result = await agent.execute_task(task)
        except Exception as exc:
            self._logger.error(
                "agent_execution_failed",
                job_url=job.job_url,
                error=str(exc),
            )
            failed = replace(
                record,
                status=JobApplicationStatus.FAILED,
                failure_reason=str(exc),
            )
            self._job_repo.update(failed)
            await ui.send_info(
                f"Failed to apply for {job.company_name}. Reason: {exc}",
            )
            self._write_run_metadata(run_context, job, started_at, failed)
            return failed

        if result.status == "success":
            applied = replace(
                record,
                status=JobApplicationStatus.APPLIED,
                applied_at=self._clock.now().astimezone(timezone.utc),
            )
            self._job_repo.update(applied)
            await ui.send_info(
                f"Application submitted for {job.company_name} - {job.job_title}.",
            )
            self._write_run_metadata(run_context, job, started_at, applied)
            return applied

        if result.status == "skipped":
            skipped = replace(
                record,
                status=JobApplicationStatus.SKIPPED,
                failure_reason=result.reason or "Debug mode: final submit skipped",
            )
            self._job_repo.update(skipped)
            await ui.send_info(
                f"[DEBUG] Prepared application for {job.company_name} but skipped final submit.",
            )
            self._write_run_metadata(run_context, job, started_at, skipped)
            return skipped

        # "failed" or any other status
        failed = replace(
            record,
            status=JobApplicationStatus.FAILED,
            failure_reason=result.reason or "Agent reported failure",
        )
        self._job_repo.update(failed)
        await ui.send_info(
            f"Failed to apply for {job.company_name}. Reason: {result.reason}",
        )
        self._write_run_metadata(run_context, job, started_at, failed)
        return failed

    def _write_run_metadata(
        self,
        run_context: RunContext,
        job: JobPostingRef,
        started_at: object,
        record: JobApplicationRecord,
    ) -> None:
        if self._debug_manager is None or not run_context.is_debug:
            return
        ended_at = self._clock.now().astimezone(timezone.utc)
        self._debug_manager.save_metadata(run_context, {
            "run_id": run_context.run_id,
            "company": job.company_name,
            "job_url": job.job_url,
            "mode": "debug" if run_context.is_debug else "normal",
            "started_at": str(started_at),
            "ended_at": str(ended_at),
            "outcome": record.status.value,
            "failure_reason": record.failure_reason,
        })
