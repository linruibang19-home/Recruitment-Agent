from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Candidate, Job, Score
from app.db.repositories import recommendations as repo
from app.schemas.recommendations import RecommendationItemRead, RecommendationRunRead
from app.services.candidate_pipeline import refresh_candidate_pipeline_status
from app.services.message_generator import generate_interview_invite


def _recommendation_reason(score: Score) -> str:
    profile = score.candidate.profile
    highlights = profile.highlights[:2] if profile else []
    risks = profile.risks[:2] if profile else []
    parts = [f"岗位匹配 {float(score.total_score):.0f} 分"]
    if highlights:
        parts.append("；".join(highlights))
    if risks:
        parts.append(f"需关注：{'；'.join(risks)}")
    elif score.rationale:
        parts.append(score.rationale)
    return "；".join(parts)


def generate_daily_recommendations(
    db: Session,
    *,
    recommendation_date: date,
    job_id: int | None = None,
    top_n: int | None = None,
    create_interview_drafts: bool = True,
) -> RecommendationRunRead:
    limit = top_n or settings.recommendation_top_n
    jobs = repo.list_active_jobs(db, job_id)
    items: list[RecommendationItemRead] = []
    drafts_created = 0

    for job in jobs:
        scores = repo.list_ranked_scores(db, job.id, limit)
        ranked = [(score, _recommendation_reason(score)) for score in scores]
        recommendations = repo.replace_daily_recommendations(
            db,
            job_id=job.id,
            recommendation_date=recommendation_date,
            ranked=ranked,
        )
        for recommendation, score in zip(recommendations, scores):
            action = None
            if (
                create_interview_drafts
                and float(score.total_score) >= settings.interview_invite_score_threshold
            ):
                action, created = repo.get_or_create_interview_action(
                    db,
                    score=score,
                    draft_message=generate_interview_invite(score.candidate, job),
                    recommendation_id=recommendation.id,
                    recommendation_date=recommendation_date,
                )
                drafts_created += int(created)
                if action.status in ("pending", "approved"):
                    score.candidate.status = "interview_invite_pending"
                refresh_candidate_pipeline_status(db, score.candidate)
            profile = score.candidate.profile
            items.append(
                RecommendationItemRead(
                    id=recommendation.id,
                    job_id=job.id,
                    job_title=job.title,
                    candidate_id=score.candidate_id,
                    candidate_name=score.candidate.name or "未命名候选人",
                    recommendation_date=recommendation_date,
                    rank=recommendation.rank,
                    total_score=float(score.total_score),
                    reason=recommendation.reason,
                    highlights=profile.highlights if profile else [],
                    risks=profile.risks if profile else [],
                    action_id=action.id if action else None,
                    action_status=action.status if action else None,
                    interview_draft=action.draft_message if action else None,
                )
            )
    db.commit()
    return RecommendationRunRead(
        recommendation_date=recommendation_date,
        jobs_processed=len(jobs),
        recommendations_created=len(items),
        drafts_created=drafts_created,
        items=items,
    )


def read_daily_recommendations(
    db: Session,
    *,
    recommendation_date: date,
    job_id: int | None = None,
) -> list[RecommendationItemRead]:
    recommendations = repo.list_daily_recommendations(
        db,
        recommendation_date=recommendation_date,
        job_id=job_id,
    )
    items: list[RecommendationItemRead] = []
    for recommendation in recommendations:
        candidate = db.get(Candidate, recommendation.candidate_id)
        job = db.get(Job, recommendation.job_id)
        score = db.query(Score).filter_by(
            candidate_id=recommendation.candidate_id,
            job_id=recommendation.job_id,
        ).one_or_none()
        if not candidate or not job or not score:
            continue
        profile = candidate.profile
        action = repo.get_action_for_recommendation(
            db,
            candidate_id=candidate.id,
            job_id=job.id,
        )
        items.append(
            RecommendationItemRead(
                id=recommendation.id,
                job_id=job.id,
                job_title=job.title,
                candidate_id=candidate.id,
                candidate_name=candidate.name or "未命名候选人",
                recommendation_date=recommendation.recommendation_date,
                rank=recommendation.rank,
                total_score=float(score.total_score),
                reason=recommendation.reason,
                highlights=profile.highlights if profile else [],
                risks=profile.risks if profile else [],
                action_id=action.id if action else None,
                action_status=action.status if action else None,
                interview_draft=action.draft_message if action else None,
            )
        )
    return items
