from pathlib import Path
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.db.models import AuditLog
from app.core.security import redact_data, redact_text


PROJECT_ROOT = Path(__file__).resolve().parents[4]


def _safe_screenshot_path(screenshot_path: str | None) -> str | None:
    if not screenshot_path:
        return None
    path = Path(screenshot_path)
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return "[本地路径]"


def create_audit_log(
    db: Session,
    *,
    action_type: str,
    status: str,
    detail: str | None = None,
    screenshot_path: str | None = None,
    payload: dict[str, Any] | None = None,
) -> AuditLog:
    entry = AuditLog(
        action_type=action_type,
        status=status,
        detail=redact_text(detail),
        screenshot_path=_safe_screenshot_path(screenshot_path),
        payload=redact_data(payload or {}),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def list_audit_logs(
    db: Session,
    *,
    limit: int = 50,
    offset: int = 0,
    status: str | None = None,
    action_type: str | None = None,
) -> tuple[list[AuditLog], int]:
    stmt: Select[tuple[AuditLog]] = select(AuditLog)
    filters = []
    if status:
        filters.append(AuditLog.status == status)
    if action_type:
        filters.append(AuditLog.action_type == action_type)
    if filters:
        stmt = stmt.where(*filters)
    count_stmt = select(func.count()).select_from(AuditLog)
    if filters:
        count_stmt = count_stmt.where(*filters)
    total = db.scalar(count_stmt) or 0
    items = list(db.scalars(stmt.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)))
    return items, total


def get_audit_log(db: Session, audit_log_id: int) -> AuditLog | None:
    return db.get(AuditLog, audit_log_id)
