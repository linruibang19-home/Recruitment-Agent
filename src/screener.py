"""阶段2a: 智能筛选。

职责: 按配置的筛选条件拉取候选人 → 让 LLM 评估技能匹配度 → 排序。

练习点: Tool Use + 配额优先级调度。不是无差别打招呼,
而是先评分排序,把每日 80 个额度优先给高质量候选人。
"""
from __future__ import annotations

import json

from config import cfg
from db import upsert_candidate


def screen_candidates(raw_cards: list[dict]) -> list[dict]:
    """对一批候选人卡片评估匹配度并排序(高分优先)。

    raw_cards: 来自 browser_session 的候选人卡片列表
    返回: [{boss_id, card, skill_match}, ...] 按 skill_match 降序
    """
    threshold = cfg.get("screening.skill_match_threshold", 0.6)
    jd = _build_jd_text()
    scored = []
    for card in raw_cards:
        boss_id = card.get("boss_id") or card.get("name", "")
        match = _estimate_match(card.get("skills", ""), jd)
        if match < threshold:
            continue  # 不达标不占额度
        upsert_candidate(
            boss_id=str(boss_id),
            name=card.get("name"),
            title=card.get("title"),
            company=card.get("company"),
            card_json=card,
            skill_match=match,
            status="new",
        )
        scored.append({"boss_id": str(boss_id), "card": card, "skill_match": match})
    scored.sort(key=lambda x: x["skill_match"], reverse=True)
    return scored


def _build_jd_text() -> str:
    """把配置里的岗位要求拼成一段 JD 文本,供匹配评估。"""
    s = cfg.get("screening", {})
    parts = [
        f"岗位: {s.get('job_title')}",
        f"经验: {s.get('experience')}",
        f"学历: {s.get('education')}",
        f"行业偏好: {','.join(s.get('industry_prefs', []))}",
    ]
    return "; ".join(parts)


def _estimate_match(candidate_skills: str, jd: str) -> float:
    """轻量关键词重合度估算(可被工具 estimate_skill_match 取代)。

    这里用纯本地估算避免每条都调 LLM(省钱)。LLM 版本在 tools/boss_tools 里。
    """
    if not candidate_skills or not jd:
        return 0.0
    cand = set(_tokenize(candidate_skills))
    req = set(_tokenize(jd))
    if not req:
        return 0.0
    return round(len(cand & req) / len(req), 3)


def _tokenize(text: str) -> set[str]:
    return {t for t in text.lower().replace(",", " ").replace(";", " ").split() if len(t) > 1}
