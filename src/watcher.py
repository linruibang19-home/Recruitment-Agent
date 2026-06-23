"""阶段3a: 巡检 Boss 消息页,拉取新回复交给 reply_agent 处理。

职责: 周期性轮询 → 检测新消息 → 去重 → 交给 reply_agent 做意图理解与回复。
"""
from __future__ import annotations

import time

from db import interaction_history, log_interaction
from reply_agent import handle_reply


async def poll_once(session) -> dict:
    """巡检一次。返回 {new_messages, handled, needs_human}。

    真实实现需用 browser-use 读取消息列表并识别"未读/新"。
    """
    report = {"new_messages": 0, "handled": 0, "needs_human": 0}
    # TODO(对接Boss): 从消息页解析 [{boss_id, content, ts}] 列表
    new_messages: list[dict] = await _fetch_new_messages(session)

    for msg in new_messages:
        report["new_messages"] += 1
        boss_id = msg["boss_id"]
        # 去重: 同内容同候选人的消息已处理过则跳过
        if _already_seen(boss_id, msg["content"]):
            continue
        log_interaction(boss_id, "in", "reply", msg["content"])
        outcome = handle_reply(session, boss_id, msg["content"])
        if outcome.get("needs_human"):
            report["needs_human"] += 1
        else:
            report["handled"] += 1
    return report


async def _fetch_new_messages(session) -> list[dict]:
    """从 Boss 消息页抓取新消息。占位:返回空,真实实现对接 DOM。"""
    return []


def _already_seen(boss_id: str, content: str) -> bool:
    for it in interaction_history(boss_id):
        if it.get("direction") == "in" and it.get("content") == content:
            return True
    return False
