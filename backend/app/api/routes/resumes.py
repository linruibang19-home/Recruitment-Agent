from __future__ import annotations

import re
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Job
from app.db.repositories import audit_logs as audit_repo
from app.db.repositories import resume_processing as resume_repo
from app.db.session import get_db
from app.schemas.resumes import CandidateDetailRead, ResumeProcessResult, ScoreRead
from app.schemas.workflows import WorkflowStartRequest
from app.services.profiler import generate_candidate_profile
from app.services.resume_parser import parse_pdf_text
from app.services.scorer import score_candidate
from app.services.workflow_service import start_workflow_safely

router = APIRouter(prefix="/candidates", tags=["resumes"])
PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_RESUME_DIR = PROJECT_ROOT / "data" / "resumes"


def _safe_filename(filename: str | None) -> str:
    base = Path(filename or "resume.pdf").name
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", base)
    return cleaned if cleaned.lower().endswith(".pdf") else f"{cleaned}.pdf"


@router.get("/{candidate_id}/detail", response_model=CandidateDetailRead)
def get_candidate_detail(candidate_id: int, db: Session = Depends(get_db)) -> CandidateDetailRead:
    candidate = resume_repo.get_candidate_detail(db, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return CandidateDetailRead(
        candidate=candidate,
        profile=candidate.profile,
        resumes=sorted(candidate.resumes, key=lambda item: item.created_at, reverse=True),
        scores=sorted(candidate.scores, key=lambda item: item.updated_at, reverse=True),
    )


@router.post(
    "/{candidate_id}/resumes",
    response_model=ResumeProcessResult,
    status_code=status.HTTP_201_CREATED,
)
async def upload_and_process_resume(
    candidate_id: int,
    file: UploadFile = File(...),
    job_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> ResumeProcessResult:
    candidate = resume_repo.get_candidate_detail(db, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    job = None
    if job_id is not None:
        job = db.get(Job, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=415, detail="只支持 PDF 简历")

    content = await file.read(settings.max_resume_size_mb * 1024 * 1024 + 1)
    if len(content) > settings.max_resume_size_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"简历不能超过 {settings.max_resume_size_mb} MB")
    if not content.startswith(b"%PDF"):
        raise HTTPException(status_code=415, detail="文件不是有效 PDF")

    resume_dir = Path(settings.resume_dir) if settings.resume_dir else DEFAULT_RESUME_DIR
    candidate_dir = resume_dir / str(candidate_id)
    candidate_dir.mkdir(parents=True, exist_ok=True)
    safe_name = _safe_filename(file.filename)
    stored_path = candidate_dir / f"{uuid4().hex}-{safe_name}"
    stored_path.write_bytes(content)

    resume = resume_repo.create_resume(
        db,
        candidate_id=candidate_id,
        original_filename=file.filename or safe_name,
        file_path=str(stored_path),
    )
    try:
        parsed = parse_pdf_text(stored_path)
        profile_data, parser_name = generate_candidate_profile(parsed.text)
        profile = resume_repo.save_processing_result(
            db,
            candidate=candidate,
            resume=resume,
            parsed_text=parsed.text,
            ocr_text=parsed.ocr_text,
            parse_status=parsed.status,
            profile_data=profile_data,
            parser_name=parser_name,
        )
        score = None
        if job is not None:
            score = resume_repo.upsert_score(
                db,
                candidate=candidate,
                job=job,
                result=score_candidate(candidate, profile, job),
            )
        db.commit()
        db.refresh(resume)
        db.refresh(candidate)
        db.refresh(profile)
        if score:
            db.refresh(score)
        audit_repo.create_audit_log(
            db,
            action_type="resume_process",
            status="ok",
            detail="候选人简历解析完成",
            payload={
                "candidate_id": candidate_id,
                "resume_id": resume.id,
                "parse_status": parsed.status,
                "parser": parser_name,
                "ocr_used": parsed.ocr_used,
                "text_length": len(parsed.text),
                "job_id": job_id,
            },
        )
        start_workflow_safely(
            db,
            WorkflowStartRequest(
                workflow_name="chat_resume",
                candidate_id=candidate_id,
                job_id=job_id,
                payload={
                    "resume_id": resume.id,
                    "parse_status": parsed.status,
                    "source": "resume_upload",
                    "idempotency_key": f"resume:{resume.id}",
                },
            ),
        )
        return ResumeProcessResult(
            resume=resume,
            candidate=candidate,
            profile=profile,
            score=score,
            parser=parser_name,
            text_length=len(parsed.text),
            ocr_used=parsed.ocr_used,
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        stored_path.unlink(missing_ok=True)
        audit_repo.create_audit_log(
            db,
            action_type="resume_process",
            status="failed",
            detail=f"{type(exc).__name__}: {exc}",
            payload={"candidate_id": candidate_id},
        )
        raise HTTPException(status_code=422, detail=f"简历处理失败：{exc}") from exc


@router.post("/{candidate_id}/scores/{job_id}", response_model=ScoreRead)
def rescore_candidate(candidate_id: int, job_id: int, db: Session = Depends(get_db)) -> ScoreRead:
    candidate = resume_repo.get_candidate_detail(db, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    if not candidate.profile:
        raise HTTPException(status_code=409, detail="请先解析候选人简历")
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    score = resume_repo.upsert_score(
        db,
        candidate=candidate,
        job=job,
        result=score_candidate(candidate, candidate.profile, job),
    )
    db.commit()
    db.refresh(score)
    audit_repo.create_audit_log(
        db,
        action_type="candidate_score",
        status="ok",
        detail=f"候选人 {candidate_id} 对岗位 {job_id} 评分完成",
        payload={"candidate_id": candidate_id, "job_id": job_id, "total_score": float(score.total_score)},
    )
    return score
