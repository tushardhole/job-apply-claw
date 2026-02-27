from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from domain import BrowserSessionPort, JobPostingRef
from domain.services import WorkAuthorizationQuestion


@dataclass
class FakeBrowserSession:
    login_required: bool = False
    guest_apply_available: bool = True
    captcha_present: bool = False
    image_captcha: bool = False
    oauth_only_login: bool = False
    otp_required: bool = False
    account_already_exists: bool = False
    work_auth_questions: list[WorkAuthorizationQuestion] = field(default_factory=list)
    personal_questions: list[dict[str, str]] = field(default_factory=list)

    visited_urls: list[str] = field(default_factory=list)
    clicked_buttons: list[str] = field(default_factory=list)
    filled_inputs: dict[str, str] = field(default_factory=dict)
    selected_options: dict[str, str] = field(default_factory=dict)
    uploaded_files: dict[str, str] = field(default_factory=dict)
    screenshots: list[str] = field(default_factory=list)

    async def goto(self, url: str) -> None:
        self.visited_urls.append(url)

    async def wait_for_load(self) -> None:
        return None

    async def click_button(self, label_or_selector: str) -> None:
        self.clicked_buttons.append(label_or_selector)

    async def fill_input(self, label_or_selector: str, value: str) -> None:
        self.filled_inputs[label_or_selector] = value

    async def select_option(self, label_or_selector: str, value: str) -> None:
        self.selected_options[label_or_selector] = value

    async def upload_file(self, label_or_selector: str, path: str) -> None:
        self.uploaded_files[label_or_selector] = path

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
        self.screenshots.append(step_name)
        return f"image:{step_name}".encode("utf-8")

    async def detect_image_captcha(self) -> bool:
        return self.image_captcha

    async def detect_otp_required(self) -> bool:
        return self.otp_required

    async def detect_account_already_exists(self) -> bool:
        return self.account_already_exists

    async def submit_account_creation(self) -> None:
        self.clicked_buttons.append("Create Account")

    async def list_work_authorization_questions(self) -> list[WorkAuthorizationQuestion]:
        return self.work_auth_questions

    async def list_personal_questions(self) -> list[dict[str, Any]]:
        return self.personal_questions


_browser_protocol_check: BrowserSessionPort
_browser_protocol_check = FakeBrowserSession()
