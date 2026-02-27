from __future__ import annotations

from pathlib import Path

from test.fixtures import mock_cover_letter_path, mock_resume_path


def test_mock_resume_exists_and_is_valid_pdf() -> None:
    path = Path(mock_resume_path())
    assert path.exists()
    assert path.stat().st_size > 0
    header = path.read_bytes()[:5]
    assert header == b"%PDF-"


def test_mock_cover_letter_exists_and_is_valid_pdf() -> None:
    path = Path(mock_cover_letter_path())
    assert path.exists()
    assert path.stat().st_size > 0
    header = path.read_bytes()[:5]
    assert header == b"%PDF-"
