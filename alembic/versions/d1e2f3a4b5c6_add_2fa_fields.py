"""add_2fa_fields

Revision ID: d1e2f3a4b5c6
Revises: c7d5a2b6e4f1
Create Date: 2026-07-01 20:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d1e2f3a4b5c6"
down_revision: str | None = "c7d5a2b6e4f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("totp_secret", sa.String(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("is_2fa_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "is_2fa_enabled")
    op.drop_column("users", "totp_secret")
