from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TypeVar
from uuid import uuid4

from playwright.async_api import BrowserContext, Page, Playwright, async_playwright

from app.browser.extractor import click_chat_by_name, extract_chat_detail, extract_chat_summaries
from app.browser.talent_extractor import extract_talent_cards
from app.core.config import settings
from app.schemas.automation import BrowserStatus, ChatScanResult
from app.schemas.talents import TalentCard


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PROFILE_DIR = PROJECT_ROOT / "data" / "profiles" / "boss-chrome"
DEFAULT_SCREENSHOT_DIR = PROJECT_ROOT / "data" / "screenshots"
BLOCKED_KEYWORDS = ("验证码", "安全验证", "账号异常", "访问受限", "操作频繁")
LOGIN_KEYWORDS = ("登录", "扫码登录", "手机号登录")


@dataclass(frozen=True)
class BrowserSessionConfig:
    base_url: str
    chat_url: str
    recommend_url: str
    user_data_dir: str
    screenshot_dir: str
    executable_path: str
    browser_channel: str
    headless: bool = False


def get_browser_session_config() -> BrowserSessionConfig:
    return BrowserSessionConfig(
        base_url=settings.boss_base_url,
        chat_url=f"{settings.boss_base_url.rstrip('/')}/web/chat/index",
        recommend_url=f"{settings.boss_base_url.rstrip('/')}/web/chat/recommend",
        user_data_dir=settings.chrome_user_data_dir or str(DEFAULT_PROFILE_DIR),
        screenshot_dir=settings.screenshot_dir or str(DEFAULT_SCREENSHOT_DIR),
        executable_path=settings.chrome_executable_path,
        browser_channel=settings.playwright_browser_channel,
        headless=settings.browser_headless,
    )


class BrowserSessionError(RuntimeError):
    pass


class BrowserOperationError(BrowserSessionError):
    def __init__(self, message: str, screenshot_path: str | None = None) -> None:
        super().__init__(message)
        self.screenshot_path = screenshot_path


class _BrowserWorker:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._playwright: Playwright | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._state = "stopped"
        self._detail: str | None = None
        self._consecutive_failures = 0
        self._last_error: str | None = None

    async def start(self) -> BrowserStatus:
        async with self._lock:
            if self._context and self._page and not self._page.is_closed():
                return await self._inspect_page()
            if self._context or self._playwright:
                await self._close_resources()

            config = get_browser_session_config()
            Path(config.user_data_dir).mkdir(parents=True, exist_ok=True)
            Path(config.screenshot_dir).mkdir(parents=True, exist_ok=True)
            self._state = "starting"
            try:
                self._playwright = await async_playwright().start()
                launch_options: dict[str, object] = {
                    "headless": config.headless,
                    "viewport": {"width": 1440, "height": 960},
                    "locale": "zh-CN",
                }
                if config.executable_path:
                    launch_options["executable_path"] = config.executable_path
                elif config.browser_channel:
                    launch_options["channel"] = config.browser_channel
                self._context = await self._playwright.chromium.launch_persistent_context(
                    config.user_data_dir,
                    **launch_options,
                )
                self._page = self._context.pages[0] if self._context.pages else await self._context.new_page()
                await self._page.goto(config.chat_url, wait_until="domcontentloaded", timeout=30_000)
                await self._page.wait_for_timeout(1_000)
                await self._page.bring_to_front()
                self._reset_operation_failures()
                return await self._inspect_page()
            except Exception as exc:
                self._state = "error"
                self._detail = f"{type(exc).__name__}: {exc}"
                await self._close_resources()
                raise BrowserSessionError(self._detail) from exc

    async def status(self) -> BrowserStatus:
        async with self._lock:
            if not self._context or not self._page or self._page.is_closed():
                return BrowserStatus(
                    state="stopped",
                    running=False,
                    detail=self._detail,
                    consecutive_failures=self._consecutive_failures,
                    last_error=self._last_error,
                )
            return await self._inspect_page()

    async def scan_chats(self, limit: int, capture_screenshot: bool) -> ChatScanResult:
        async with self._lock:
            page = await self._require_ready_page()
            try:
                conversations = await extract_chat_summaries(page, limit)
            except Exception as exc:
                self._record_operation_failure(exc)
                screenshot_path = await self._screenshot(page, "chat-scan-failed")
                raise BrowserOperationError(str(exc), screenshot_path) from exc
            self._reset_operation_failures()
            screenshot_path = await self._screenshot(page, "chat-scan") if capture_screenshot else None
            return ChatScanResult(
                scanned_at=datetime.now(timezone.utc),
                page_url=page.url,
                conversations=conversations,
                screenshot_path=screenshot_path,
            )

    async def open_chat(self, candidate_name: str, capture_screenshot: bool) -> ChatScanResult:
        async with self._lock:
            page = await self._require_ready_page()
            try:
                if not await click_chat_by_name(page, candidate_name):
                    raise ValueError(f"未在当前沟通列表找到候选人：{candidate_name}")
                detail = await extract_chat_detail(page)
            except Exception as exc:
                self._record_operation_failure(exc)
                screenshot_path = await self._screenshot(page, "chat-open-failed")
                raise BrowserOperationError(str(exc), screenshot_path) from exc
            self._reset_operation_failures()
            screenshot_path = await self._screenshot(page, "chat-detail") if capture_screenshot else None
            return ChatScanResult(
                scanned_at=datetime.now(timezone.utc),
                page_url=page.url,
                conversations=[],
                detail=detail,
                screenshot_path=screenshot_path,
            )

    async def scan_talents(
        self,
        limit: int,
        capture_screenshot: bool,
    ) -> tuple[list[TalentCard], str, str | None]:
        async with self._lock:
            page = await self._require_ready_page()
            config = get_browser_session_config()
            try:
                if "/web/chat/recommend" not in page.url:
                    await page.goto(
                        config.recommend_url,
                        wait_until="domcontentloaded",
                        timeout=30_000,
                    )
                    await page.wait_for_timeout(1_200)
                status = await self._inspect_page()
                if status.state != "ready":
                    raise BrowserSessionError(status.detail or "推荐牛人页面不可读取")
                cards = await extract_talent_cards(page, limit)
            except Exception as exc:
                self._record_operation_failure(exc)
                screenshot_path = await self._screenshot(page, "talent-scan-failed")
                raise BrowserOperationError(str(exc), screenshot_path) from exc
            self._reset_operation_failures()
            screenshot_path = await self._screenshot(page, "talent-scan") if capture_screenshot else None
            return cards, page.url, screenshot_path

    async def _require_ready_page(self) -> Page:
        if not self._context or not self._page or self._page.is_closed():
            raise BrowserSessionError("浏览器会话未启动")
        status = await self._inspect_page()
        if status.state != "ready":
            raise BrowserSessionError(status.detail or f"浏览器状态不可扫描：{status.state}")
        return self._page

    async def _screenshot(self, page: Page, prefix: str) -> str:
        config = get_browser_session_config()
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = Path(config.screenshot_dir) / f"{prefix}-{timestamp}-{uuid4().hex[:8]}.png"
        await page.screenshot(path=str(path), full_page=False)
        return str(path)

    async def stop(self) -> BrowserStatus:
        async with self._lock:
            await self._close_resources()
            self._state = "stopped"
            self._detail = "浏览器会话已停止"
            self._reset_operation_failures()
            return BrowserStatus(state="stopped", running=False, detail=self._detail)

    async def _inspect_page(self) -> BrowserStatus:
        if not self._page or self._page.is_closed():
            return BrowserStatus(state="stopped", running=False, detail=self._detail)
        url = self._page.url
        title = await self._page.title()
        body_text = (await self._page.locator("body").inner_text())[:5000]
        if self._consecutive_failures >= settings.stop_after_automation_failures:
            self._state = "blocked"
            self._detail = (
                f"连续失败 {self._consecutive_failures} 次，自动化已安全停机，请人工检查页面"
            )
        elif any(keyword in body_text for keyword in BLOCKED_KEYWORDS):
            self._state = "blocked"
            self._detail = "检测到验证码、账号异常或访问限制，已禁止继续扫描"
        elif "login" in url.lower() or any(keyword in body_text for keyword in LOGIN_KEYWORDS):
            self._state = "login_required"
            self._detail = "请在浏览器窗口中手工完成 BOSS 直聘登录"
        else:
            self._state = "ready"
            self._detail = "浏览器会话可用，只读扫描已就绪"
        return BrowserStatus(
            state=self._state,
            running=True,
            current_url=url,
            page_title=title or None,
            detail=self._detail,
            consecutive_failures=self._consecutive_failures,
            last_error=self._last_error,
        )

    def _record_operation_failure(self, exc: Exception) -> None:
        self._consecutive_failures += 1
        self._last_error = f"{type(exc).__name__}: {exc}"
        if self._consecutive_failures >= settings.stop_after_automation_failures:
            self._state = "blocked"
            self._detail = (
                f"连续失败 {self._consecutive_failures} 次，自动化已安全停机，请人工检查页面"
            )

    def _reset_operation_failures(self) -> None:
        self._consecutive_failures = 0
        self._last_error = None

    async def _close_resources(self) -> None:
        if self._context:
            await self._context.close()
        if self._playwright:
            await self._playwright.stop()
        self._context = None
        self._page = None
        self._playwright = None


T = TypeVar("T")


class BrowserSessionManager:
    def __init__(self) -> None:
        self._thread_lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._ready = threading.Event()
        self._worker: _BrowserWorker | None = None

    async def start(self) -> BrowserStatus:
        return await self._submit(lambda: self._get_worker().start())

    async def status(self) -> BrowserStatus:
        return await self._submit(lambda: self._get_worker().status())

    async def stop(self) -> BrowserStatus:
        return await self._submit(lambda: self._get_worker().stop())

    async def scan_chats(self, limit: int, capture_screenshot: bool) -> ChatScanResult:
        return await self._submit(lambda: self._get_worker().scan_chats(limit, capture_screenshot))

    async def open_chat(self, candidate_name: str, capture_screenshot: bool) -> ChatScanResult:
        return await self._submit(
            lambda: self._get_worker().open_chat(candidate_name, capture_screenshot)
        )

    async def scan_talents(
        self,
        limit: int,
        capture_screenshot: bool,
    ) -> tuple[list[TalentCard], str, str | None]:
        return await self._submit(
            lambda: self._get_worker().scan_talents(limit, capture_screenshot)
        )

    def _get_worker(self) -> _BrowserWorker:
        if not self._worker:
            raise BrowserSessionError("浏览器 Worker 尚未初始化")
        return self._worker

    async def _submit(self, factory: Callable[[], Coroutine[object, object, T]]) -> T:
        self._ensure_thread()
        if not self._loop:
            raise BrowserSessionError("浏览器 Worker 事件循环未启动")
        future = asyncio.run_coroutine_threadsafe(factory(), self._loop)
        return await asyncio.wrap_future(future)

    def _ensure_thread(self) -> None:
        with self._thread_lock:
            if self._thread and self._thread.is_alive():
                return
            self._ready.clear()
            self._thread = threading.Thread(
                target=self._run_loop,
                name="browser-worker",
                daemon=True,
            )
            self._thread.start()
        if not self._ready.wait(timeout=10):
            raise BrowserSessionError("浏览器 Worker 启动超时")

    def _run_loop(self) -> None:
        if hasattr(asyncio, "ProactorEventLoop"):
            loop = asyncio.ProactorEventLoop()
        else:
            loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        self._worker = _BrowserWorker()
        self._ready.set()
        loop.run_forever()


browser_session_manager = BrowserSessionManager()
