from __future__ import annotations

from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, joinedload

from app.db.models import ActionQueueItem, Candidate, Job, Recommendation, Score


def list_active_jobs(Session: Session, job_id: int | None = None) -> list[Job]:
    stmt = select(Job).where(Job.is_active.is_(True))
    if job_id is not None:
        stmt = stmt.where(Job.id == job_id)
    return list(Session.scalars(stmt.order_by(Job.created_at)))


def list_ranked_scores(Session: Session, job_id: int, limit: int) -> list[Score]:
    stmt = (
        select(Score)
        .where(Score.job_id == job_id)
        .options(
            joinedload(Score.candidate).joinedload(Candidate.profile),
            joinedload(Score.job),
        )
        .order_by(Score.total_score.desc(), Score.updated_at.desc())
        .limit(limit)
    )
    return list(Session.scalars(stmt))


def replace_daily_recommendations(
    Session: Session,
    *,
    job_id: int,
    recommendation_date: date,
    ranked: list[tuple[Score, str]],
) -> list[Recommendation]:
    Session.execute(
        delete(Recommendation).where(
            Recommendation.job_id == job_id,
            Recommendation.recommendation_date == recommendation_date,
        )
    )
    items: list[Recommendation] = []
    for rank, (score, reason) in enumerate(ranked, start=1):
        item = Recommendation(
            job_id=job_id,
            candidate_id=score.candidate_id,
            recommendation_date=recommendation_date,
            rank=rank,
            reason=reason,
        )
        Session.add(item)
        items.append(item)
    Session.flush()
    return items


def get_or_create_interview_action(
    Session: Session,
    *,
    score: Score,
    draft_message: str,
    recommendation_id: int,
    recommendation_date: date,
) -> tuple[ActionQueueItem, bool]:
    existing = list(
        Session.scalars(
            select(ActionQueueItem)
            .where(
                ActionQueueItem.candidate_id == score.candidate_id,
                ActionQueueItem.job_id == score.job_id,
                ActionQueueItem.action_type == "interview_invite",
            )
            .order_by(ActionQueueItem.created_at.desc())
        )
    )
    action = next(
        (
            item
            for item in existing
            if (item.payload or {}).get("recommendation_date") == recommendation_date.isoformat()
        ),
        None,
    )
    if action:
        if action.status in ("pending", "approved"):
            action.draft_message = draft_message
        action.payload = {
            **(action.payload or {}),
            "recommendation_id": recommendation_id,
        }
        return action, False
    action = ActionQueueItem(
        candidate_id=score.candidate_id,
        job_id=score.job_id,
        action_type="interview_invite",
        status="pending",
        risk_level="high",
        draft_message=draft_message,
        payload={
            "recommendation_id": recommendation_id,
            "recommendation_date": recommendation_date.isoformat(),
            "source": "daily_recommendation",
        },
    )
    Session.add(action)
    Session.flush()
    return action, True


def list_actions(
    Session: Session,
    *,
    status: str | None,
    limit: int,
    offset: int,
) -> list[ActionQueueItem]:
    stmt = select(ActionQueueItem).options(
        joinedload(ActionQueueItem.candidate),
        joinedload(ActionQueueItem.job),
    )
    if status:
        stmt = stmt.where(ActionQueueItem.status == status)
    return list(
        Session.scalars(
            stmt.order_by(ActionQueueItem.created_at.desc()).limit(limit).offset(offset)
        )
    )


def list_daily_recommendations(
    Session: Session,
    *,
    recommendation_date: date,
    job_id: int | None = None,
) -> list[Recommendation]:
    stmt = select(Recommendation).where(
        Recommendation.recommendation_date == recommendation_date
    )
    if job_id is not None:
        stmt = stmt.where(Recommendation.job_id == job_id)
    return list(Session.scalars(stmt.order_by(Recommendation.job_id, Recommendation.rank)))


def get_action_for_recommendation(
    Session: Session,
    *,
    candidate_id: int,
    job_id: int,
) -> ActionQueueItem | None:
    return Session.scalar(
        select(ActionQueueItem)
        .where(
            ActionQueueItem.candidate_id == candidate_id,
            ActionQueueItem.job_id == job_id,
            ActionQueueItem.action_type == "interview_invite",
        )
        .order_by(ActionQueueItem.created_at.desc())
    )
