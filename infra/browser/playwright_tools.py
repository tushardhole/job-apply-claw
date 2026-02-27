"""Playwright-backed implementation of BrowserToolsPort.

Each browser tool the LLM agent can call is mapped to a method that
drives a Playwright ``Page`` instance.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from domain.models import ToolCall, ToolDefinition
from domain.ports import UserInteractionPort


TOOL_DEFINITIONS: list[ToolDefinition] = [
    ToolDefinition(
        name="page_snapshot",
        description="Return the accessibility tree of the current page as structured text.",
        parameters={},
    ),
    ToolDefinition(
        name="screenshot",
        description="Take a full-page screenshot and return the raw PNG bytes (base64 in messages).",
        parameters={},
    ),
    ToolDefinition(
        name="goto",
        description="Navigate the browser to the given URL.",
        parameters={"url": {"type": "string", "description": "The URL to navigate to."}},
    ),
    ToolDefinition(
        name="click",
        description="Click an element identified by visible text, ARIA role label, or CSS selector.",
        parameters={"target": {"type": "string", "description": "Button text, link text, or CSS selector."}},
    ),
    ToolDefinition(
        name="fill",
        description="Fill a form field with the given value. Identifies the field by label, placeholder, name attribute, or CSS selector.",
        parameters={
            "field": {"type": "string", "description": "Field label, placeholder, name, or CSS selector."},
            "value": {"type": "string", "description": "The value to type into the field."},
        },
    ),
    ToolDefinition(
        name="select_option",
        description="Select a dropdown option by its visible text or value.",
        parameters={
            "field": {"type": "string", "description": "Dropdown label or selector."},
            "value": {"type": "string", "description": "Option text or value to select."},
        },
    ),
    ToolDefinition(
        name="upload_file",
        description="Upload a document to a file input field.",
        parameters={
            "field": {"type": "string", "description": "File input label or selector."},
            "file_type": {"type": "string", "enum": ["resume", "cover_letter"], "description": "Which document to upload."},
        },
    ),
    ToolDefinition(
        name="scroll",
        description="Scroll the page up or down.",
        parameters={"direction": {"type": "string", "enum": ["up", "down"], "description": "Scroll direction."}},
    ),
    ToolDefinition(
        name="get_current_url",
        description="Return the current page URL.",
        parameters={},
    ),
    ToolDefinition(
        name="wait",
        description="Wait for the page to finish loading or for a specified number of seconds.",
        parameters={"seconds": {"type": "integer", "description": "Seconds to wait (default 2).", "default": 2}},
    ),
    ToolDefinition(
        name="ask_user",
        description="Ask the human user a question via Telegram and wait for their text reply.",
        parameters={"question": {"type": "string", "description": "The question to ask the user."}},
    ),
    ToolDefinition(
        name="report_status",
        description="Send an informational status message to the user (no reply expected).",
        parameters={"message": {"type": "string", "description": "The status message."}},
    ),
    ToolDefinition(
        name="done",
        description="Signal that the current task is complete.",
        parameters={
            "status": {"type": "string", "enum": ["success", "failed", "skipped"], "description": "Outcome."},
            "reason": {"type": "string", "description": "Short explanation of the outcome."},
        },
    ),
]


class PlaywrightBrowserTools:
    """Translates agent tool calls into Playwright page operations.

    Implements ``BrowserToolsPort``.
    """

    def __init__(
        self,
        *,
        page: Any,
        ui: UserInteractionPort,
        resume_path: str = "",
        cover_letter_path: str = "",
    ) -> None:
        self._page = page
        self._ui = ui
        self._resume_path = resume_path
        self._cover_letter_path = cover_letter_path

    def available_tools(self) -> list[ToolDefinition]:
        return list(TOOL_DEFINITIONS)

    async def execute(self, tool_call: ToolCall) -> str:
        handler = getattr(self, f"_tool_{tool_call.name}", None)
        if handler is None:
            return f"Unknown tool: {tool_call.name}"
        return await handler(**tool_call.arguments)

    # -- individual tools ---------------------------------------------------

    async def _tool_page_snapshot(self) -> str:
        snapshot = await self._page.accessibility.snapshot()
        if snapshot is None:
            body = await self._page.inner_text("body")
            return body[:4000] if len(body) > 4000 else body
        return json.dumps(snapshot, indent=2, default=str)[:8000]

    async def _tool_screenshot(self) -> str:
        data = await self._page.screenshot(full_page=True)
        import base64
        return base64.b64encode(data).decode("ascii")

    async def _tool_goto(self, url: str) -> str:
        await self._page.goto(url, wait_until="domcontentloaded")
        return f"Navigated to {url}"

    async def _tool_click(self, target: str) -> str:
        for locator_fn in [
            lambda: self._page.get_by_role("button", name=target),
            lambda: self._page.get_by_role("link", name=target),
            lambda: self._page.get_by_text(target, exact=False),
            lambda: self._page.locator(target),
        ]:
            loc = locator_fn()
            if await loc.count() > 0:
                await loc.first.click()
                return f"Clicked: {target}"
        return f"Element not found: {target}"

    async def _tool_fill(self, field: str, value: str) -> str:
        for locator_fn in [
            lambda: self._page.get_by_label(field),
            lambda: self._page.get_by_placeholder(field),
            lambda: self._page.locator(f'[name="{field}"]'),
            lambda: self._page.locator(f"#{field}"),
            lambda: self._page.locator(field),
        ]:
            loc = locator_fn()
            if await loc.count() > 0:
                await loc.first.fill(value)
                return f"Filled {field}"
        return f"Field not found: {field}"

    async def _tool_select_option(self, field: str, value: str) -> str:
        for locator_fn in [
            lambda: self._page.get_by_label(field),
            lambda: self._page.locator(f'[name="{field}"]'),
            lambda: self._page.locator(field),
        ]:
            loc = locator_fn()
            if await loc.count() > 0:
                await loc.first.select_option(value)
                return f"Selected {value} in {field}"
        return f"Dropdown not found: {field}"

    async def _tool_upload_file(self, field: str, file_type: str = "resume") -> str:
        path = self._resume_path if file_type == "resume" else self._cover_letter_path
        if not path:
            return f"No {file_type} file configured"
        for locator_fn in [
            lambda: self._page.get_by_label(field),
            lambda: self._page.locator(f'[name="{field}"]'),
            lambda: self._page.locator(field),
        ]:
            loc = locator_fn()
            if await loc.count() > 0:
                await loc.first.set_input_files(path)
                return f"Uploaded {file_type} to {field}"
        return f"File input not found: {field}"

    async def _tool_scroll(self, direction: str = "down") -> str:
        delta = 600 if direction == "down" else -600
        await self._page.evaluate(f"window.scrollBy(0, {delta})")
        return f"Scrolled {direction}"

    async def _tool_get_current_url(self) -> str:
        return self._page.url

    async def _tool_wait(self, seconds: int = 2) -> str:
        try:
            await self._page.wait_for_load_state("networkidle", timeout=seconds * 1000)
        except Exception:
            await asyncio.sleep(seconds)
        return f"Waited {seconds}s"

    async def _tool_ask_user(self, question: str) -> str:
        response = await self._ui.ask_free_text("agent_question", question)
        return response.text

    async def _tool_report_status(self, message: str) -> str:
        await self._ui.send_info(message)
        return "Status sent"

    async def _tool_done(self, status: str = "success", reason: str = "") -> str:
        return json.dumps({"done": True, "status": status, "reason": reason})
