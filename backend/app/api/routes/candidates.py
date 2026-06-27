from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import ActionQueueItem, Candidate, Interaction, Resume, Score
from app.db.repositories import candidates as candidate_repo
from app.db.repositories import audit_logs as audit_repo
from app.db.session import get_db
from app.core.config import settings
from app.core.security import is_within_directory
from app.schemas.candidates import (
    CandidateCreate,
    CandidateDeleteResult,
    CandidatePipelineItem,
    CandidatePipelineSummary,
    CandidateRead,
    CandidateUpdate,
)
from app.schemas.common import PageResponse

router = APIRouter(prefix="/candidates", tags=["candidates"])
PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_RESUME_DIR = PROJECT_ROOT / "data" / "resumes"


def _pipeline_stage(
    candidate: Candidate,
    *,
    resume_count: int,
    parsed_resume_count: int,
    best_score: float | None,
    pending_action_count: int,
) -> tuple[str, str, str]:
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


@router.get("", response_model=PageResponse[CandidateRead])
def list_candidates(
    candidate_status: str | None = Query(default=None, alias="status"),
    source: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> PageResponse[CandidateRead]:
    items, total = candidate_repo.list_candidates(
        db,
        status=candidate_status,
        source=source,
        limit=limit,
        offset=offset,
    )
    return PageResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/pipeline", response_model=CandidatePipelineSummary)
def candidate_pipeline(
    limit: int = Query(default=80, ge=1, le=200),
    db: Session = Depends(get_db),
) -> CandidatePipelineSummary:
    candidates = list(
        db.scalars(
            select(Candidate)
            .where(Candidate.source.in_(("boss_chat", "boss_recommend", "manual", "imported")))
            .order_by(Candidate.updated_at.desc())
            .limit(limit)
        )
    )
    ids = [candidate.id for candidate in candidates]
    if not ids:
        return CandidatePipelineSummary(
            total=0,
            discovered=0,
            resume_requested=0,
            resume_received=0,
            parsed=0,
            scored=0,
            pending_review=0,
            items=[],
        )

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

    items: list[CandidatePipelineItem] = []
    counts = {
        "discovered": 0,
        "resume_requested": 0,
        "resume_received": 0,
        "parsed": 0,
        "scored": 0,
        "pending_review": 0,
    }
    for candidate in candidates:
        resume_count, parsed_resume_count = resume_map.get(candidate.id, (0, 0))
        best_score = score_map.get(candidate.id)
        pending_action_count = action_map.get(candidate.id, 0)
        message_count, last_interaction_at = message_map.get(candidate.id, (0, None))
        stage, stage_label, next_action = _pipeline_stage(
            candidate,
            resume_count=resume_count,
            parsed_resume_count=parsed_resume_count,
            best_score=best_score,
            pending_action_count=pending_action_count,
        )
        counts[stage] += 1
        items.append(
            CandidatePipelineItem(
                candidate_id=candidate.id,
                name=candidate.name,
                source=candidate.source,
                status=candidate.status,
                stage=stage,
                stage_label=stage_label,
                next_action=next_action,
                has_resume=resume_count > 0,
                resume_count=resume_count,
                message_count=message_count,
                pending_action_count=pending_action_count,
                best_score=best_score,
                last_interaction_at=last_interaction_at,
                updated_at=candidate.updated_at,
            )
        )

    return CandidatePipelineSummary(total=len(items), items=items, **counts)


@router.post("", response_model=CandidateRead, status_code=status.HTTP_201_CREATED)
def create_candidate(payload: CandidateCreate, db: Session = Depends(get_db)) -> CandidateRead:
    try:
        return candidate_repo.create_candidate(db, payload)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Candidate violates a database constraint") from exc


@router.get("/{candidate_id}", response_model=CandidateRead)
def get_candidate(candidate_id: int, db: Session = Depends(get_db)) -> CandidateRead:
    candidate = candidate_repo.get_candidate(db, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate


@router.patch("/{candidate_id}", response_model=CandidateRead)
def update_candidate(candidate_id: int, payload: CandidateUpdate, db: Session = Depends(get_db)) -> CandidateRead:
    candidate = candidate_repo.get_candidate(db, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    try:
        return candidate_repo.update_candidate(db, candidate, payload)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Candidate violates a database constraint") from exc


@router.delete("/{candidate_id}", response_model=CandidateDeleteResult)
def delete_candidate(
    candidate_id: int,
    confirm: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> CandidateDeleteResult:
    if not confirm:
        raise HTTPException(status_code=400, detail="Candidate deletion requires confirm=true")
    candidate = candidate_repo.get_candidate(db, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    resume_root = Path(settings.resume_dir) if settings.resume_dir else DEFAULT_RESUME_DIR
    resume_paths = [
        Path(resume.file_path)
        for resume in candidate.resumes
        if resume.file_path and is_within_directory(Path(resume.file_path), resume_root)
    ]
    db.delete(candidate)
    db.commit()

    deleted_files = 0
    for resume_path in resume_paths:
        try:
            if resume_path.is_file():
                resume_path.unlink(missing_ok=True)
                deleted_files += 1
        except OSError:
            continue
        parent = resume_path.parent
        if parent != resume_root and is_within_directory(parent, resume_root):
            try:
                parent.rmdir()
            except OSError:
                pass

    audit_repo.create_audit_log(
        db,
        action_type="candidate_deleted",
        status="ok",
        detail=f"候选人数据已删除，ID：{candidate_id}",
        payload={"candidate_id": candidate_id, "deleted_resume_files": deleted_files},
    )
    return CandidateDeleteResult(
        candidate_id=candidate_id,
        deleted_resume_files=deleted_files,
    )
