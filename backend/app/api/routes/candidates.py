from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.repositories import candidates as candidate_repo
from app.db.session import get_db
from app.schemas.candidates import CandidateCreate, CandidateRead, CandidateUpdate
from app.schemas.common import PageResponse

router = APIRouter(prefix="/candidates", tags=["candidates"])


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

