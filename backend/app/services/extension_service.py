from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    ActionQueueItem,
    Candidate,
    ExtensionCommand,
    ExtensionSession,
    Interaction,
)
from app.db.repositories import audit_logs as audit_repo
from app.db.repositories import talents as talent_repo
from app.schemas.extension import ExtensionHeartbeat
from app.schemas.talents import TalentCard, TalentFilter
from app.services.quota import greeting_quota_status
from app.services.talent_service import filter_talent_cards, greeting_message


ONLINE_WINDOW = timedelta(seconds=20)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def record_heartbeat(db: Session, payload: ExtensionHeartbeat) -> ExtensionSession:
    session = db.scalar(
        select(ExtensionSession).where(ExtensionSession.extension_id == payload.extension_id)
    )
    if session is None:
        session = ExtensionSession(extension_id=payload.extension_id)
    session.status = payload.status
    session.page_url = payload.page_url
    session.page_title = payload.page_title
    session.page_type = payload.page_type
    session.last_seen_at = _now()
    session.metadata_json = payload.metadata
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def latest_session(db: Session) -> ExtensionSession | None:
    return db.scalar(
        select(ExtensionSession).order_by(ExtensionSession.last_seen_at.desc()).limit(1)
    )


def is_connected(session: ExtensionSession | None) -> bool:
    return bool(
        session
        and session.status == "online"
        and session.last_seen_at >= _now() - ONLINE_WINDOW
    )


def create_command(
    db: Session, *, command_type: str, payload: dict[str, Any]
) -> ExtensionCommand:
    if command_type == "request_resumes_batch":
        safe_payload = {
            **payload,
            "limit": min(int(payload.get("limit") or 20), 20),
            "message": str(payload.get("message") or "方便发一份你的简历过来吗？"),
            "only_unread": True,
            "read_only": False,
            "auto_send": True,
            "control": "running",
        }
    else:
        safe_payload = {**payload, "read_only": True, "auto_send": False, "control": "running"}
    command = ExtensionCommand(
        command_type=command_type,
        status="queued",
        payload=safe_payload,
    )
    db.add(command)
    db.commit()
    db.refresh(command)
    return command


def command_control(db: Session, command_id: int) -> str:
    command = db.get(ExtensionCommand, command_id)
    if command is None:
        return "stopped"
    control = (command.payload or {}).get("control")
    return control if control in {"running", "paused", "stopped"} else "running"


def update_command_control(db: Session, command_id: int, control: str) -> ExtensionCommand:
    command = db.get(ExtensionCommand, command_id)
    if command is None:
        raise ValueError("extension command not found")
    if command.status not in {"queued", "running"}:
        raise ValueError(f"cannot control command in status {command.status}")
    command.payload = {**(command.payload or {}), "control": control}
    db.add(command)
    db.commit()
    db.refresh(command)
    return command


def claim_next_command(db: Session, extension_id: str) -> ExtensionCommand | None:
    command = db.scalar(
        select(ExtensionCommand)
        .where(ExtensionCommand.status == "queued")
        .order_by(ExtensionCommand.created_at.asc())
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if command is None:
        return None
    command.status = "running"
    command.extension_id = extension_id
    command.claimed_at = _now()
    db.commit()
    db.refresh(command)
    return command


def _stable_uid(name: str, href: str | None, raw_text: str) -> str:
    source = href or f"{name}|{raw_text}"
    return f"chat-{hashlib.sha256(source.encode('utf-8')).hexdigest()[:24]}"


def _upsert_chat_candidate(db: Session, data: dict[str, Any]) -> Candidate:
    name = str(data.get("candidate_name") or data.get("name") or "未命名候选人").strip()
    href = data.get("href")
    raw_text = str(data.get("raw_text") or "")
    boss_uid = str(data.get("boss_uid") or _stable_uid(name, href, raw_text))
    candidate = db.scalar(select(Candidate).where(Candidate.boss_uid == boss_uid))
    if candidate is None:
        candidate = Candidate(boss_uid=boss_uid, source="boss_chat")
    candidate.name = name
    candidate.source = "boss_chat"
    candidate.raw_card = {
        **(candidate.raw_card or {}),
        "href": href,
        "raw_text": raw_text,
        "last_collected_at": _now().isoformat(),
    }
    db.add(candidate)
    db.flush()
    return candidate


def _message_hash(candidate_id: int, message: dict[str, Any]) -> str:
    value = "|".join(
        [
            str(candidate_id),
            str(message.get("direction") or "in"),
            str(message.get("content") or ""),
            str(message.get("time") or ""),
        ]
    )
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _save_messages(db: Session, candidate: Candidate, messages: list[Any]) -> int:
    created = 0
    for item in messages[:200]:
        message = item if isinstance(item, dict) else {"content": str(item), "direction": "in"}
        content = str(message.get("content") or "").strip()
        if not content:
            continue
        digest = _message_hash(candidate.id, message)
        duplicate = db.scalar(
            select(Interaction.id).where(
                Interaction.candidate_id == candidate.id,
                Interaction.payload["message_hash"].astext == digest,
            )
        )
        if duplicate:
            continue
        direction = message.get("direction")
        if direction not in {"in", "out", "system"}:
            direction = "in"
        db.add(
            Interaction(
                candidate_id=candidate.id,
                direction=direction,
                kind="chat_message",
                content=content,
                payload={"message_hash": digest, "source": "chrome_extension"},
            )
        )
        created += 1
    return created


def _ensure_resume_draft(db: Session, candidate: Candidate) -> ActionQueueItem | None:
    existing = db.scalar(
        select(ActionQueueItem).where(
            ActionQueueItem.candidate_id == candidate.id,
            ActionQueueItem.action_type == "request_resume_chat",
            ActionQueueItem.status.in_(("pending", "approved")),
        )
    )
    if existing:
        return None
    action = ActionQueueItem(
        candidate_id=candidate.id,
        action_type="request_resume_chat",
        status="pending",
        risk_level="medium",
        draft_message=(
            f"{candidate.name or '您好'}，您好。为了进一步评估您与岗位的匹配度，"
            "方便发送一份 PDF 格式的最新简历吗？收到后我们会尽快查看并回复。"
        ),
        payload={"source": "boss_chat", "auto_send": False},
    )
    db.add(action)
    return action


def ingest_chat_result(db: Session, result: dict[str, Any]) -> tuple[int | None, list[str], list[dict[str, Any]]]:
    details = [
        item
        for item in result.get("details") or []
        if isinstance(item, dict) and (item.get("candidate_name") or item.get("messages"))
    ]
    if details:
        first_candidate_id: int | None = None
        first_attachment_urls: list[str] = []
        attachment_uploads: list[dict[str, Any]] = []
        for detail_item in details[:100]:
            nested_result = {**result, "detail": detail_item, "details": []}
            candidate_id, attachment_urls, _ = ingest_chat_result(db, nested_result)
            if candidate_id is None:
                continue
            if first_candidate_id is None:
                first_candidate_id = candidate_id
                first_attachment_urls = attachment_urls
            if attachment_urls:
                attachment_uploads.append(
                    {
                        "candidate_id": candidate_id,
                        "attachment_urls": attachment_urls,
                        "job_id": result.get("job_id"),
                    }
                )
        return first_candidate_id, first_attachment_urls, attachment_uploads

    detail = result.get("detail") or result
    conversations = result.get("conversations") or []
    if not detail.get("candidate_name") and conversations:
        for summary in conversations[:100]:
            _upsert_chat_candidate(db, summary)
        db.commit()
        return None, [], []

    if not (
        detail.get("candidate_name")
        or detail.get("name")
        or detail.get("messages")
        or detail.get("attachments")
    ):
        audit_repo.create_audit_log(
            db,
            action_type="extension_chat_ingest",
            status="failed",
            detail="扩展未在当前 BOSS 沟通页识别到会话或聊天详情",
            payload={"page_url": result.get("page_url")},
        )
        return None, [], []

    candidate = _upsert_chat_candidate(db, detail)
    message_count = _save_messages(db, candidate, detail.get("messages") or [])
    attachments = detail.get("attachments") or []
    attachment_urls = [
        str(item["href"])
        for item in attachments
        if isinstance(item, dict) and item.get("href")
    ]
    if attachments:
        candidate.status = "resume_requested"
        existing_attachment = db.scalar(
            select(ActionQueueItem).where(
                ActionQueueItem.candidate_id == candidate.id,
                ActionQueueItem.action_type == "resume_attachment_detected",
                ActionQueueItem.status == "pending",
            )
        )
        if existing_attachment is None:
            db.add(
                ActionQueueItem(
                    candidate_id=candidate.id,
                    action_type="resume_attachment_detected",
                    status="pending",
                    risk_level="low",
                    draft_message=None,
                    payload={
                        "source": "boss_chat",
                        "attachments": attachments,
                        "auto_send": False,
                    },
                )
            )
    else:
        candidate.status = "resume_requested"
        if not detail.get("resume_request_sent"):
            _ensure_resume_draft(db, candidate)
    db.commit()
    audit_repo.create_audit_log(
        db,
        action_type="extension_chat_ingest",
        status="ok",
        detail=f"已采集候选人 {candidate.name} 的沟通记录",
        payload={
            "candidate_id": candidate.id,
            "message_count": message_count,
            "attachment_count": len(attachments),
        },
    )
    attachment_uploads = (
        [{"candidate_id": candidate.id, "attachment_urls": attachment_urls, "job_id": result.get("job_id")}]
        if attachment_urls
        else []
    )
    return candidate.id, attachment_urls, attachment_uploads


def ingest_talent_result(
    db: Session, *, result: dict[str, Any], command_payload: dict[str, Any]
) -> dict[str, int]:
    filters = TalentFilter.model_validate(command_payload)
    job = talent_repo.get_job(db, filters.job_id)
    if job is None:
        raise ValueError("岗位不存在")
    cards = [TalentCard.model_validate(item) for item in result.get("cards") or []]
    if not filters.required_keywords:
        filters.required_keywords = list(job.keywords)
    matched_cards = filter_talent_cards(cards, filters)
    available = greeting_quota_status(db).available_count
    duplicate_count = 0
    drafted_count = 0
    for card, matched_keywords in matched_cards:
        candidate, _ = talent_repo.upsert_talent_candidate(db, card)
        if talent_repo.get_existing_greeting(db, candidate_id=candidate.id, job_id=job.id):
            duplicate_count += 1
            continue
        if drafted_count >= available:
            continue
        talent_repo.create_greeting_draft(
            db,
            candidate=candidate,
            job=job,
            draft_message=greeting_message(card, job),
            matched_keywords=matched_keywords,
        )
        drafted_count += 1
    db.commit()
    summary = {
        "total_read": len(cards),
        "matched_count": len(matched_cards),
        "duplicate_count": duplicate_count,
        "drafted_count": drafted_count,
    }
    audit_repo.create_audit_log(
        db,
        action_type="extension_talent_ingest",
        status="ok",
        detail=f"已读取 {len(cards)} 张牛人卡片，生成 {drafted_count} 条草稿",
        payload={"job_id": filters.job_id, **summary},
    )
    return summary


def complete_command(
    db: Session, command: ExtensionCommand, result: dict[str, Any]
) -> tuple[int | None, list[str], list[dict[str, Any]]]:
    candidate_id = None
    attachment_urls: list[str] = []
    attachment_uploads: list[dict[str, Any]] = []
    if command.command_type in {
        "scan_chats",
        "scan_chat_details",
        "request_resumes_batch",
        "read_current_chat",
    }:
        candidate_id, attachment_urls, attachment_uploads = ingest_chat_result(
            db, {**result, "job_id": command.payload.get("job_id")}
        )
    elif command.command_type == "scan_talents":
        result = {**result, **ingest_talent_result(db, result=result, command_payload=command.payload)}
    command.result = result
    command.status = "completed"
    command.completed_at = _now()
    db.commit()
    db.refresh(command)
    return candidate_id, attachment_urls, attachment_uploads


def fail_command(
    db: Session, command: ExtensionCommand, *, extension_id: str, error_message: str
) -> ExtensionCommand:
    command.extension_id = extension_id
    command.status = "failed"
    command.error_message = error_message
    command.completed_at = _now()
    db.commit()
    db.refresh(command)
    audit_repo.create_audit_log(
        db,
        action_type="extension_command",
        status="failed",
        detail=error_message,
        payload={"command_id": command.id, "command_type": command.command_type},
    )
    return command
