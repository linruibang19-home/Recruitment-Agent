"""阶段6: 高优先级跟进 + 自动约面。

对评分 > high_priority_threshold 的候选人:
  - 主动发更详细岗位介绍 / 回答问题 / 推联系方式
  - 表达面试意向后,提出 3 个可选时间,确认后发面试邀请
"""
from __future__ import annotations

from config import cfg
from db import get_candidate, log_interaction, interaction_history
from llm_client import llm

FOLLOWUP_SYSTEM = """你是招聘助理。对方是高分候选人,你正在深度跟进以促成面试。
要求:
1. 记住此前的对话(会一并提供),保持上下文一致。
2. 对方表达任何面试意向 → 提出 3 个具体可选时间(用占位符,真实时间由人工/日历确认)。
3. 自然、有诚意,不要重复已说过的话。
只输出要发给对方的消息。"""


def maybe_followup(session, boss_id: str) -> bool:
    """对高分候选人发一条跟进。返回是否发了。"""
    cand = get_candidate(boss_id)
    if not cand:
        return False
    threshold = cfg.get("scoring.high_priority_threshold", 80)
    if (cand.get("score") or 0) < threshold:
        return False

    history = interaction_history(boss_id)
    history_text = "\n".join(
        f"[{'我' if h['direction']=='out' else '对方'}] {h.get('content','')}"
        for h in history[-6:]
    )
    msg = llm.chat([
        {"role": "system", "content": FOLLOWUP_SYSTEM},
        {"role": "user", "content": f"候选人画像分数: {cand.get('score')}\n历史对话:\n{history_text}"},
    ]).strip()
    if session.send_message(msg):
        log_interaction(boss_id, "out", "followup", msg)
        return True
    return False
