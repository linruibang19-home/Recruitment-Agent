from __future__ import annotations

import hashlib
import re
from urllib.parse import parse_qs, urlparse

from playwright.async_api import Locator, Page

from app.schemas.talents import TalentCard


TALENT_CARD_SELECTORS = (
    "[data-recruitment-agent-talent-card]",
    ".recommend-list .candidate-card",
    ".recommend-list .recommend-card",
    ".recommend-card",
    "[class*='recommend-list'] [class*='card']",
    "[class*='geek-card']",
)
EDUCATION_LEVELS = ("博士", "硕士", "本科", "大专", "高中")
SKILL_DICTIONARY = (
    "Python", "Java", "C++", "Go", "JavaScript", "TypeScript", "React", "Vue",
    "Spring", "SpringBoot", "FastAPI", "Django", "MySQL", "PostgreSQL", "Redis",
    "Docker", "Kubernetes", "Linux", "PyTorch", "TensorFlow", "LangChain",
    "LangGraph", "RAG", "LLM", "NLP", "OCR", "机器学习", "深度学习", "数据分析",
)


async def _text(locator: Locator, selectors: tuple[str, ...]) -> str | None:
    for selector in selectors:
        child = locator.locator(selector).first
        if await child.count():
            value = " ".join((await child.inner_text()).split())
            if value:
                return value
    return None


def _uid(href: str | None, raw_text: str) -> str:
    if href:
        query = parse_qs(urlparse(href).query)
        for key in ("uid", "geekId", "encryptGeekId", "id"):
            if query.get(key):
                return query[key][0]
        path_tail = urlparse(href).path.rstrip("/").split("/")[-1]
        if path_tail and path_tail not in ("recommend", "geek"):
            return path_tail
    return hashlib.sha256(raw_text.encode("utf-8")).hexdigest()[:24]


async def extract_talent_cards(page: Page, limit: int) -> list[TalentCard]:
    cards: Locator | None = None
    for selector in TALENT_CARD_SELECTORS:
        locator = page.locator(selector)
        if await locator.count():
            cards = locator
            break
    if cards is None:
        return []

    results: list[TalentCard] = []
    for index in range(min(await cards.count(), limit)):
        card = cards.nth(index)
        raw_text = " ".join((await card.inner_text()).split())
        if not raw_text:
            continue
        name = await _text(card, (".name", "[class*='name']", "[data-name]"))
        href = await card.get_attribute("href")
        if not href and await card.locator("a").count():
            href = await card.locator("a").first.get_attribute("href")
        age_match = re.search(r"(\d{2})岁", raw_text)
        year_match = re.search(r"(20\d{2})年?(?:毕业|应届)", raw_text)
        salary_match = re.search(r"(\d+(?:-\d+)?K|\d+-\d+元/天|薪资面议)", raw_text, re.IGNORECASE)
        education = next((level for level in EDUCATION_LEVELS if level in raw_text), None)
        school = await _text(card, (".school", "[class*='school']", "[data-school]"))
        intention = await _text(card, (".expect", ".intention", "[class*='expect']", "[data-intention]"))
        experience = await _text(card, (".experience", "[class*='experience']", "[data-experience]"))
        city = await _text(card, (".city", "[class*='city']", "[data-city]"))
        major = await _text(card, (".major", "[class*='major']", "[data-major]"))
        skills = [skill for skill in SKILL_DICTIONARY if skill.lower() in raw_text.lower()]
        results.append(
            TalentCard(
                boss_uid=_uid(href, raw_text),
                name=name or raw_text.split(" ")[0],
                age=int(age_match.group(1)) if age_match else None,
                city=city,
                education_level=education,
                school=school,
                major=major,
                graduation_year=int(year_match.group(1)) if year_match else None,
                candidate_type="校招" if any(key in raw_text for key in ("应届", "在校", "校招")) else None,
                experience=experience,
                intention=intention,
                expected_salary=salary_match.group(1) if salary_match else None,
                skills=skills,
                href=href,
                raw_text=raw_text,
            )
        )
    return results
