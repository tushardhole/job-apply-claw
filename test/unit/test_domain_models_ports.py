import asyncio
from datetime import datetime, timezone

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
    UserProfile,
)
from test.mocks.fake_user_interaction import FakeUserInteraction


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
        applied_at=datetime.now(timezone.utc),
    )
    assert record.status is JobApplicationStatus.APPLIED


def test_account_credential_timestamps() -> None:
    now = datetime.now(timezone.utc)
    cred = AccountCredential(
        id="cred-1",
        portal="greenhouse",
        tenant="company-a",
        email="user@example.com",
        password="secure-value",
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
    async def main() -> None:
        ui = FakeUserInteraction()
        resp = await ui.ask_free_text("q1", "Tell me something")
        assert resp.text == ""

    asyncio.run(main())


# --------------- Agent model tests ---------------

from domain.models import (
    AgentResult,
    AgentStep,
    AgentTask,
    LLMToolResponse,
    ToolCall,
    ToolDefinition,
)


def test_tool_definition_construction() -> None:
    td = ToolDefinition(
        name="click",
        description="Click an element",
        parameters={"target": {"type": "string"}},
    )
    assert td.name == "click"
    assert td.parameters["target"]["type"] == "string"


def test_tool_call_construction() -> None:
    tc = ToolCall(name="fill", arguments={"field": "email", "value": "a@b.com"})
    assert tc.name == "fill"
    assert tc.arguments["value"] == "a@b.com"


def test_llm_tool_response_defaults() -> None:
    resp = LLMToolResponse()
    assert resp.tool_calls is None
    assert resp.text is None
    assert resp.finish_reason is None


def test_llm_tool_response_with_tool_calls() -> None:
    tc = ToolCall(name="goto", arguments={"url": "https://example.com"})
    resp = LLMToolResponse(tool_calls=[tc], finish_reason="tool_calls")
    assert resp.tool_calls is not None
    assert len(resp.tool_calls) == 1
    assert resp.tool_calls[0].name == "goto"


def test_agent_step_records_tool_execution() -> None:
    step = AgentStep(
        step_number=0,
        tool_name="click",
        tool_args={"target": "Apply"},
        tool_result="Clicked Apply",
    )
    assert step.step_number == 0
    assert step.screenshot_bytes is None


def test_agent_step_with_screenshot() -> None:
    step = AgentStep(
        step_number=1,
        tool_name="screenshot",
        tool_args={},
        tool_result="ok",
        screenshot_bytes=b"PNG_DATA",
    )
    assert step.screenshot_bytes == b"PNG_DATA"


def test_agent_task_defaults() -> None:
    task = AgentTask(objective="Apply to job")
    assert task.max_steps == 50
    assert task.debug is False
    assert task.context == {}


def test_agent_task_with_context() -> None:
    task = AgentTask(
        objective="Apply to https://example.com/jobs/1",
        context={"profile": {"name": "Jane"}, "debug": True},
        max_steps=30,
        debug=True,
    )
    assert task.context["profile"]["name"] == "Jane"
    assert task.max_steps == 30
    assert task.debug is True


def test_agent_result_success() -> None:
    result = AgentResult(status="success")
    assert result.status == "success"
    assert result.reason is None
    assert result.data == {}
    assert result.steps_taken == []


def test_agent_result_failed_with_steps() -> None:
    steps = [
        AgentStep(step_number=0, tool_name="goto", tool_args={"url": "x"}, tool_result="ok"),
        AgentStep(step_number=1, tool_name="done", tool_args={}, tool_result="done"),
    ]
    result = AgentResult(
        status="failed",
        reason="Image captcha",
        steps_taken=steps,
    )
    assert result.status == "failed"
    assert result.reason == "Image captcha"
    assert len(result.steps_taken) == 2


def test_agent_result_with_data() -> None:
    result = AgentResult(
        status="success",
        data={"new_password": "Reset-abc123"},
    )
    assert result.data["new_password"] == "Reset-abc123"


def test_agent_models_are_frozen() -> None:
    task = AgentTask(objective="test")
    with pytest.raises(AttributeError):
        task.objective = "changed"  # type: ignore[misc]

    tc = ToolCall(name="click", arguments={})
    with pytest.raises(AttributeError):
        tc.name = "fill"  # type: ignore[misc]

    result = AgentResult(status="success")
    with pytest.raises(AttributeError):
        result.status = "failed"  # type: ignore[misc]

