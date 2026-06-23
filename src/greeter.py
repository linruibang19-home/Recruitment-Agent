"""阶段2b: 批量打招呼(配额管理 + 拟人化节奏 + LLM 个性化招呼语)。

练习点:
  - 配额管理: 每日 80 上限,超额立即停。
  - 拟人化: humanize.human_pause + 随机干扰动作,反风控。
  - LLM 个性化: 每条招呼语单独生成,绝不用同一模板(机器人指纹)。
"""
from __future__ import annotations

import json
import time

import humanize
from config import cfg
from db import daily_greeted, daily_limit, increment_quota, log_interaction
from llm_client import llm
from safety import SafetyStop, notify_human

GREET_SYSTEM = """你是招聘者,正在 Boss 直聘上给候选人发第一句招呼。
要求:
1. 根据候选人信息个性化,提及对方的具体公司/职位/技能,绝不套用固定模板。
2. 简短(2-3 句)、自然、像真人。
3. 结尾自然地引导对方发一份简历(PDF)。
只输出招呼语本身,不要解释。"""


def greet_batch(scored_candidates: list[dict], session) -> dict:
    """对排序后的候选人列表打招呼,直到额度耗尽或时段结束。

    返回执行报告 {greeted, skipped, remaining_quota, stopped_reason}
    """
    day, greeted = daily_greeted()
    limit = daily_limit()
    report = {"greeted": 0, "skipped": 0, "remaining_quota": max(0, limit - greeted),
              "stopped_reason": None}

    for cand in scored_candidates:
        if greeted >= limit:
            report["stopped_reason"] = "quota_exhausted"
            break
        if not humanize.in_greet_window():
            report["stopped_reason"] = "out_of_window"
            break

        try:
            _greet_one(session, cand)
            greeted = increment_quota()
            report["greeted"] += 1
        except SafetyStop as e:
            report["stopped_reason"] = f"safety_stop: {e}"
            notify_human(f"打招呼过程中触发风控刹车: {e}")
            break

        # 拟人化节奏: 真实停顿 + 偶尔干扰动作
        time.sleep(humanize.human_pause("greet"))
        if humanize.should_distract():
            _do_distraction(session)

    report["remaining_quota"] = max(0, limit - daily_greeted()[1])
    return report


def _greet_one(session, cand: dict) -> None:
    boss_id = cand["boss_id"]
    card = cand["card"]
    jd = _short_jd()
    message = llm.chat(
        [{"role": "system", "content": GREET_SYSTEM},
         {"role": "user", "content": f"候选人: {json.dumps(card, ensure_ascii=False)}\n岗位要求: {jd}"}],
    ).strip()
    if not session.send_message(message):
        raise SafetyStop(f"向 {boss_id} 发送失败,疑似风控")
    log_interaction(boss_id, "out", "greet", message)
    from db import upsert_candidate
    upsert_candidate(boss_id=boss_id, status="greeted")


def _do_distraction(session) -> None:
    """执行一个无意义但像人的浏览动作。真实实现由 session 解释。"""
    action = humanize.random_distraction()
    # TODO(对接Boss): session 上没有这个方法时安全跳过
    try:
        getattr(session, action, lambda: None)()
    except Exception:
        pass


def _short_jd() -> str:
    s = cfg.get("screening", {})
    return f"{s.get('job_title')} | {s.get('experience')} | {','.join(s.get('industry_prefs', []))}"
