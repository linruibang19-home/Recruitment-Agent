"""FAQ 检索与自我增长。

练习点: 长期记忆 / 自我演进雏形。reply_agent 遇到答不上的问题,
可调 faq_suggest_pending 让人补;补完入库后,下次同类问题 Agent 自己能答。
"""
from __future__ import annotations

from db import faq_add, faq_answer


def lookup(question: str) -> str | None:
    return faq_answer(question)


def add(question: str, answer: str) -> None:
    faq_add(question, answer)
