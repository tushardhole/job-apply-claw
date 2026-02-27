"""Test fixtures for integration and unit tests."""

from pathlib import Path

_FIXTURES_DIR = Path(__file__).parent


def fixture_path(*parts: str) -> Path:
    """Resolve a path relative to the test/fixtures/ directory."""
    return _FIXTURES_DIR.joinpath(*parts)


def mock_resume_path() -> str:
    return str(fixture_path("documents", "mock_resume.pdf"))


def mock_cover_letter_path() -> str:
    return str(fixture_path("documents", "mock_cover_letter.pdf"))
