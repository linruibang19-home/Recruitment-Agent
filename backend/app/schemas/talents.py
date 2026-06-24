from datetime import date, datetime

from pydantic import BaseModel, Field


class TalentFilter(BaseModel):
    job_id: int
    city: str | None = None
    experience: list[str] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    intentions: list[str] = Field(default_factory=list)
    salary_keywords: list[str] = Field(default_factory=list)
    required_keywords: list[str] = Field(default_factory=list)
    limit: int = Field(default=20, ge=1, le=100)
    capture_screenshot: bool = True


class TalentCard(BaseModel):
    boss_uid: str
    name: str
    age: int | None = None
    city: str | None = None
    education_level: str | None = None
    school: str | None = None
    major: str | None = None
    graduation_year: int | None = None
    candidate_type: str | None = None
    experience: str | None = None
    intention: str | None = None
    expected_salary: str | None = None
    skills: list[str] = Field(default_factory=list)
    href: str | None = None
    raw_text: str


class TalentScanResult(BaseModel):
    scanned_at: datetime
    page_url: str
    total_read: int
    matched_count: int
    duplicate_count: int
    drafted_count: int
    cards: list[TalentCard]
    screenshot_path: str | None = None


class GreetingQuotaRead(BaseModel):
    quota_date: date
    used_count: int
    max_count: int
    pending_count: int
    approved_count: int
    available_count: int
