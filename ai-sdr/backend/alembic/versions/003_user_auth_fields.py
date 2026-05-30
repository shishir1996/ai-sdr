"""Add auth-related fields to users table

Revision ID: 003
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("phone", sa.String(50), nullable=True))
    op.add_column("users", sa.Column("country_code", sa.String(10), nullable=True))
    op.add_column("users", sa.Column("email_verified", sa.Boolean(), nullable=True, server_default=sa.text("false")))
    op.add_column("users", sa.Column("supabase_uid", sa.String(255), nullable=True))
    op.create_index("ix_users_supabase_uid", "users", ["supabase_uid"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_supabase_uid", table_name="users")
    op.drop_column("users", "supabase_uid")
    op.drop_column("users", "email_verified")
    op.drop_column("users", "country_code")
    op.drop_column("users", "phone")
