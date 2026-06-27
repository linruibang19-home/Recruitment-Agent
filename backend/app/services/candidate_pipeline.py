from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import ActionQueueItem, Candidate, Interaction, Resume, Score

PipelineStage = Literal[
    "discovered",
    "resume_requested",
    "resume_received",
    "parsed",
    "scored",
    "pending_review",
]

STAGE_STATUS: dict[PipelineStage, str] = {
    "discovered": "discovered",
    "resume_requested": "resume_requested",
    "resume_received": "resume_received",
    "parsed": "resume_parsed",
    "scored": "scored",
    "pending_review": "pending_review",
}


@dataclass(frozen=True)
class CandidatePipelineSnapshot:
    candidate_id: int
    resume_count: int
    parsed_resume_count: int
    best_score: float | None
    pending_action_count: int
    message_count: int
    last_interaction_at: datetime | None
    stage: PipelineStage
    stage_label: str
    next_action: str
    expected_status: str
    status_drift: bool


@dataclass(frozen=True)
class CandidatePipelineSyncResult:
    scanned: int
    updated: int
    changes: list[dict[str, str | int]]


def resolve_pipeline_stage(
    candidate: Candidate,
    *,
    resume_count: int,
    parsed_resume_count: int,
    best_score: float | None,
    pending_action_count: int,
) -> tuple[PipelineStage, str, str]:
    if pending_action_count:
        return "pending_review", "待人工确认", "处理待确认动作"
    if best_score is not None:
        return "scored", "已评分", "等待每日推荐或人工筛选"
    if parsed_resume_count:
        return "parsed", "已解析", "执行岗位匹配评分"
    if resume_count:
        return "resume_received", "已收到简历", "解析简历并生成候选人画像"
    if candidate.status == "resume_requested":
        return "resume_requested", "已索要简历", "等待候选人发送简历"
    return "discovered", "已发现", "读取沟通并索要 PDF 简历"


def load_pipeline_snapshots(
    db: Session,
    candidates: list[Candidate],
) -> dict[int, CandidatePipelineSnapshot]:
    ids = [candidate.id for candidate in candidates]
    if not ids:
        return {}

    resume_rows = db.execute(
        select(
            Resume.candidate_id,
            func.count(Resume.id),
            func.count(Resume.id).filter(Resume.parse_status == "ok"),
        )
        .where(Resume.candidate_id.in_(ids))
        .group_by(Resume.candidate_id)
    ).all()
    score_rows = db.execute(
        select(Score.candidate_id, func.max(Score.total_score))
        .where(Score.candidate_id.in_(ids))
        .group_by(Score.candidate_id)
    ).all()
    action_rows = db.execute(
        select(ActionQueueItem.candidate_id, func.count(ActionQueueItem.id))
        .where(
            ActionQueueItem.candidate_id.in_(ids),
            ActionQueueItem.status == "pending",
        )
        .group_by(ActionQueueItem.candidate_id)
    ).all()
    message_rows = db.execute(
        select(Interaction.candidate_id, func.count(Interaction.id), func.max(Interaction.occurred_at))
        .where(Interaction.candidate_id.in_(ids))
        .group_by(Interaction.candidate_id)
    ).all()

    resume_map = {int(row[0]): (int(row[1]), int(row[2])) for row in resume_rows}
    score_map = {int(row[0]): float(row[1]) for row in score_rows if row[1] is not None}
    action_map = {int(row[0]): int(row[1]) for row in action_rows}
    message_map = {int(row[0]): (int(row[1]), row[2]) for row in message_rows}

    snapshots: dict[int, CandidatePipelineSnapshot] = {}
    for candidate in candidates:
        resume_count, parsed_resume_count = resume_map.get(candidate.id, (0, 0))
        best_score = score_map.get(candidate.id)
        pending_action_count = action_map.get(candidate.id, 0)
        message_count, last_interaction_at = message_map.get(candidate.id, (0, None))
        stage, stage_label, next_action = resolve_pipeline_stage(
            candidate,
            resume_count=resume_count,
            parsed_resume_count=parsed_resume_count,
            best_score=best_score,
            pending_action_count=pending_action_count,
        )
        expected_status = STAGE_STATUS[stage]
        snapshots[candidate.id] = CandidatePipelineSnapshot(
            candidate_id=candidate.id,
            resume_count=resume_count,
            parsed_resume_count=parsed_resume_count,
            best_score=best_score,
            pending_action_count=pending_action_count,
            message_count=message_count,
            last_interaction_at=last_interaction_at,
            stage=stage,
            stage_label=stage_label,
            next_action=next_action,
            expected_status=expected_status,
            status_drift=candidate.status != expected_status,
        )
    return snapshots


def sync_candidate_pipeline_statuses(
    db: Session,
    *,
    limit: int = 200,
) -> CandidatePipelineSyncResult:
    candidates = list(
        db.scalars(
            select(Candidate)
            .where(Candidate.source.in_(("boss_chat", "boss_recommend", "manual", "imported")))
            .order_by(Candidate.updated_at.desc())
            .limit(limit)
        )
    )
    snapshots = load_pipeline_snapshots(db, candidates)
    changes: list[dict[str, str | int]] = []
    for candidate in candidates:
        snapshot = snapshots[candidate.id]
        if not snapshot.status_drift:
            continue
        changes.append(
            {
                "candidate_id": candidate.id,
                "from_status": candidate.status,
                "to_status": snapshot.expected_status,
                "stage": snapshot.stage,
            }
        )
        candidate.status = snapshot.expected_status
        db.add(candidate)
    if changes:
        db.commit()
    return CandidatePipelineSyncResult(scanned=len(candidates), updated=len(changes), changes=changes)


def refresh_candidate_pipeline_status(db: Session, candidate: Candidate) -> bool:
    db.flush()
    snapshot = load_pipeline_snapshots(db, [candidate]).get(candidate.id)
    if snapshot is None or not snapshot.status_drift:
        return False
    candidate.status = snapshot.expected_status
    db.add(candidate)
    db.flush()
    return True
