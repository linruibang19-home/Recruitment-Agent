from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Candidate, CandidateProfile, Job, Resume, Score
from app.services.scorer import CandidateScore


def get_candidate_detail(db: Session, candidate_id: int) -> Candidate | None:
    return db.scalar(
        select(Candidate)
        .where(Candidate.id == candidate_id)
        .options(
            selectinload(Candidate.profile),
            selectinload(Candidate.resumes),
            selectinload(Candidate.scores),
        )
    )


def create_resume(
    db: Session,
    *,
    candidate_id: int,
    original_filename: str,
    file_path: str | None,
) -> Resume:
    resume = Resume(
        candidate_id=candidate_id,
        original_filename=original_filename,
        file_path=file_path,
        parse_status="pending",
    )
    db.add(resume)
    db.flush()
    return resume


def save_processing_result(
    db: Session,
    *,
    candidate: Candidate,
    resume: Resume,
    parsed_text: str,
    ocr_text: str,
    parse_status: str,
    profile_data: dict[str, Any],
    parser_name: str,
) -> CandidateProfile:
    resume.parsed_text = parsed_text
    resume.ocr_text = ocr_text or None
    resume.parse_status = parse_status

    candidate.education_level = profile_data.get("education_level") or candidate.education_level
    candidate.school = profile_data.get("school") or candidate.school
    candidate.major = profile_data.get("major") or candidate.major
    candidate.graduation_year = profile_data.get("graduation_year") or candidate.graduation_year
    candidate.candidate_type = profile_data.get("candidate_type") or candidate.candidate_type
    candidate.profile_summary = profile_data.get("profile_summary") or candidate.profile_summary
    candidate.status = "resume_parsed" if parse_status == "ok" else "discovered"

    profile = candidate.profile or CandidateProfile(candidate_id=candidate.id)
    profile.skills = profile_data.get("skills") or []
    profile.highlights = profile_data.get("highlights") or []
    profile.risks = profile_data.get("risks") or []
    profile.profile_json = {**profile_data, "parser": parser_name}
    db.add(profile)
    db.flush()
    return profile


def upsert_score(
    db: Session,
    *,
    candidate: Candidate,
    job: Job,
    result: CandidateScore,
) -> Score:
    score = db.scalar(
        select(Score).where(Score.candidate_id == candidate.id, Score.job_id == job.id)
    )
    if not score:
        score = Score(candidate_id=candidate.id, job_id=job.id, total_score=Decimal("0"))
    score.total_score = Decimal(str(result.total))
    score.dimensions = result.dimensions
    score.rationale = result.rationale
    candidate.status = "scored"
    db.add(score)
    db.flush()
    return score
