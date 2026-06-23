from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class JobBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    city: str | None = None
    description: str | None = None
    experience_requirement: str | None = None
    education_requirement: str | None = None
    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)
    keywords: list[str] = Field(default_factory=list)
    is_active: bool = True


class JobCreate(JobBase):
    pass


class JobUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    city: str | None = None
    description: str | None = None
    experience_requirement: str | None = None
    education_requirement: str | None = None
    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)
    keywords: list[str] | None = None
    is_active: bool | None = None


class JobRead(JobBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime

