from __future__ import annotations

import re

from playwright.async_api import Locator, Page

from app.schemas.automation import AttachmentInfo, ChatDetail, ChatSummary


CHAT_ITEM_SELECTORS = (
    ".user-list .user-item",
    ".chat-list .chat-item",
    ".chat-list .friend-item",
    ".friend-list .friend-item",
    "[class*='chat-list'] [class*='item']",
)
MESSAGE_SELECTORS = (
    ".chat-message",
    ".message-item",
    ".message-content",
    "[class*='message-item']",
)
ATTACHMENT_SELECTORS = (
    "a[href*='.pdf']",
    "[class*='attachment']",
    "[class*='resume']",
    "[class*='file-card']",
)
PDF_FILENAME_RE = re.compile(r"[^\\/:*?\"<>|\r\n]+\.pdf", re.IGNORECASE)


async def _first_non_empty_text(locator: Locator, selectors: tuple[str, ...]) -> str | None:
    for selector in selectors:
        child = locator.locator(selector).first
        if await child.count():
            text = (await child.inner_text()).strip()
            if text:
                return text
    return None


async def find_chat_items(page: Page) -> Locator:
    for selector in CHAT_ITEM_SELECTORS:
        locator = page.locator(selector)
        if await locator.count():
            return locator
    return page.locator("[data-recruitment-agent-chat-item]")


async def extract_chat_summaries(page: Page, limit: int) -> list[ChatSummary]:
    items = await find_chat_items(page)
    results: list[ChatSummary] = []
    for index in range(min(await items.count(), limit)):
        item = items.nth(index)
        raw_text = " ".join((await item.inner_text()).split())
        if not raw_text:
            continue
        name = await _first_non_empty_text(
            item,
            (".name", ".user-name", ".friend-name", "[class*='name']"),
        )
        preview = await _first_non_empty_text(
            item,
            (".last-msg", ".preview", ".message-text", "[class*='last']"),
        )
        unread_text = await _first_non_empty_text(
            item,
            (".badge", ".unread", "[class*='unread']"),
        )
        href = await item.get_attribute("href")
        if not href:
            href = await item.locator("a").first.get_attribute("href") if await item.locator("a").count() else None
        unread_match = re.search(r"\d+", unread_text or "")
        results.append(
            ChatSummary(
                name=name or raw_text.split(" ")[0],
                preview=preview,
                unread_count=int(unread_match.group()) if unread_match else 0,
                href=href,
                raw_text=raw_text,
            )
        )
    return results


async def extract_chat_detail(page: Page) -> ChatDetail:
    candidate_name = None
    for selector in (
        ".chat-header .name",
        ".conversation-header [class*='name']",
        "[data-recruitment-agent-candidate-name]",
    ):
        locator = page.locator(selector).first
        if await locator.count():
            candidate_name = (await locator.inner_text()).strip() or None
            if candidate_name:
                break

    messages: list[str] = []
    seen_messages: set[str] = set()
    for selector in MESSAGE_SELECTORS:
        locators = page.locator(selector)
        if not await locators.count():
            continue
        for index in range(min(await locators.count(), 100)):
            text = " ".join((await locators.nth(index).inner_text()).split())
            if text and text not in seen_messages:
                seen_messages.add(text)
                messages.append(text)
        if messages:
            break

    attachments: list[AttachmentInfo] = []
    seen_attachments: set[tuple[str | None, str | None]] = set()
    for selector in ATTACHMENT_SELECTORS:
        locators = page.locator(selector)
        for index in range(min(await locators.count(), 50)):
            locator = locators.nth(index)
            text = " ".join((await locator.inner_text()).split())
            href = await locator.get_attribute("href")
            filename_match = PDF_FILENAME_RE.search(text) or PDF_FILENAME_RE.search(href or "")
            is_pdf = bool(filename_match) or ".pdf" in text.lower() or ".pdf" in (href or "").lower()
            if not is_pdf and not any(keyword in text for keyword in ("附件简历", "在线简历", "预览附件")):
                continue
            filename = filename_match.group() if filename_match else None
            key = (filename, href)
            if key in seen_attachments:
                continue
            seen_attachments.add(key)
            attachments.append(
                AttachmentInfo(
                    filename=filename,
                    attachment_type="pdf" if is_pdf else "resume_card",
                    preview_text=text or None,
                    href=href,
                )
            )
    return ChatDetail(candidate_name=candidate_name, messages=messages, attachments=attachments)


async def click_chat_by_name(page: Page, candidate_name: str) -> bool:
    items = await find_chat_items(page)
    for index in range(await items.count()):
        item = items.nth(index)
        text = " ".join((await item.inner_text()).split())
        if candidate_name in text:
            await item.click()
            await page.wait_for_timeout(800)
            return True
    return False
