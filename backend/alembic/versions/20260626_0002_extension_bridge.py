"""add Chrome extension bridge

Revision ID: 20260626_0002
Revises: 20260624_0001
Create Date: 2026-06-26 00:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260626_0002"
down_revision: Union[str, None] = "20260624_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "extension_sessions",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("extension_id", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default="offline", nullable=False),
        sa.Column("page_url", sa.Text(), nullable=True),
        sa.Column("page_title", sa.Text(), nullable=True),
        sa.Column("page_type", sa.Text(), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status in ('online','offline','unsupported_page','error')",
            name="extension_sessions_status_check",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("extension_id"),
    )
    op.create_index("extension_sessions_last_seen_idx", "extension_sessions", ["last_seen_at"])

    op.create_table(
        "extension_commands",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("extension_id", sa.Text(), nullable=True),
        sa.Column("command_type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default="queued", nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "command_type in ('scan_chats','scan_chat_details','read_current_chat','scan_talents')",
            name="extension_commands_type_check",
        ),
        sa.CheckConstraint(
            "status in ('queued','running','completed','failed')",
            name="extension_commands_status_check",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "extension_commands_status_created_idx",
        "extension_commands",
        ["status", "created_at"],
    )
    op.create_index(
        "extension_commands_extension_status_idx",
        "extension_commands",
        ["extension_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("extension_commands_extension_status_idx", table_name="extension_commands")
    op.drop_index("extension_commands_status_created_idx", table_name="extension_commands")
    op.drop_table("extension_commands")
    op.drop_index("extension_sessions_last_seen_idx", table_name="extension_sessions")
    op.drop_table("extension_sessions")
