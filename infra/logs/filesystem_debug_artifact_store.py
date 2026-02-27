from __future__ import annotations

import json
import re
from pathlib import Path

from domain.models import RunContext


class FileSystemDebugArtifactStore:
    """Stores debug screenshots and metadata under logs/run_<id>/."""

    def __init__(self, base_dir: str = "logs") -> None:
        self._base_dir = Path(base_dir)
        self._step_counter: dict[str, int] = {}

    def ensure_run_directory(self, run_context: RunContext) -> str:
        run_dir = self._run_dir(run_context)
        run_dir.mkdir(parents=True, exist_ok=True)
        return str(run_dir)

    def save_screenshot(
        self,
        run_context: RunContext,
        step_name: str,
        image_bytes: bytes,
    ) -> str:
        run_dir = self._run_dir(run_context)
        run_dir.mkdir(parents=True, exist_ok=True)
        count = self._step_counter.get(run_context.run_id, 0) + 1
        self._step_counter[run_context.run_id] = count
        filename = f"Screenshot_{count:03d}_{self._safe(step_name)}.png"
        path = run_dir / filename
        path.write_bytes(image_bytes)
        return str(path)

    def save_run_metadata(
        self,
        run_context: RunContext,
        metadata: dict[str, object],
    ) -> str:
        run_dir = self._run_dir(run_context)
        run_dir.mkdir(parents=True, exist_ok=True)
        path = run_dir / "run_meta.json"
        path.write_text(json.dumps(metadata, indent=2, default=str))
        return str(path)

    def _run_dir(self, run_context: RunContext) -> Path:
        if run_context.log_directory:
            return Path(run_context.log_directory)
        return self._base_dir / f"run_{run_context.run_id}"

    @staticmethod
    def _safe(step_name: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", step_name).strip("_")
        return cleaned or "step"
