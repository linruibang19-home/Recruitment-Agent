from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import ActionQueueItem
from app.db.repositories import audit_logs as audit_repo
from app.db.repositories import recommendations as recommendation_repo
from app.db.session import get_db
from app.schemas.common import PageResponse
from app.schemas.recommendations import (
    ActionDecisionRequest,
    ActionQueueRead,
    RecommendationGenerateRequest,
    RecommendationItemRead,
    RecommendationRunRead,
)
from app.services.recommendation_service import (
    generate_daily_recommendations,
    read_daily_recommendations,
)

router = APIRouter(tags=["recommendations"])


def _action_read(action: ActionQueueItem) -> ActionQueueRead:
    return ActionQueueRead(
        id=action.id,
        candidate_id=action.candidate_id,
        candidate_name=action.candidate.name if action.candidate else None,
        job_id=action.job_id,
        job_title=action.job.title if action.job else None,
        action_type=action.action_type,
        status=action.status,
        risk_level=action.risk_level,
        draft_message=action.draft_message,
        payload=action.payload,
        created_at=action.created_at,
        updated_at=action.updated_at,
    )


@router.get("/recommendations/today", response_model=list[RecommendationItemRead])
def get_today_recommendations(
    job_id: int | None = None,
    db: Session = Depends(get_db),
) -> list[RecommendationItemRead]:
    return read_daily_recommendations(db, recommendation_date=date.today(), job_id=job_id)


@router.post("/recommendations/generate", response_model=RecommendationRunRead)
def generate_recommendations(
    payload: RecommendationGenerateRequest,
    db: Session = Depends(get_db),
) -> RecommendationRunRead:
    result = generate_daily_recommendations(
        db,
        recommendation_date=date.today(),
        job_id=payload.job_id,
        top_n=payload.top_n,
        create_interview_drafts=payload.create_interview_drafts,
    )
    audit_repo.create_audit_log(
        db,
        action_type="daily_recommendation",
        status="ok",
        detail=f"生成 {result.recommendations_created} 条候选人推荐",
        payload={
            "job_id": payload.job_id,
            "top_n": payload.top_n,
            "drafts_created": result.drafts_created,
        },
    )
    return result


@router.get("/actions", response_model=PageResponse[ActionQueueRead])
def list_actions(
    action_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> PageResponse[ActionQueueRead]:
    count_stmt = select(func.count()).select_from(ActionQueueItem)
    if action_status:
        count_stmt = count_stmt.where(ActionQueueItem.status == action_status)
    total = db.scalar(count_stmt) or 0
    items = recommendation_repo.list_actions(
        db,
        status=action_status,
        limit=limit,
        offset=offset,
    )
    return PageResponse(
        items=[_action_read(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


def _decide_action(
    db: Session,
    *,
    action_id: int,
    decision: str,
    note: str | None,
) -> ActionQueueRead:
    action = db.get(ActionQueueItem, action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    if action.status != "pending":
        raise HTTPException(status_code=409, detail="只有待确认动作可以审核")
    action.status = decision
    action.payload = {
        **(action.payload or {}),
        "review_note": note,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    }
    if action.candidate and action.action_type == "interview_invite":
        action.candidate.status = (
            "interview_invite_pending" if decision == "approved" else "scored"
        )
    db.commit()
    db.refresh(action)
    audit_repo.create_audit_log(
        db,
        action_type=f"action_{decision}",
        status="ok",
        detail=f"动作 {action_id} 已{ '通过' if decision == 'approved' else '拒绝' }",
        payload={"action_id": action_id, "note": note},
    )
    action = db.get(ActionQueueItem, action_id)
    return _action_read(action)


@router.post("/actions/{action_id}/approve", response_model=ActionQueueRead)
def approve_action(
    action_id: int,
    payload: ActionDecisionRequest,
    db: Session = Depends(get_db),
) -> ActionQueueRead:
    return _decide_action(db, action_id=action_id, decision="approved", note=payload.note)


@router.post("/actions/{action_id}/reject", response_model=ActionQueueRead)
def reject_action(
    action_id: int,
    payload: ActionDecisionRequest,
    db: Session = Depends(get_db),
) -> ActionQueueRead:
    return _decide_action(db, action_id=action_id, decision="rejected", note=payload.note)
