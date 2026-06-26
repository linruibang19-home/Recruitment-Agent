from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.candidates import CandidateRead


class ResumeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_id: int
    original_filename: str | None = None
    file_path: str | None = None
    parse_status: str
    created_at: datetime
    updated_at: datetime


class CandidateProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_id: int
    skills: list[str]
    highlights: list[str]
    risks: list[str]
    profile_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ScoreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_id: int
    job_id: int
    total_score: Decimal
    dimensions: dict[str, Any]
    rationale: str | None = None
    created_at: datetime
    updated_at: datetime


class ResumeProcessResult(BaseModel):
    resume: ResumeRead
    candidate: CandidateRead
    profile: CandidateProfileRead
    score: ScoreRead | None = None
    parser: str
    text_length: int
    ocr_used: bool


class ResumeTextCreate(BaseModel):
    original_filename: str | None = None
    parsed_text: str = Field(min_length=40, max_length=200_000)
    source: str = "boss_preview"


class CandidateDetailRead(BaseModel):
    candidate: CandidateRead
    profile: CandidateProfileRead | None = None
    resumes: list[ResumeRead] = Field(default_factory=list)
    scores: list[ScoreRead] = Field(default_factory=list)
