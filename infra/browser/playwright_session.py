from __future__ import annotations

from domain.models import JobPostingRef


class PlaywrightBrowserSession:
    """
    Thin placeholder for a Playwright-backed browser session.

    The project currently validates behavior with deterministic mocks.
    A concrete Playwright integration can replace these placeholders
    incrementally without changing domain services.
    """

    async def goto(self, url: str) -> None:
        raise NotImplementedError("Playwright adapter is not wired yet")

    async def wait_for_load(self) -> None:
        raise NotImplementedError("Playwright adapter is not wired yet")

    async def click_button(self, label_or_selector: str) -> None:
        raise NotImplementedError("Playwright adapter is not wired yet")

    async def fill_input(self, label_or_selector: str, value: str) -> None:
        raise NotImplementedError("Playwright adapter is not wired yet")

    async def select_option(self, label_or_selector: str, value: str) -> None:
        raise NotImplementedError("Playwright adapter is not wired yet")

    async def upload_file(self, label_or_selector: str, path: str) -> None:
        raise NotImplementedError("Playwright adapter is not wired yet")

    async def detect_login_required(self) -> bool:
        raise NotImplementedError("Playwright adapter is not wired yet")

    async def detect_guest_apply_available(self) -> bool:
        raise NotImplementedError("Playwright adapter is not wired yet")

    async def detect_captcha_present(self) -> bool:
        raise NotImplementedError("Playwright adapter is not wired yet")

    async def detect_oauth_only_login(self) -> bool:
        raise NotImplementedError("Playwright adapter is not wired yet")

    async def detect_job_board_type(self, ref: JobPostingRef) -> str | None:
        return ref.job_board_type

    async def take_screenshot(self, step_name: str) -> bytes:
        raise NotImplementedError("Playwright adapter is not wired yet")
