"""allow extension chat detail sweep command

Revision ID: 20260626_0003
Revises: 20260626_0002
Create Date: 2026-06-26 00:00:00
"""
from typing import Sequence, Union

from alembic import op

revision: str = "20260626_0003"
down_revision: Union[str, None] = "20260626_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("extension_commands_type_check", "extension_commands", type_="check")
    op.create_check_constraint(
        "extension_commands_type_check",
        "extension_commands",
        "command_type in ('scan_chats','scan_chat_details','read_current_chat','scan_talents')",
    )


def downgrade() -> None:
    op.drop_constraint("extension_commands_type_check", "extension_commands", type_="check")
    op.create_check_constraint(
        "extension_commands_type_check",
        "extension_commands",
        "command_type in ('scan_chats','read_current_chat','scan_talents')",
    )
