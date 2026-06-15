"""weekly_class_schedules

Revision ID: e6c4f1d2a9b7
Revises: a81237dc35d2
Create Date: 2026-06-14 20:45:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e6c4f1d2a9b7"
down_revision: str | None = "a81237dc35d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "weekly_class_schedules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("subject_name", sa.String(), nullable=False),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("location_name", sa.String(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("timezone", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("notify_before_minutes", sa.Integer(), nullable=False),
        sa.Column("rain_alert_enabled", sa.Boolean(), nullable=False),
        sa.Column("storm_alert_enabled", sa.Boolean(), nullable=False),
        sa.Column("semester_start_date", sa.Date(), nullable=True),
        sa.Column("semester_end_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "day_of_week >= 0 AND day_of_week <= 6",
            name="ck_weekly_class_schedules_day_of_week",
        ),
        sa.CheckConstraint(
            "notify_before_minutes >= 0",
            name="ck_weekly_class_schedules_notify_before_minutes",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_weekly_class_schedules_user_id",
        "weekly_class_schedules",
        ["user_id"],
    )
    op.create_index(
        "ix_weekly_class_schedules_user_active_day",
        "weekly_class_schedules",
        ["user_id", "is_active", "day_of_week"],
    )

    op.add_column("notifications", sa.Column("occurrence_key", sa.String(), nullable=True))
    op.add_column("notifications", sa.Column("risk_level", sa.String(), nullable=True))
    op.add_column("notifications", sa.Column("content_hash", sa.String(), nullable=True))
    op.create_index("ix_notifications_occurrence_key", "notifications", ["occurrence_key"])
    op.create_index(
        "ix_notifications_user_occurrence_channel",
        "notifications",
        ["user_id", "occurrence_key", "channel"],
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_user_occurrence_channel", table_name="notifications")
    op.drop_index("ix_notifications_occurrence_key", table_name="notifications")
    op.drop_column("notifications", "content_hash")
    op.drop_column("notifications", "risk_level")
    op.drop_column("notifications", "occurrence_key")

    op.drop_index("ix_weekly_class_schedules_user_active_day", table_name="weekly_class_schedules")
    op.drop_index("ix_weekly_class_schedules_user_id", table_name="weekly_class_schedules")
    op.drop_table("weekly_class_schedules")
