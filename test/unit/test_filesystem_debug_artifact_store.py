from __future__ import annotations

import json
from pathlib import Path

from domain.models import RunContext
from infra.logs import FileSystemDebugArtifactStore


def test_saves_screenshots_in_run_directory(tmp_path: Path) -> None:
    store = FileSystemDebugArtifactStore(base_dir=str(tmp_path / "logs"))
    run = RunContext(run_id="run-123", is_debug=True)
    run_dir = store.ensure_run_directory(run)
    first = store.save_screenshot(run, "page_loaded", b"a")
    second = store.save_screenshot(run, "form_filled", b"b")

    assert "run_run-123" in run_dir
    assert first.endswith("Screenshot_001_page_loaded.png")
    assert second.endswith("Screenshot_002_form_filled.png")


def test_saves_run_metadata_json(tmp_path: Path) -> None:
    store = FileSystemDebugArtifactStore(base_dir=str(tmp_path / "logs"))
    run = RunContext(run_id="run-meta-1", is_debug=True)
    store.ensure_run_directory(run)
    meta = {
        "run_id": "run-meta-1",
        "company": "Acme",
        "job_url": "https://example.test/1",
        "mode": "debug",
        "outcome": "skipped",
    }
    path = store.save_run_metadata(run, meta)
    assert path.endswith("run_meta.json")
    loaded = json.loads(Path(path).read_text())
    assert loaded["run_id"] == "run-meta-1"
    assert loaded["outcome"] == "skipped"
