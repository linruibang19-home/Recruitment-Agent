from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.db.models import Candidate, CandidateProfile, Job


EDUCATION_RANK = {"高中": 1, "大专": 2, "本科": 3, "硕士": 4, "博士": 5}


@dataclass(frozen=True)
class CandidateScore:
    total: float
    dimensions: dict[str, Any]
    rationale: str


def _education_score(candidate_level: str | None, required_level: str | None) -> tuple[float, str]:
    if not required_level:
        return 20.0, "岗位未限制学历"
    candidate_rank = EDUCATION_RANK.get(candidate_level or "", 0)
    required_rank = max(
        (rank for level, rank in EDUCATION_RANK.items() if level in required_level),
        default=0,
    )
    if candidate_rank >= required_rank > 0:
        return 20.0, f"{candidate_level}满足{required_level}"
    if candidate_rank and required_rank and candidate_rank == required_rank - 1:
        return 10.0, f"{candidate_level}略低于{required_level}"
    return 0.0, f"{candidate_level or '未知学历'}不满足{required_level}"


def score_candidate(candidate: Candidate, profile: CandidateProfile, job: Job) -> CandidateScore:
    skills = [str(skill) for skill in profile.skills]
    normalized_skills = {skill.lower() for skill in skills}
    keywords = [str(keyword) for keyword in job.keywords]
    matched = [
        keyword for keyword in keywords
        if keyword.lower() in normalized_skills
        or any(keyword.lower() in skill.lower() for skill in skills)
    ]
    skill_score = 40.0 if not keywords else round(40 * len(matched) / len(keywords), 2)
    education_score, education_reason = _education_score(
        candidate.education_level,
        job.education_requirement,
    )

    profile_json = profile.profile_json or {}
    projects = profile_json.get("projects") or []
    work_experience = float(profile_json.get("work_experience") or 0)
    project_score = min(12.0, len(projects) * 4.0)
    experience_score = min(8.0, work_experience * 2.0)
    practice_score = round(project_score + experience_score, 2)

    completeness_fields = (
        candidate.education_level,
        candidate.school,
        candidate.major,
        candidate.graduation_year,
        skills,
    )
    completeness_score = round(10 * sum(bool(value) for value in completeness_fields) / len(completeness_fields), 2)

    location_score = 5.0 if not job.city or not candidate.city or job.city in candidate.city else 0.0
    type_score = 5.0 if candidate.candidate_type else 2.0
    fit_score = location_score + type_score

    total = round(skill_score + education_score + practice_score + completeness_score + fit_score, 2)
    dimensions = {
        "skills": {"score": skill_score, "max": 40, "matched": matched, "required": keywords},
        "education": {"score": education_score, "max": 20, "reason": education_reason},
        "projects_experience": {
            "score": practice_score,
            "max": 20,
            "project_count": len(projects),
            "work_years": work_experience,
        },
        "completeness": {"score": completeness_score, "max": 10},
        "basic_fit": {"score": fit_score, "max": 10},
    }
    reasons = [
        f"技能命中 {len(matched)}/{len(keywords)}" if keywords else "岗位未设置技能关键词",
        education_reason,
        f"识别到 {len(projects)} 段项目经历",
        f"信息完整度 {completeness_score}/10",
    ]
    return CandidateScore(total=min(total, 100.0), dimensions=dimensions, rationale="；".join(reasons))
