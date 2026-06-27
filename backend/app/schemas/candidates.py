from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CandidateBase(BaseModel):
    boss_uid: str | None = None
    source: str = "manual"
    status: str = "discovered"
    name: str | None = None
    current_role: str | None = None
    age: int | None = Field(default=None, ge=16, le=80)
    city: str | None = None
    education_level: str | None = None
    school: str | None = None
    major: str | None = None
    graduation_year: int | None = Field(default=None, ge=1980, le=2100)
    candidate_type: str | None = None
    expected_salary: str | None = None
    profile_summary: str | None = None
    raw_card: dict[str, Any] = Field(default_factory=dict)


class CandidateCreate(CandidateBase):
    pass


class CandidateUpdate(BaseModel):
    boss_uid: str | None = None
    source: str | None = None
    status: str | None = None
    name: str | None = None
    current_role: str | None = None
    age: int | None = Field(default=None, ge=16, le=80)
    city: str | None = None
    education_level: str | None = None
    school: str | None = None
    major: str | None = None
    graduation_year: int | None = Field(default=None, ge=1980, le=2100)
    candidate_type: str | None = None
    expected_salary: str | None = None
    profile_summary: str | None = None
    raw_card: dict[str, Any] | None = None


class CandidateRead(CandidateBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class CandidateDeleteResult(BaseModel):
    candidate_id: int
    deleted_resume_files: int
    deleted: bool = True


class CandidatePipelineItem(BaseModel):
    candidate_id: int
    name: str | None = None
    source: str
    status: str
    stage: str
    stage_label: str
    next_action: str
    has_resume: bool
    resume_count: int
    message_count: int
    pending_action_count: int
    best_score: float | None = None
    last_interaction_at: datetime | None = None
    updated_at: datetime
    expected_status: str
    status_drift: bool


class CandidatePipelineSummary(BaseModel):
    total: int
    discovered: int
    resume_requested: int
    resume_received: int
    parsed: int
    scored: int
    pending_review: int
    drift_count: int
    items: list[CandidatePipelineItem]


class CandidatePipelineSyncChange(BaseModel):
    candidate_id: int
    from_status: str
    to_status: str
    stage: str


class CandidatePipelineSyncRead(BaseModel):
    scanned: int
    updated: int
    changes: list[CandidatePipelineSyncChange]
