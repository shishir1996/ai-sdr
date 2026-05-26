"""Add email threading columns to email_messages

Revision ID: 002
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("email_messages", sa.Column("direction", sa.String(20), nullable=True, server_default="outbound"))
    op.add_column("email_messages", sa.Column("in_reply_to", sa.String(255), nullable=True))
    op.add_column("email_messages", sa.Column("references", sa.Text(), nullable=True))
    op.add_column("email_messages", sa.Column("thread_id", sa.String(255), nullable=True))
    op.add_column("email_messages", sa.Column("rfc_message_id", sa.String(255), nullable=True))
    op.create_index("ix_email_messages_in_reply_to", "email_messages", ["in_reply_to"])
    op.create_index("ix_email_messages_thread_id", "email_messages", ["thread_id"])


def downgrade() -> None:
    op.drop_index("ix_email_messages_thread_id", table_name="email_messages")
    op.drop_index("ix_email_messages_in_reply_to", table_name="email_messages")
    op.drop_column("email_messages", "rfc_message_id")
    op.drop_column("email_messages", "thread_id")
    op.drop_column("email_messages", "references")
    op.drop_column("email_messages", "in_reply_to")
    op.drop_column("email_messages", "direction")
