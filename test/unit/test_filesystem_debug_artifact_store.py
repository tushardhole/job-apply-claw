from __future__ import annotations

from domain.models import RunContext
from infra.logs import FileSystemDebugArtifactStore


def test_saves_screenshots_in_run_directory(tmp_path: str) -> None:
    store = FileSystemDebugArtifactStore(base_dir=str(tmp_path / "logs"))
    run = RunContext(run_id="run-123", is_debug=True)
    run_dir = store.ensure_run_directory(run)
    first = store.save_screenshot(run, "page_loaded", b"a")
    second = store.save_screenshot(run, "form_filled", b"b")

    assert "run_run-123" in run_dir
    assert first.endswith("Screenshot_001_page_loaded.png")
    assert second.endswith("Screenshot_002_form_filled.png")
