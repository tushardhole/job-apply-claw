from __future__ import annotations

from typing import Any

from domain.models import JobPostingRef


_HEURISTIC_LOGIN_KEYWORDS = [
    "sign in", "log in", "login", "signin",
    "create account", "register",
]
_HEURISTIC_GUEST_KEYWORDS = [
    "apply as guest", "guest", "continue without",
    "apply without", "skip sign",
]
_HEURISTIC_CAPTCHA_KEYWORDS = [
    "captcha", "recaptcha", "hcaptcha", "i'm not a robot",
    "verify you are human",
]
_HEURISTIC_OAUTH_KEYWORDS = [
    "sign in with google", "sign in with microsoft",
    "sign in with apple", "continue with google",
    "sign in with facebook", "sign in with linkedin",
]


class PlaywrightBrowserSession:
    """
    Playwright-backed implementation of BrowserSessionPort.

    Requires ``playwright`` to be installed and browsers set up via
    ``playwright install chromium``.

    The session uses a single Chromium page instance.  Call ``close()``
    when finished.
    """

    def __init__(self, *, headless: bool = True) -> None:
        self._headless = headless
        self._playwright: Any = None
        self._browser: Any = None
        self._page: Any = None

    async def launch(self) -> None:
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self._headless)
        self._page = await self._browser.new_page()

    async def close(self) -> None:
        if self._page:
            await self._page.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    def _ensure_page(self) -> Any:
        if self._page is None:
            raise RuntimeError("Browser not launched. Call launch() first.")
        return self._page

    # -- navigation ---------------------------------------------------------

    async def goto(self, url: str) -> None:
        page = self._ensure_page()
        await page.goto(url, wait_until="domcontentloaded")

    async def wait_for_load(self) -> None:
        page = self._ensure_page()
        await page.wait_for_load_state("networkidle", timeout=15_000)

    # -- element interactions -----------------------------------------------

    async def click_button(self, label_or_selector: str) -> None:
        page = self._ensure_page()
        btn = page.get_by_role("button", name=label_or_selector)
        if await btn.count() > 0:
            await btn.first.click()
            return
        link = page.get_by_role("link", name=label_or_selector)
        if await link.count() > 0:
            await link.first.click()
            return
        fallback = page.locator(label_or_selector)
        await fallback.first.click()

    async def fill_input(self, label_or_selector: str, value: str) -> None:
        page = self._ensure_page()
        by_label = page.get_by_label(label_or_selector)
        if await by_label.count() > 0:
            await by_label.first.fill(value)
            return
        by_placeholder = page.get_by_placeholder(label_or_selector)
        if await by_placeholder.count() > 0:
            await by_placeholder.first.fill(value)
            return
        by_name = page.locator(f'[name="{label_or_selector}"]')
        if await by_name.count() > 0:
            await by_name.first.fill(value)
            return
        by_id = page.locator(f"#{label_or_selector}")
        if await by_id.count() > 0:
            await by_id.first.fill(value)
            return
        fallback = page.locator(label_or_selector)
        await fallback.first.fill(value)

    async def select_option(self, label_or_selector: str, value: str) -> None:
        page = self._ensure_page()
        by_label = page.get_by_label(label_or_selector)
        if await by_label.count() > 0:
            await by_label.first.select_option(value)
            return
        by_name = page.locator(f'[name="{label_or_selector}"]')
        if await by_name.count() > 0:
            await by_name.first.select_option(value)
            return
        fallback = page.locator(label_or_selector)
        await fallback.first.select_option(value)

    async def upload_file(self, label_or_selector: str, path: str) -> None:
        page = self._ensure_page()
        by_label = page.get_by_label(label_or_selector)
        if await by_label.count() > 0:
            await by_label.first.set_input_files(path)
            return
        by_name = page.locator(f'[name="{label_or_selector}"]')
        if await by_name.count() > 0:
            await by_name.first.set_input_files(path)
            return
        fallback = page.locator(label_or_selector)
        await fallback.first.set_input_files(path)

    # -- detection helpers --------------------------------------------------

    async def detect_login_required(self) -> bool:
        return await self._page_text_contains_any(_HEURISTIC_LOGIN_KEYWORDS)

    async def detect_guest_apply_available(self) -> bool:
        return await self._page_text_contains_any(_HEURISTIC_GUEST_KEYWORDS)

    async def detect_captcha_present(self) -> bool:
        return await self._page_text_contains_any(_HEURISTIC_CAPTCHA_KEYWORDS)

    async def detect_oauth_only_login(self) -> bool:
        has_oauth = await self._page_text_contains_any(_HEURISTIC_OAUTH_KEYWORDS)
        if not has_oauth:
            return False
        page = self._ensure_page()
        email_inputs = page.locator('input[type="email"], input[name="email"]')
        password_inputs = page.locator('input[type="password"]')
        has_credential_form = (await email_inputs.count() > 0) and (
            await password_inputs.count() > 0
        )
        return not has_credential_form

    async def detect_job_board_type(self, ref: JobPostingRef) -> str | None:
        url = ref.job_url.lower()
        if "myworkdayjobs" in url or "workday" in url:
            return "workday"
        if "greenhouse.io" in url:
            return "greenhouse"
        if "lever.co" in url:
            return "lever"
        if "jobs.smartrecruiters" in url:
            return "smartrecruiters"
        return ref.job_board_type

    async def take_screenshot(self, step_name: str) -> bytes:
        page = self._ensure_page()
        return await page.screenshot(full_page=True)

    # -- internal helpers ---------------------------------------------------

    async def _page_text_contains_any(self, keywords: list[str]) -> bool:
        page = self._ensure_page()
        body = await page.inner_text("body")
        lower = body.lower()
        return any(kw in lower for kw in keywords)
