from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import ActionQueueItem, DailyQuota
from app.schemas.talents import GreetingQuotaRead


QUOTA_TYPE = "boss_greeting"
SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")


def get_or_create_greeting_quota(db: Session, quota_date: date | None = None) -> DailyQuota:
    target_date = quota_date or date.today()
    quota = db.scalar(
        select(DailyQuota).where(
            DailyQuota.quota_date == target_date,
            DailyQuota.quota_type == QUOTA_TYPE,
        )
    )
    if quota:
        return quota
    quota = DailyQuota(
        quota_date=target_date,
        quota_type=QUOTA_TYPE,
        used_count=0,
        max_count=settings.max_daily_greetings,
    )
    db.add(quota)
    db.flush()
    return quota


def greeting_quota_status(db: Session, quota_date: date | None = None) -> GreetingQuotaRead:
    quota = get_or_create_greeting_quota(db, quota_date)
    target_date = quota.quota_date
    start_local = datetime.combine(target_date, time.min, tzinfo=SHANGHAI_TZ)
    end_local = start_local + timedelta(days=1)
    start = start_local.astimezone(timezone.utc)
    end = end_local.astimezone(timezone.utc)
    base = (
        ActionQueueItem.action_type == "request_resume_greeting",
        ActionQueueItem.created_at >= start,
        ActionQueueItem.created_at < end,
    )
    pending = db.scalar(
        select(func.count()).select_from(ActionQueueItem).where(*base, ActionQueueItem.status == "pending")
    ) or 0
    approved = db.scalar(
        select(func.count()).select_from(ActionQueueItem).where(*base, ActionQueueItem.status == "approved")
    ) or 0
    reserved = quota.used_count + pending + approved
    return GreetingQuotaRead(
        quota_date=target_date,
        used_count=quota.used_count,
        max_count=quota.max_count,
        pending_count=pending,
        approved_count=approved,
        available_count=max(0, quota.max_count - reserved),
    )
