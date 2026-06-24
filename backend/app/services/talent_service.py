from __future__ import annotations

from app.db.models import Job
from app.schemas.talents import TalentCard, TalentFilter


def filter_talent_cards(
    cards: list[TalentCard],
    filters: TalentFilter,
) -> list[tuple[TalentCard, list[str]]]:
    results: list[tuple[TalentCard, list[str]]] = []
    required_keywords = filters.required_keywords
    for card in cards:
        text = card.raw_text.lower()
        if filters.city and filters.city.lower() not in text and filters.city != card.city:
            continue
        if filters.education and not any(level in card.raw_text for level in filters.education):
            continue
        if filters.experience and not any(value.lower() in text for value in filters.experience):
            continue
        if filters.intentions and not any(value.lower() in text for value in filters.intentions):
            continue
        if filters.salary_keywords and not any(value.lower() in text for value in filters.salary_keywords):
            continue
        matched = [
            keyword
            for keyword in required_keywords
            if keyword.lower() in text
            or any(keyword.lower() in skill.lower() for skill in card.skills)
        ]
        if required_keywords and not matched:
            continue
        results.append((card, matched))
    return results


def greeting_message(card: TalentCard, job: Job) -> str:
    name = card.name or "您好"
    return (
        f"{name}，您好。我们正在招聘“{job.title}”，看到您的经历与岗位方向较匹配。"
        "如果您对该机会感兴趣，方便发送一份 PDF 简历吗？我们会在查看后尽快回复您。"
    )
