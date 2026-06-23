"""主调度器: 把 6 个阶段串成"每日筛选窗口 + 定时巡检"两个循环。

练习点: 驻留型 Agent 的形态不是一次性流水线,而是
  - 每日: 在打招呼时段内跑筛选→打招呼(有窗口判断)
  - 持续: 每 30 分钟巡检回复 + 对高分候选人跟进
用 APScheduler 注册定时任务,所有任务都用 safety 包裹,风控即停。
"""
from __future__ import annotations

import asyncio
import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

import humanize
from config import cfg
from safety import SafetyStop, notify_human
from browser_session import get_session


async def daily_run() -> None:
    """每日打招呼流程: 启动浏览器 → 登录自检 → 筛选 → 打招呼。"""
    session = get_session()
    try:
        await session.start()
        if not await session.ensure_logged_in():
            return  # 已通知人扫码

        # 筛选: 真实实现用 browser-use 拉候选人卡片
        import screener, greeter
        raw_cards = await _fetch_candidate_cards(session)
        scored = screener.screen_candidates(raw_cards)
        report = greeter.greet_batch(scored, session)
        _log_daily_report(report)
    except SafetyStop as e:
        notify_human(f"每日流程因风控中止: {e}")
    finally:
        await session.close()


async def watch_loop() -> None:
    """巡检: 读新回复 → 交 reply_agent → 对高分候选人跟进。"""
    session = get_session()
    try:
        await session.start()
        if not await session.ensure_logged_in():
            return
        import watcher, followuper
        from db import list_by_status
        report = await watcher.poll_once(session)
        for cand in list_by_status("replied"):
            followuper.maybe_followup(session, cand["boss_id"])
        _log_watch_report(report)
    except SafetyStop as e:
        notify_human(f"巡检因风控中止: {e}")
    finally:
        await session.close()


# ---------- 占位: 真实实现对接 Boss DOM ----------

async def _fetch_candidate_cards(session) -> list[dict]:
    """根据 config.screening 打开 Boss 搜索页并抓候选人卡片。占位返回空。"""
    # TODO(对接Boss): session.open_url(搜索URL) → browser-use 解析卡片列表
    return []


def _log_daily_report(report: dict) -> None:
    ts = datetime.datetime.now().isoformat(timespec="seconds")
    line = f"[{ts}] DAILY greeted={report.get('greeted')} stopped={report.get('stopped_reason')}\n"
    _append_log(line)


def _log_watch_report(report: dict) -> None:
    ts = datetime.datetime.now().isoformat(timespec="seconds")
    line = (f"[{ts}] WATCH new={report.get('new_messages')} "
            f"handled={report.get('handled')} human={report.get('needs_human')}\n")
    _append_log(line)


def _append_log(line: str) -> None:
    from config import cfg
    p = cfg.path("logs_dir") / "run.log"
    with p.open("a", encoding="utf-8") as f:
        f.write(line)


# ---------- 调度注册 ----------

def run() -> None:
    """阻塞运行调度器。"""
    poll_min = cfg.get("watcher.poll_interval_min", 30)

    scheduler = BlockingScheduler()
    scheduler.add_job(
        lambda: asyncio.run(daily_run()),
        IntervalTrigger(minutes=30),  # 内部由 humanize.in_greet_window 判断是否真的打招呼
        id="daily",
        next_run_time=datetime.datetime.now() + datetime.timedelta(seconds=10),
    )
    scheduler.add_job(
        lambda: asyncio.run(watch_loop()),
        IntervalTrigger(minutes=poll_min),
        id="watch",
        next_run_time=datetime.datetime.now() + datetime.timedelta(seconds=15),
    )
    print("[scheduler] 启动。daily 每30分钟触发(窗口内才打招呼),watch 每 "
          f"{poll_min} 分钟巡检。Ctrl+C 退出。")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == "__main__":
    run()
