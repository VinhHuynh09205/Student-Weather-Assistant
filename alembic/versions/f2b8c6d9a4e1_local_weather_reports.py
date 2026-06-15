"""local_weather_reports

Revision ID: f2b8c6d9a4e1
Revises: e6c4f1d2a9b7
Create Date: 2026-06-15 20:10:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f2b8c6d9a4e1"
down_revision: str | None = "e6c4f1d2a9b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "local_weather_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("location_name", sa.String(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("reported_condition", sa.String(), nullable=False),
        sa.Column("intensity", sa.String(), nullable=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "reported_condition IN ('rain', 'no_rain', 'storm')",
            name="ck_local_weather_reports_condition",
        ),
        sa.CheckConstraint(
            "intensity IS NULL OR intensity IN ('light', 'moderate', 'heavy')",
            name="ck_local_weather_reports_intensity",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_local_weather_reports_user_id", "local_weather_reports", ["user_id"])
    op.create_index(
        "ix_local_weather_reports_user_active_expires",
        "local_weather_reports",
        ["user_id", "is_active", "expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_local_weather_reports_user_active_expires", table_name="local_weather_reports")
    op.drop_index("ix_local_weather_reports_user_id", table_name="local_weather_reports")
    op.drop_table("local_weather_reports")
