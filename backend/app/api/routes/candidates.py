from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.repositories import candidates as candidate_repo
from app.db.repositories import audit_logs as audit_repo
from app.db.session import get_db
from app.core.config import settings
from app.core.security import is_within_directory
from app.schemas.candidates import CandidateCreate, CandidateDeleteResult, CandidateRead, CandidateUpdate
from app.schemas.common import PageResponse

router = APIRouter(prefix="/candidates", tags=["candidates"])
PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_RESUME_DIR = PROJECT_ROOT / "data" / "resumes"


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
