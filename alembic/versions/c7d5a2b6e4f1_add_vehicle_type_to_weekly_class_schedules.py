"""add_vehicle_type_to_weekly_class_schedules

Revision ID: c7d5a2b6e4f1
Revises: f2b8c6d9a4e1
Create Date: 2026-06-17 10:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7d5a2b6e4f1"
down_revision: str | None = "f2b8c6d9a4e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "weekly_class_schedules",
        sa.Column("vehicle_type", sa.String(), server_default="motorbike", nullable=False),
    )
    op.create_check_constraint(
        "ck_weekly_class_schedules_vehicle_type",
        "weekly_class_schedules",
        "vehicle_type IN ('motorbike', 'walking', 'bus', 'car', 'bicycle')",
    )
    op.alter_column("weekly_class_schedules", "vehicle_type", server_default=None)


def downgrade() -> None:
    op.drop_constraint(
        "ck_weekly_class_schedules_vehicle_type",
        "weekly_class_schedules",
        type_="check",
    )
    op.drop_column("weekly_class_schedules", "vehicle_type")
