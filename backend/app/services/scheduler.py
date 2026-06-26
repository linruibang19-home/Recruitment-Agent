from __future__ import annotations

import random
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select

from app.core.config import settings
from app.db.models import ExtensionCommand
from app.db.repositories import audit_logs as audit_repo
from app.db.session import SessionLocal
from app.services import extension_service
from app.services.recommendation_service import generate_daily_recommendations
from app.services.quota import greeting_quota_status


SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
CHAT_LOOP_MESSAGE = "方便发一份你的简历过来吗？"

_chat_loop_state = {
    "enabled": False,
    "next_enqueue_at": None,
    "last_enqueue_at": None,
    "last_command_id": None,
    "last_message": "未启动",
}


def _run_daily_recommendation() -> None:
    with SessionLocal() as db:
        try:
            result = generate_daily_recommendations(
                db,
                recommendation_date=date.today(),
                top_n=settings.recommendation_top_n,
                create_interview_drafts=True,
            )
            audit_repo.create_audit_log(
                db,
                action_type="daily_recommendation_schedule",
                status="ok",
                detail=f"定时生成 {result.recommendations_created} 条推荐",
                payload={"drafts_created": result.drafts_created},
            )
        except Exception as exc:
            db.rollback()
            audit_repo.create_audit_log(
                db,
                action_type="daily_recommendation_schedule",
                status="failed",
                detail=f"{type(exc).__name__}: {exc}",
            )


scheduler = BackgroundScheduler(timezone="Asia/Shanghai")


def _now_local() -> datetime:
    return datetime.now(SHANGHAI_TZ)


def _next_gap() -> timedelta:
    minimum = max(1, settings.chat_loop_min_gap_minutes)
    maximum = max(minimum, settings.chat_loop_max_gap_minutes)
    return timedelta(minutes=random.randint(minimum, maximum))


def chat_loop_status() -> dict:
    return {
        **_chat_loop_state,
        "running": bool(_chat_loop_state["enabled"]),
    }


def start_chat_loop() -> dict:
    _chat_loop_state["enabled"] = True
    _chat_loop_state["next_enqueue_at"] = _now_local()
    _chat_loop_state["last_message"] = "已启动，等待扩展领取下一批任务"
    _run_chat_resume_loop()
    return chat_loop_status()


def pause_chat_loop() -> dict:
    _chat_loop_state["enabled"] = False
    _chat_loop_state["last_message"] = "已暂停，不再创建新的批量索要任务"
    return chat_loop_status()


def _has_pending_resume_request_command(db) -> bool:
    return bool(
        db.scalar(
            select(ExtensionCommand.id)
            .where(
                ExtensionCommand.command_type == "request_resumes_batch",
                ExtensionCommand.status.in_(("queued", "running")),
            )
            .limit(1)
        )
    )


def _run_chat_resume_loop() -> None:
    if not _chat_loop_state["enabled"]:
        return
    now = _now_local()
    next_enqueue_at = _chat_loop_state["next_enqueue_at"]
    if isinstance(next_enqueue_at, datetime) and now < next_enqueue_at:
        return
    with SessionLocal() as db:
        try:
            session = extension_service.latest_session(db)
            if not extension_service.is_connected(session):
                _chat_loop_state["last_message"] = "Chrome 扩展未连接，等待已登录的 BOSS 页面"
                _chat_loop_state["next_enqueue_at"] = now + timedelta(minutes=1)
                return
            quota = greeting_quota_status(db)
            if quota.available_count <= 0:
                _chat_loop_state["enabled"] = False
                _chat_loop_state["last_message"] = "今日主动触达额度已用完，自动循环已停止"
                audit_repo.create_audit_log(
                    db,
                    action_type="chat_resume_loop",
                    status="ok",
                    detail="今日主动触达额度已用完，自动循环已停止",
                    payload={"available_count": quota.available_count, "max_count": quota.max_count},
                )
                return
            if _has_pending_resume_request_command(db):
                _chat_loop_state["last_message"] = "已有批量索要任务排队或运行中，暂不创建新批次"
                _chat_loop_state["next_enqueue_at"] = now + timedelta(minutes=1)
                return
            limit = min(settings.chat_loop_batch_limit, quota.available_count)
            command = extension_service.create_command(
                db,
                command_type="request_resumes_batch",
                payload={
                    "limit": limit,
                    "delay_ms": random.randint(
                        settings.chat_loop_min_delay_ms,
                        settings.chat_loop_max_delay_ms,
                    ),
                    "message": CHAT_LOOP_MESSAGE,
                    "source": "chat_loop",
                },
            )
            gap = _next_gap()
            _chat_loop_state["last_enqueue_at"] = now
            _chat_loop_state["next_enqueue_at"] = now + gap
            _chat_loop_state["last_command_id"] = command.id
            _chat_loop_state["last_message"] = f"已创建批量索要任务 #{command.id}，下一次约 {int(gap.total_seconds() // 60)} 分钟后"
            audit_repo.create_audit_log(
                db,
                action_type="chat_resume_loop",
                status="ok",
                detail=_chat_loop_state["last_message"],
                payload={
                    "command_id": command.id,
                    "limit": limit,
                    "next_enqueue_at": _chat_loop_state["next_enqueue_at"].isoformat(),
                },
            )
        except Exception as exc:
            db.rollback()
            _chat_loop_state["last_message"] = f"{type(exc).__name__}: {exc}"
            _chat_loop_state["next_enqueue_at"] = now + timedelta(minutes=2)
            audit_repo.create_audit_log(
                db,
                action_type="chat_resume_loop",
                status="failed",
                detail=_chat_loop_state["last_message"],
            )


def start_scheduler() -> None:
    if scheduler.running:
        return
    scheduler.add_job(
        _run_daily_recommendation,
        trigger="cron",
        hour=settings.recommendation_hour,
        minute=0,
        id="daily-recommendation",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        _run_chat_resume_loop,
        trigger="interval",
        minutes=1,
        id="chat-resume-loop",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
