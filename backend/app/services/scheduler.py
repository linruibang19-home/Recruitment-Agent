from __future__ import annotations

from datetime import date

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import settings
from app.db.repositories import audit_logs as audit_repo
from app.db.session import SessionLocal
from app.services.recommendation_service import generate_daily_recommendations


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
    scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
