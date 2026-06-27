from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class RecommendationGenerateRequest(BaseModel):
    job_id: int | None = None
    top_n: int | None = Field(default=None, ge=1, le=20)
    create_interview_drafts: bool = True


class RecommendationItemRead(BaseModel):
    id: int
    job_id: int
    job_title: str
    candidate_id: int
    candidate_name: str
    recommendation_date: date
    rank: int
    total_score: float
    reason: str | None = None
    highlights: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    action_id: int | None = None
    action_status: str | None = None
    interview_draft: str | None = None


class RecommendationRunRead(BaseModel):
    recommendation_date: date
    jobs_processed: int
    recommendations_created: int
    drafts_created: int
    items: list[RecommendationItemRead]


class ActionQueueRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_id: int | None = None
    candidate_name: str | None = None
    job_id: int | None = None
    job_title: str | None = None
    action_type: str
    status: str
    risk_level: str
    draft_message: str | None = None
    payload: dict
    created_at: datetime
    updated_at: datetime


class ActionDecisionRequest(BaseModel):
    note: str | None = Field(default=None, max_length=500)
