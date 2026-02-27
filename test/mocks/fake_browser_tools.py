"""In-memory fake for BrowserToolsPort that records calls and returns scripted results."""

from __future__ import annotations

import json
from collections import deque
from typing import Any

from domain.models import ToolCall, ToolDefinition
from infra.browser.playwright_tools import TOOL_DEFINITIONS


class FakeBrowserTools:
    """Test double for ``BrowserToolsPort``.

    Records every tool execution and lets tests inspect what was called.
    Special tools (``ask_user``, ``page_snapshot``) can be pre-loaded with
    queued responses.
    """

    def __init__(
        self,
        *,
        page_snapshots: list[str] | None = None,
        user_responses: list[str] | None = None,
    ) -> None:
        self.executed: list[ToolCall] = []
        self._page_snapshots: deque[str] = deque(page_snapshots or ["<empty page>"])
        self._user_responses: deque[str] = deque(user_responses or [])
        self.current_url: str = "about:blank"

    def available_tools(self) -> list[ToolDefinition]:
        return list(TOOL_DEFINITIONS)

    async def execute(self, tool_call: ToolCall) -> str:
        self.executed.append(tool_call)
        handler = getattr(self, f"_handle_{tool_call.name}", None)
        if handler:
            return handler(tool_call.arguments)
        return f"ok:{tool_call.name}"

    # -- tool handlers that simulate behaviour -----------------------------

    def _handle_page_snapshot(self, args: dict[str, Any]) -> str:
        if self._page_snapshots:
            return self._page_snapshots.popleft()
        return "<empty page>"

    def _handle_goto(self, args: dict[str, Any]) -> str:
        self.current_url = args.get("url", self.current_url)
        return f"Navigated to {self.current_url}"

    def _handle_get_current_url(self, args: dict[str, Any]) -> str:
        return self.current_url

    def _handle_fill(self, args: dict[str, Any]) -> str:
        return f"Filled {args.get('field', '?')}"

    def _handle_click(self, args: dict[str, Any]) -> str:
        return f"Clicked {args.get('target', '?')}"

    def _handle_select_option(self, args: dict[str, Any]) -> str:
        return f"Selected {args.get('value', '?')} in {args.get('field', '?')}"

    def _handle_upload_file(self, args: dict[str, Any]) -> str:
        return f"Uploaded {args.get('file_type', '?')} to {args.get('field', '?')}"

    def _handle_screenshot(self, args: dict[str, Any]) -> str:
        return "SCREENSHOT_BASE64"

    def _handle_scroll(self, args: dict[str, Any]) -> str:
        return f"Scrolled {args.get('direction', 'down')}"

    def _handle_wait(self, args: dict[str, Any]) -> str:
        return f"Waited {args.get('seconds', 2)}s"

    def _handle_ask_user(self, args: dict[str, Any]) -> str:
        if self._user_responses:
            return self._user_responses.popleft()
        return ""

    def _handle_report_status(self, args: dict[str, Any]) -> str:
        return "Status sent"

    def _handle_done(self, args: dict[str, Any]) -> str:
        return json.dumps({"done": True, **args})

    # -- test helper accessors ---------------------------------------------

    def filled_fields(self) -> dict[str, str]:
        """Return {field: value} for all fill tool calls."""
        return {
            tc.arguments["field"]: tc.arguments["value"]
            for tc in self.executed
            if tc.name == "fill"
        }

    def clicked_targets(self) -> list[str]:
        return [tc.arguments["target"] for tc in self.executed if tc.name == "click"]

    def ask_user_questions(self) -> list[str]:
        return [tc.arguments.get("question", "") for tc in self.executed if tc.name == "ask_user"]

    def visited_urls(self) -> list[str]:
        return [tc.arguments["url"] for tc in self.executed if tc.name == "goto"]
