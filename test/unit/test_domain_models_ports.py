import asyncio
from datetime import datetime
from typing import Sequence

import pytest

from domain import (
    AccountCredential,
    ClockPort,
    CommonAnswers,
    JobApplicationRecord,
    JobApplicationStatus,
    JobApplicationRepositoryPort,
    LoggerPort,
    RunContext,
    UserInteractionPort,
    UserProfile,
)


def test_user_profile_basics() -> None:
    profile = UserProfile(full_name="Ada Lovelace", email="ada@example.com")
    assert profile.full_name == "Ada Lovelace"
    assert profile.email == "ada@example.com"


def test_common_answers_lookup() -> None:
    answers = CommonAnswers(answers={"salary_expectation": "120000"})
    assert answers.get("salary_expectation") == "120000"
    assert answers.get("unknown", default=None) is None


def test_job_application_record_status_enum_roundtrip() -> None:
    record = JobApplicationRecord(
        id="rec-1",
        company_name="Example Corp",
        job_title="Software Engineer",
        job_url="https://example.com/jobs/1",
        status=JobApplicationStatus.APPLIED,
        applied_at=datetime.utcnow(),
    )
    assert record.status is JobApplicationStatus.APPLIED


def test_account_credential_timestamps() -> None:
    now = datetime.utcnow()
    cred = AccountCredential(
        id="cred-1",
        portal="greenhouse",
        tenant="company-a",
        email="user@example.com",
        secret="secure-value",
        created_at=now,
        updated_at=now,
    )
    assert cred.created_at == now
    assert cred.updated_at == now


def test_run_context_defaults() -> None:
    ctx = RunContext(run_id="run-123")
    assert ctx.run_id == "run-123"
    assert ctx.is_debug is False
    assert ctx.log_directory is None


def test_job_application_repository_port_protocol() -> None:
    class InMemoryRepo:
        def __init__(self) -> None:
            self._records: dict[str, JobApplicationRecord] = {}

        def add(self, record: JobApplicationRecord) -> None:
            self._records[record.id] = record

        def update(self, record: JobApplicationRecord) -> None:
            self._records[record.id] = record

        def get(self, record_id: str) -> JobApplicationRecord | None:
            return self._records.get(record_id)

        def list_all(self) -> list[JobApplicationRecord]:
            return list(self._records.values())

    repo: JobApplicationRepositoryPort = InMemoryRepo()
    assert repo.list_all() == []


def test_clock_port_protocol() -> None:
    class FixedClock:
        def __init__(self, fixed: datetime) -> None:
            self._fixed = fixed

        def now(self) -> datetime:
            return self._fixed

    fixed = datetime(2024, 1, 1)
    clock: ClockPort = FixedClock(fixed)
    assert clock.now() == fixed


def test_logger_port_protocol(capsys: pytest.CaptureFixture[str]) -> None:
    class PrintLogger:
        def info(self, message: str, **fields: object) -> None:
            print("INFO", message, fields)

        def warning(self, message: str, **fields: object) -> None:
            print("WARNING", message, fields)

        def error(self, message: str, **fields: object) -> None:
            print("ERROR", message, fields)

    logger: LoggerPort = PrintLogger()
    logger.info("hello", run_id="123")
    out = capsys.readouterr().out
    assert "INFO" in out and "hello" in out


def test_user_interaction_port_protocol() -> None:
    class FakeUserInteraction:
        async def send_info(self, message: str) -> None:
            self.last_message = message

        async def ask_free_text(self, question_id: str, prompt: str):
            self.last_prompt = prompt
            from domain.models import FreeTextQuestionResponse

            return FreeTextQuestionResponse(question_id=question_id, text="answer")

        async def ask_choice(
            self,
            question_id: str,
            prompt: str,
            options: Sequence[str],
            allow_multiple: bool = False,
        ):
            from domain.models import ChoiceQuestionResponse

            return ChoiceQuestionResponse(
                question_id=question_id,
                selected_options=[options[0]],
            )

        async def send_image_and_ask_text(
            self,
            question_id: str,
            image_bytes: bytes,
            prompt: str,
        ):
            from domain.models import FreeTextQuestionResponse

            return FreeTextQuestionResponse(question_id=question_id, text="decoded")

    async def main() -> None:
        ui: UserInteractionPort = FakeUserInteraction()
        resp = await ui.ask_free_text("q1", "Tell me something")
        assert resp.text == "answer"

    asyncio.run(main())

