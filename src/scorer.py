"""阶段5a: 多维加权评分。

练习点: 自评输出质量。画像生成后,基于画像字段 + 互动数据做加权打分,
作为"Agent 对自己产出画像的质量判断"。权重可配置,留口子未来回灌录用结果做学习。
"""
from __future__ import annotations

from db import interaction_history
from config import cfg
from db import get_candidate


def score(boss_id: str) -> float:
    """对候选人加权评分并存回。返回总分(0-100)。"""
    cand = get_candidate(boss_id)
    if not cand:
        return 0.0
    profile = cand.get("profile_json") or {}
    card = cand.get("card_json") or {}

    dims = {
        "skill_match": _skill(profile, card),
        "experience_match": _experience(profile),
        "stability": _stability(profile),
        "growth": _growth(profile),
        "communication": _communication(boss_id),
    }
    weights = cfg.get("scoring.weights", {})
    total = sum(dims[k] * weights.get(k, 0) for k in dims) * 100  # 归一到 100

    from db import get_conn
    import time
    with get_conn() as conn:
        conn.execute("UPDATE candidates SET score=?, updated_at=? WHERE boss_id=?",
                     (round(total, 1), time.time(), boss_id))
    return round(total, 1)


# ---- 各维度 0-1 归一 ----

def _skill(profile: dict, card: dict) -> float:
    base = card.get("skill_match") if isinstance(card, dict) else None
    if base is not None:
        return float(base)
    matrix = profile.get("skill_matrix", {})
    if not matrix:
        return 0.5
    return min(1.0, sum(matrix.values()) / (len(matrix) * 5))


def _experience(profile: dict) -> float:
    years = (profile.get("basic") or {}).get("years_exp", 0) or 0
    # 经验 3-5 年给满分,线性衰减
    if 3 <= years <= 6:
        return 1.0
    return max(0.2, min(1.0, years / 5.0))


def _stability(profile: dict) -> float:
    # 画像 risks 里提到跳槽频繁则降分
    risks = " ".join(profile.get("risks", []))
    if any(k in risks for k in ["跳槽", "频繁", "短期"]):
        return 0.4
    return 0.8


def _growth(profile: dict) -> float:
    highlights = profile.get("highlights", [])
    if any(k in " ".join(highlights) for k in ["从0到1", "搭建", "主导", "管理"]):
        return 1.0
    return 0.5


def _communication(boss_id: str) -> float:
    # 回复速度快、主动 = 高分。这里用互动次数近似。
    history = interaction_history(boss_id)
    in_msgs = [h for h in history if h.get("direction") == "in"]
    if len(in_msgs) >= 3:
        return 1.0
    if len(in_msgs) >= 1:
        return 0.7
    return 0.3
