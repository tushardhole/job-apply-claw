from __future__ import annotations

from domain.models import RunContext
from domain.ports import BrowserSessionPort, DebugArtifactStorePort


class DebugRunManager:
    """Coordinates per-step screenshot capture for debug runs."""

    def __init__(self, artifact_store: DebugArtifactStorePort) -> None:
        self._artifact_store = artifact_store

    def start(self, run_context: RunContext) -> str:
        return self._artifact_store.ensure_run_directory(run_context)

    async def capture_step(
        self,
        run_context: RunContext,
        browser: BrowserSessionPort,
        step_name: str,
    ) -> str | None:
        if not run_context.is_debug:
            return None
        screenshot = await browser.take_screenshot(step_name)
        return self._artifact_store.save_screenshot(run_context, step_name, screenshot)
