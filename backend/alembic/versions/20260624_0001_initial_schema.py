"""initial schema

Revision ID: 20260624_0001
Revises:
Create Date: 2026-06-24 00:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260624_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("city", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("experience_requirement", sa.Text(), nullable=True),
        sa.Column("education_requirement", sa.Text(), nullable=True),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column("keywords", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "salary_min is null or salary_max is null or salary_min <= salary_max",
            name="jobs_salary_range_check",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("jobs_active_created_idx", "jobs", ["is_active", "created_at"])

    op.create_table(
        "candidates",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("boss_uid", sa.Text(), nullable=True),
        sa.Column("source", sa.Text(), server_default="manual", nullable=False),
        sa.Column("status", sa.Text(), server_default="discovered", nullable=False),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("current_role", sa.Text(), nullable=True),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("city", sa.Text(), nullable=True),
        sa.Column("education_level", sa.Text(), nullable=True),
        sa.Column("school", sa.Text(), nullable=True),
        sa.Column("major", sa.Text(), nullable=True),
        sa.Column("graduation_year", sa.Integer(), nullable=True),
        sa.Column("candidate_type", sa.Text(), nullable=True),
        sa.Column("expected_salary", sa.Text(), nullable=True),
        sa.Column("profile_summary", sa.Text(), nullable=True),
        sa.Column("raw_card", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("age is null or age between 16 and 80", name="candidates_age_check"),
        sa.CheckConstraint(
            "graduation_year is null or graduation_year between 1980 and 2100",
            name="candidates_graduation_year_check",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("boss_uid"),
    )
    op.create_index("candidates_school_idx", "candidates", ["school"])
    op.create_index("candidates_source_status_idx", "candidates", ["source", "status"])
    op.create_index("candidates_status_updated_idx", "candidates", ["status", "updated_at"])

    op.create_table(
        "daily_quota",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("quota_date", sa.Date(), nullable=False),
        sa.Column("quota_type", sa.Text(), nullable=False),
        sa.Column("used_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_count", sa.Integer(), server_default="50", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("used_count >= 0 and max_count >= 0", name="daily_quota_non_negative_check"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("quota_date", "quota_type", name="daily_quota_date_type_uq"),
    )

    op.create_table(
        "workflow_runs",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("workflow_name", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default="running", nullable=False),
        sa.Column("current_node", sa.Text(), nullable=True),
        sa.Column("state_json", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("workflow_runs_name_status_idx", "workflow_runs", ["workflow_name", "status"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("action_type", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=True),
        sa.Column("entity_id", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.Text(), server_default="ok", nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("screenshot_path", sa.Text(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("audit_logs_action_time_idx", "audit_logs", ["action_type", "created_at"])
    op.create_index("audit_logs_entity_idx", "audit_logs", ["entity_type", "entity_id"])

    op.create_table(
        "candidate_profiles",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("candidate_id", sa.BigInteger(), nullable=False),
        sa.Column("skills", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("highlights", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("risks", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("profile_json", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("candidate_id"),
    )
    op.create_index("candidate_profiles_candidate_id_idx", "candidate_profiles", ["candidate_id"])

    op.create_table(
        "resumes",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("candidate_id", sa.BigInteger(), nullable=False),
        sa.Column("original_filename", sa.Text(), nullable=True),
        sa.Column("file_path", sa.Text(), nullable=True),
        sa.Column("parsed_text", sa.Text(), nullable=True),
        sa.Column("ocr_text", sa.Text(), nullable=True),
        sa.Column("parse_status", sa.Text(), server_default="pending", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "parse_status in ('pending','ok','failed','needs_review')",
            name="resumes_parse_status_check",
        ),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("resumes_candidate_status_idx", "resumes", ["candidate_id", "parse_status"])

    op.create_table(
        "interactions",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("candidate_id", sa.BigInteger(), nullable=False),
        sa.Column("direction", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("direction in ('in','out','system')", name="interactions_direction_check"),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("interactions_candidate_time_idx", "interactions", ["candidate_id", "occurred_at"])
    op.create_index("interactions_kind_time_idx", "interactions", ["kind", "occurred_at"])

    op.create_table(
        "scores",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("candidate_id", sa.BigInteger(), nullable=False),
        sa.Column("job_id", sa.BigInteger(), nullable=False),
        sa.Column("total_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("dimensions", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("total_score >= 0 and total_score <= 100", name="scores_total_score_check"),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("candidate_id", "job_id", name="scores_candidate_job_uq"),
    )
    op.create_index("scores_candidate_id_idx", "scores", ["candidate_id"])
    op.create_index("scores_job_total_idx", "scores", ["job_id", "total_score"])

    op.create_table(
        "recommendations",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("job_id", sa.BigInteger(), nullable=False),
        sa.Column("candidate_id", sa.BigInteger(), nullable=False),
        sa.Column("recommendation_date", sa.Date(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "job_id", "candidate_id", "recommendation_date", name="recommendations_daily_candidate_uq"
        ),
    )
    op.create_index(
        "recommendations_job_date_rank_idx",
        "recommendations",
        ["job_id", "recommendation_date", "rank"],
    )
    op.create_index("recommendations_candidate_id_idx", "recommendations", ["candidate_id"])

    op.create_table(
        "action_queue",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("candidate_id", sa.BigInteger(), nullable=True),
        sa.Column("job_id", sa.BigInteger(), nullable=True),
        sa.Column("action_type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default="pending", nullable=False),
        sa.Column("risk_level", sa.Text(), server_default="low", nullable=False),
        sa.Column("draft_message", sa.Text(), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status in ('pending','approved','rejected','executed','failed')",
            name="action_queue_status_check",
        ),
        sa.CheckConstraint(
            "risk_level in ('low','medium','high')",
            name="action_queue_risk_level_check",
        ),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("action_queue_candidate_id_idx", "action_queue", ["candidate_id"])
    op.create_index("action_queue_job_id_idx", "action_queue", ["job_id"])
    op.create_index("action_queue_status_scheduled_idx", "action_queue", ["status", "scheduled_at"])


def downgrade() -> None:
    op.drop_index("action_queue_status_scheduled_idx", table_name="action_queue")
    op.drop_index("action_queue_job_id_idx", table_name="action_queue")
    op.drop_index("action_queue_candidate_id_idx", table_name="action_queue")
    op.drop_table("action_queue")
    op.drop_index("recommendations_candidate_id_idx", table_name="recommendations")
    op.drop_index("recommendations_job_date_rank_idx", table_name="recommendations")
    op.drop_table("recommendations")
    op.drop_index("scores_job_total_idx", table_name="scores")
    op.drop_index("scores_candidate_id_idx", table_name="scores")
    op.drop_table("scores")
    op.drop_index("interactions_kind_time_idx", table_name="interactions")
    op.drop_index("interactions_candidate_time_idx", table_name="interactions")
    op.drop_table("interactions")
    op.drop_index("resumes_candidate_status_idx", table_name="resumes")
    op.drop_table("resumes")
    op.drop_index("candidate_profiles_candidate_id_idx", table_name="candidate_profiles")
    op.drop_table("candidate_profiles")
    op.drop_index("audit_logs_entity_idx", table_name="audit_logs")
    op.drop_index("audit_logs_action_time_idx", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index("workflow_runs_name_status_idx", table_name="workflow_runs")
    op.drop_table("workflow_runs")
    op.drop_table("daily_quota")
    op.drop_index("candidates_status_updated_idx", table_name="candidates")
    op.drop_index("candidates_source_status_idx", table_name="candidates")
    op.drop_index("candidates_school_idx", table_name="candidates")
    op.drop_table("candidates")
    op.drop_index("jobs_active_created_idx", table_name="jobs")
    op.drop_table("jobs")
