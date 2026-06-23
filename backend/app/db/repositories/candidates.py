from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.db.models import Candidate
from app.schemas.candidates import CandidateCreate, CandidateUpdate


def list_candidates(
    db: Session,
    *,
    status: str | None = None,
    source: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Candidate], int]:
    stmt: Select[tuple[Candidate]] = select(Candidate)
    count_stmt = select(func.count()).select_from(Candidate)
    if status:
        stmt = stmt.where(Candidate.status == status)
        count_stmt = count_stmt.where(Candidate.status == status)
    if source:
        stmt = stmt.where(Candidate.source == source)
        count_stmt = count_stmt.where(Candidate.source == source)
    total = db.scalar(count_stmt) or 0
    items = list(db.scalars(stmt.order_by(Candidate.updated_at.desc()).limit(limit).offset(offset)))
    return items, total


def get_candidate(db: Session, candidate_id: int) -> Candidate | None:
    return db.get(Candidate, candidate_id)


def create_candidate(db: Session, payload: CandidateCreate) -> Candidate:
    candidate = Candidate(**payload.model_dump())
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


def update_candidate(db: Session, candidate: Candidate, payload: CandidateUpdate) -> Candidate:
    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(candidate, key, value)
    db.commit()
    db.refresh(candidate)
    return candidate

