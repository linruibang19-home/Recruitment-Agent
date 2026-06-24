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
