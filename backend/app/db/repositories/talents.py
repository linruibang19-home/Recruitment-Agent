from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ActionQueueItem, Candidate, Job
from app.schemas.talents import TalentCard


def get_job(db: Session, job_id: int) -> Job | None:
    return db.get(Job, job_id)


def get_candidate_by_boss_uid(db: Session, boss_uid: str) -> Candidate | None:
    return db.scalar(select(Candidate).where(Candidate.boss_uid == boss_uid))


def upsert_talent_candidate(db: Session, card: TalentCard) -> tuple[Candidate, bool]:
    candidate = get_candidate_by_boss_uid(db, card.boss_uid)
    created = candidate is None
    if candidate is None:
        candidate = Candidate(boss_uid=card.boss_uid, source="boss_recommend")
    candidate.name = card.name or candidate.name
    candidate.age = card.age or candidate.age
    candidate.city = card.city or candidate.city
    candidate.education_level = card.education_level or candidate.education_level
    candidate.school = card.school or candidate.school
    candidate.major = card.major or candidate.major
    candidate.graduation_year = card.graduation_year or candidate.graduation_year
    candidate.candidate_type = card.candidate_type or candidate.candidate_type
    candidate.expected_salary = card.expected_salary or candidate.expected_salary
    candidate.current_role = card.intention or candidate.current_role
    candidate.raw_card = {
        **(candidate.raw_card or {}),
        **card.model_dump(),
    }
    db.add(candidate)
    db.flush()
    return candidate, created


def get_existing_greeting(
    db: Session,
    *,
    candidate_id: int,
    job_id: int,
) -> ActionQueueItem | None:
    return db.scalar(
        select(ActionQueueItem)
        .where(
            ActionQueueItem.candidate_id == candidate_id,
            ActionQueueItem.job_id == job_id,
            ActionQueueItem.action_type == "request_resume_greeting",
        )
        .order_by(ActionQueueItem.created_at.desc())
    )


def create_greeting_draft(
    db: Session,
    *,
    candidate: Candidate,
    job: Job,
    draft_message: str,
    matched_keywords: list[str],
) -> ActionQueueItem:
    action = ActionQueueItem(
        candidate_id=candidate.id,
        job_id=job.id,
        action_type="request_resume_greeting",
        status="pending",
        risk_level="medium",
        draft_message=draft_message,
        payload={
            "source": "boss_recommend",
            "matched_keywords": matched_keywords,
            "auto_send": False,
        },
    )
    db.add(action)
    db.flush()
    return action
