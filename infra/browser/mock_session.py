from __future__ import annotations

from dataclasses import dataclass, field

from domain.models import JobPostingRef
from domain.services import WorkAuthorizationQuestion


@dataclass
class MockBrowserSession:
    """
    Deterministic browser adapter for local CLI testing.

    This simulates common job board branches before a real browser backend
    is attached.
    """

    login_required: bool = False
    guest_apply_available: bool = True
    captcha_present: bool = False
    image_captcha: bool = False
    oauth_only_login: bool = False
    otp_required: bool = False
    account_already_exists: bool = False
    work_auth_questions: list[WorkAuthorizationQuestion] = field(default_factory=list)
    personal_questions: list[dict[str, str]] = field(default_factory=list)

    async def goto(self, url: str) -> None:
        return None

    async def wait_for_load(self) -> None:
        return None

    async def click_button(self, label_or_selector: str) -> None:
        return None

    async def fill_input(self, label_or_selector: str, value: str) -> None:
        return None

    async def select_option(self, label_or_selector: str, value: str) -> None:
        return None

    async def upload_file(self, label_or_selector: str, path: str) -> None:
        return None

    async def detect_login_required(self) -> bool:
        return self.login_required

    async def detect_guest_apply_available(self) -> bool:
        return self.guest_apply_available

    async def detect_captcha_present(self) -> bool:
        return self.captcha_present

    async def detect_oauth_only_login(self) -> bool:
        return self.oauth_only_login

    async def detect_job_board_type(self, ref: JobPostingRef) -> str | None:
        return ref.job_board_type

    async def take_screenshot(self, step_name: str) -> bytes:
        return f"image:{step_name}".encode()

    async def detect_image_captcha(self) -> bool:
        return self.image_captcha

    async def detect_otp_required(self) -> bool:
        return self.otp_required

    async def detect_account_already_exists(self) -> bool:
        return self.account_already_exists

    async def submit_account_creation(self) -> None:
        return None

    async def list_work_authorization_questions(self) -> list[WorkAuthorizationQuestion]:
        return self.work_auth_questions

    async def list_personal_questions(self) -> list[dict[str, str]]:
        return self.personal_questions
