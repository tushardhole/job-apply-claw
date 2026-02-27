"""Unit tests for PlaywrightBrowserTools.

Uses a lightweight fake page object to avoid requiring a real browser.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any

import pytest

from domain.models import ToolCall
from infra.browser.playwright_tools import TOOL_DEFINITIONS, PlaywrightBrowserTools
from test.mocks.fake_user_interaction import FakeUserInteraction


# ---------- Fake Playwright Page ------------------------------------------

class _FakeLocator:
    def __init__(self, elements: int = 1, text: str = "ok") -> None:
        self._count = elements
        self._text = text
        self.clicked = False
        self.filled_value: str | None = None
        self.selected_value: str | None = None
        self.uploaded_path: str | None = None

    async def count(self) -> int:
        return self._count

    @property
    def first(self) -> "_FakeLocator":
        return self

    async def click(self) -> None:
        self.clicked = True

    async def fill(self, value: str) -> None:
        self.filled_value = value

    async def select_option(self, value: str) -> None:
        self.selected_value = value

    async def set_input_files(self, path: str) -> None:
        self.uploaded_path = path


@dataclass
class _FakeAccessibility:
    snapshot_result: dict[str, Any] | None = None

    async def snapshot(self) -> dict[str, Any] | None:
        return self.snapshot_result


@dataclass
class _FakePage:
    url: str = "https://example.com"
    _body_text: str = "Page body text"
    _locator: _FakeLocator = field(default_factory=_FakeLocator)
    accessibility: _FakeAccessibility = field(default_factory=_FakeAccessibility)
    _goto_calls: list[str] = field(default_factory=list)
    _eval_calls: list[str] = field(default_factory=list)

    async def goto(self, url: str, **kwargs: Any) -> None:
        self.url = url
        self._goto_calls.append(url)

    async def inner_text(self, selector: str) -> str:
        return self._body_text

    async def screenshot(self, **kwargs: Any) -> bytes:
        return b"PNG_FAKE"

    async def wait_for_load_state(self, state: str, **kwargs: Any) -> None:
        pass

    async def evaluate(self, expression: str) -> None:
        self._eval_calls.append(expression)

    def get_by_role(self, role: str, name: str = "") -> _FakeLocator:
        return self._locator

    def get_by_text(self, text: str, exact: bool = False) -> _FakeLocator:
        return self._locator

    def get_by_label(self, text: str) -> _FakeLocator:
        return self._locator

    def get_by_placeholder(self, text: str) -> _FakeLocator:
        return self._locator

    def locator(self, selector: str) -> _FakeLocator:
        return self._locator


# ---------- Helpers -------------------------------------------------------

def _make_tools(
    page: _FakePage | None = None,
    ui: FakeUserInteraction | None = None,
    resume_path: str = "/tmp/resume.pdf",
    cover_letter_path: str = "/tmp/cover.pdf",
) -> PlaywrightBrowserTools:
    return PlaywrightBrowserTools(
        page=page or _FakePage(),
        ui=ui or FakeUserInteraction(),
        resume_path=resume_path,
        cover_letter_path=cover_letter_path,
    )


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


# ---------- Tests ---------------------------------------------------------

def test_available_tools_returns_all_definitions() -> None:
    tools = _make_tools()
    defs = tools.available_tools()
    names = {d.name for d in defs}
    assert "page_snapshot" in names
    assert "goto" in names
    assert "click" in names
    assert "fill" in names
    assert "done" in names
    assert "ask_user" in names
    assert len(defs) == len(TOOL_DEFINITIONS)


def test_unknown_tool_returns_error() -> None:
    tools = _make_tools()
    result = _run(tools.execute(ToolCall(name="nonexistent", arguments={})))
    assert "Unknown tool" in result


def test_goto_navigates_page() -> None:
    page = _FakePage()
    tools = _make_tools(page=page)
    result = _run(tools.execute(ToolCall(name="goto", arguments={"url": "https://jobs.com"})))
    assert "Navigated" in result
    assert page.url == "https://jobs.com"


def test_click_clicks_element() -> None:
    page = _FakePage()
    tools = _make_tools(page=page)
    result = _run(tools.execute(ToolCall(name="click", arguments={"target": "Apply"})))
    assert "Clicked" in result
    assert page._locator.clicked


def test_click_not_found() -> None:
    loc = _FakeLocator(elements=0)
    page = _FakePage(_locator=loc)
    tools = _make_tools(page=page)
    result = _run(tools.execute(ToolCall(name="click", arguments={"target": "Missing"})))
    assert "not found" in result


def test_fill_fills_field() -> None:
    page = _FakePage()
    tools = _make_tools(page=page)
    result = _run(tools.execute(ToolCall(name="fill", arguments={"field": "email", "value": "a@b.com"})))
    assert "Filled" in result
    assert page._locator.filled_value == "a@b.com"


def test_select_option_selects_dropdown() -> None:
    page = _FakePage()
    tools = _make_tools(page=page)
    result = _run(tools.execute(ToolCall(name="select_option", arguments={"field": "country", "value": "US"})))
    assert "Selected" in result


def test_upload_file_resume() -> None:
    page = _FakePage()
    tools = _make_tools(page=page, resume_path="/data/resume.pdf")
    result = _run(tools.execute(ToolCall(
        name="upload_file",
        arguments={"field": "resume", "file_type": "resume"},
    )))
    assert "Uploaded" in result
    assert page._locator.uploaded_path == "/data/resume.pdf"


def test_upload_file_no_path() -> None:
    tools = _make_tools(resume_path="")
    result = _run(tools.execute(ToolCall(
        name="upload_file",
        arguments={"field": "resume", "file_type": "resume"},
    )))
    assert "No resume file" in result


def test_scroll_down() -> None:
    page = _FakePage()
    tools = _make_tools(page=page)
    result = _run(tools.execute(ToolCall(name="scroll", arguments={"direction": "down"})))
    assert "Scrolled down" in result
    assert "600" in page._eval_calls[0]


def test_get_current_url() -> None:
    page = _FakePage(url="https://jobs.acme.com/apply")
    tools = _make_tools(page=page)
    result = _run(tools.execute(ToolCall(name="get_current_url", arguments={})))
    assert result == "https://jobs.acme.com/apply"


def test_wait_tool() -> None:
    tools = _make_tools()
    result = _run(tools.execute(ToolCall(name="wait", arguments={"seconds": 1})))
    assert "Waited" in result


def test_page_snapshot_with_accessibility() -> None:
    page = _FakePage()
    page.accessibility = _FakeAccessibility(snapshot_result={"role": "WebArea", "name": "Test"})
    tools = _make_tools(page=page)
    result = _run(tools.execute(ToolCall(name="page_snapshot", arguments={})))
    assert "WebArea" in result


def test_page_snapshot_fallback_to_body_text() -> None:
    page = _FakePage(_body_text="Hello World")
    page.accessibility = _FakeAccessibility(snapshot_result=None)
    tools = _make_tools(page=page)
    result = _run(tools.execute(ToolCall(name="page_snapshot", arguments={})))
    assert "Hello World" in result


def test_screenshot_returns_base64() -> None:
    tools = _make_tools()
    result = _run(tools.execute(ToolCall(name="screenshot", arguments={})))
    import base64
    decoded = base64.b64decode(result)
    assert decoded == b"PNG_FAKE"


def test_ask_user_delegates_to_ui() -> None:
    ui = FakeUserInteraction(free_text_answers={"agent_question": "42000"})
    tools = _make_tools(ui=ui)
    result = _run(tools.execute(ToolCall(name="ask_user", arguments={"question": "Salary?"})))
    assert result == "42000"


def test_report_status_sends_message() -> None:
    ui = FakeUserInteraction()
    tools = _make_tools(ui=ui)
    result = _run(tools.execute(ToolCall(name="report_status", arguments={"message": "Applying..."})))
    assert result == "Status sent"
    assert "Applying..." in ui.info_messages


def test_done_returns_json() -> None:
    tools = _make_tools()
    result = _run(tools.execute(ToolCall(
        name="done",
        arguments={"status": "success", "reason": "Applied"},
    )))
    parsed = json.loads(result)
    assert parsed["done"] is True
    assert parsed["status"] == "success"
