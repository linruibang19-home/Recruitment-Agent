from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Job(Base, TimestampMixin):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    city: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    experience_requirement: Mapped[str | None] = mapped_column(Text)
    education_requirement: Mapped[str | None] = mapped_column(Text)
    salary_min: Mapped[int | None] = mapped_column(Integer)
    salary_max: Mapped[int | None] = mapped_column(Integer)
    keywords: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default="[]")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    scores: Mapped[list[Score]] = relationship(back_populates="job")
    actions: Mapped[list[ActionQueueItem]] = relationship(back_populates="job")

    __table_args__ = (
        CheckConstraint(
            "salary_min is null or salary_max is null or salary_min <= salary_max",
            name="jobs_salary_range_check",
        ),
        Index("jobs_active_created_idx", "is_active", "created_at"),
    )


class Candidate(Base, TimestampMixin):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    boss_uid: Mapped[str | None] = mapped_column(Text, unique=True)
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default="manual")
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="discovered")
    name: Mapped[str | None] = mapped_column(Text)
    current_role: Mapped[str | None] = mapped_column(Text)
    age: Mapped[int | None] = mapped_column(Integer)
    city: Mapped[str | None] = mapped_column(Text)
    education_level: Mapped[str | None] = mapped_column(Text)
    school: Mapped[str | None] = mapped_column(Text)
    major: Mapped[str | None] = mapped_column(Text)
    graduation_year: Mapped[int | None] = mapped_column(Integer)
    candidate_type: Mapped[str | None] = mapped_column(Text)
    expected_salary: Mapped[str | None] = mapped_column(Text)
    profile_summary: Mapped[str | None] = mapped_column(Text)
    raw_card: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")

    profile: Mapped[CandidateProfile | None] = relationship(
        back_populates="candidate", uselist=False, cascade="all, delete-orphan"
    )
    resumes: Mapped[list[Resume]] = relationship(back_populates="candidate", cascade="all, delete-orphan")
    interactions: Mapped[list[Interaction]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )
    scores: Mapped[list[Score]] = relationship(back_populates="candidate", cascade="all, delete-orphan")
    actions: Mapped[list[ActionQueueItem]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("age is null or age between 16 and 80", name="candidates_age_check"),
        CheckConstraint(
            "graduation_year is null or graduation_year between 1980 and 2100",
            name="candidates_graduation_year_check",
        ),
        Index("candidates_status_updated_idx", "status", "updated_at"),
        Index("candidates_source_status_idx", "source", "status"),
        Index("candidates_school_idx", "school"),
    )


class CandidateProfile(Base, TimestampMixin):
    __tablename__ = "candidate_profiles"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    skills: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default="[]")
    highlights: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default="[]")
    risks: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default="[]")
    profile_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")

    candidate: Mapped[Candidate] = relationship(back_populates="profile")

    __table_args__ = (Index("candidate_profiles_candidate_id_idx", "candidate_id"),)


class Resume(Base, TimestampMixin):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(Text)
    file_path: Mapped[str | None] = mapped_column(Text)
    parsed_text: Mapped[str | None] = mapped_column(Text)
    ocr_text: Mapped[str | None] = mapped_column(Text)
    parse_status: Mapped[str] = mapped_column(Text, nullable=False, server_default="pending")

    candidate: Mapped[Candidate] = relationship(back_populates="resumes")

    __table_args__ = (
        Index("resumes_candidate_status_idx", "candidate_id", "parse_status"),
        CheckConstraint(
            "parse_status in ('pending','ok','failed','needs_review')",
            name="resumes_parse_status_check",
        ),
    )


class Interaction(Base):
    __tablename__ = "interactions"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    direction: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    candidate: Mapped[Candidate] = relationship(back_populates="interactions")

    __table_args__ = (
        CheckConstraint("direction in ('in','out','system')", name="interactions_direction_check"),
        Index("interactions_candidate_time_idx", "candidate_id", "occurred_at"),
        Index("interactions_kind_time_idx", "kind", "occurred_at"),
    )


class Score(Base, TimestampMixin):
    __tablename__ = "scores"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    total_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    dimensions: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    rationale: Mapped[str | None] = mapped_column(Text)

    candidate: Mapped[Candidate] = relationship(back_populates="scores")
    job: Mapped[Job] = relationship(back_populates="scores")

    __table_args__ = (
        UniqueConstraint("candidate_id", "job_id", name="scores_candidate_job_uq"),
        CheckConstraint("total_score >= 0 and total_score <= 100", name="scores_total_score_check"),
        Index("scores_job_total_idx", "job_id", "total_score"),
        Index("scores_candidate_id_idx", "candidate_id"),
    )


class Recommendation(Base, TimestampMixin):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    recommendation_date: Mapped[date] = mapped_column(Date, nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint(
            "job_id", "candidate_id", "recommendation_date", name="recommendations_daily_candidate_uq"
        ),
        Index("recommendations_job_date_rank_idx", "job_id", "recommendation_date", "rank"),
        Index("recommendations_candidate_id_idx", "candidate_id"),
    )


class ActionQueueItem(Base, TimestampMixin):
    __tablename__ = "action_queue"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    candidate_id: Mapped[int | None] = mapped_column(ForeignKey("candidates.id", ondelete="SET NULL"))
    job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id", ondelete="SET NULL"))
    action_type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="pending")
    risk_level: Mapped[str] = mapped_column(Text, nullable=False, server_default="low")
    draft_message: Mapped[str | None] = mapped_column(Text)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")

    candidate: Mapped[Candidate | None] = relationship(back_populates="actions")
    job: Mapped[Job | None] = relationship(back_populates="actions")

    __table_args__ = (
        CheckConstraint(
            "status in ('pending','approved','rejected','executed','failed')",
            name="action_queue_status_check",
        ),
        CheckConstraint(
            "risk_level in ('low','medium','high')",
            name="action_queue_risk_level_check",
        ),
        Index("action_queue_status_scheduled_idx", "status", "scheduled_at"),
        Index("action_queue_candidate_id_idx", "candidate_id"),
        Index("action_queue_job_id_idx", "job_id"),
    )


class DailyQuota(Base, TimestampMixin):
    __tablename__ = "daily_quota"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    quota_date: Mapped[date] = mapped_column(Date, nullable=False)
    quota_type: Mapped[str] = mapped_column(Text, nullable=False)
    used_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    max_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="50")

    __table_args__ = (
        UniqueConstraint("quota_date", "quota_type", name="daily_quota_date_type_uq"),
        CheckConstraint("used_count >= 0 and max_count >= 0", name="daily_quota_non_negative_check"),
    )


class WorkflowRun(Base, TimestampMixin):
    __tablename__ = "workflow_runs"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    workflow_name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="running")
    current_node: Mapped[str | None] = mapped_column(Text)
    state_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    error_message: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (Index("workflow_runs_name_status_idx", "workflow_name", "status"),)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    action_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_type: Mapped[str | None] = mapped_column(Text)
    entity_id: Mapped[int | None] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="ok")
    detail: Mapped[str | None] = mapped_column(Text)
    screenshot_path: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("audit_logs_action_time_idx", "action_type", "created_at"),
        Index("audit_logs_entity_idx", "entity_type", "entity_id"),
    )
