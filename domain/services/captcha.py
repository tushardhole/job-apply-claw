from __future__ import annotations

from dataclasses import dataclass

from domain.ports import BrowserSessionPort, UserInteractionPort


@dataclass(frozen=True)
class CaptchaResult:
    solved: bool
    failure_reason: str | None = None


class CaptchaHandler:
    """Handles captcha flows that can be delegated to the user."""

    async def handle_if_present(
        self,
        browser: BrowserSessionPort,
        ui: UserInteractionPort,
    ) -> CaptchaResult:
        if not await browser.detect_captcha_present():
            return CaptchaResult(solved=True)

        is_image_captcha_detector = getattr(browser, "detect_image_captcha", None)
        if callable(is_image_captcha_detector) and await is_image_captcha_detector():
            return CaptchaResult(
                solved=False,
                failure_reason="Image-based captcha prevents automation",
            )

        screenshot = await browser.take_screenshot("captcha")
        response = await ui.send_image_and_ask_text(
            "captcha_text",
            screenshot,
            "Please solve this captcha text so I can continue the application.",
        )
        await browser.fill_input("captcha", response.text.strip())
        return CaptchaResult(solved=True)
