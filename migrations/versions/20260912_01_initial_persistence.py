"""Initial persistence tables.

Revision ID: 20260912_01
Revises:
Create Date: 2026-09-12
"""

from alembic import op
import sqlalchemy as sa


revision = "20260912_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("identifier", sa.String(length=255), nullable=False, unique=True),
        sa.Column("email", sa.String(length=255), nullable=True, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "trackers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tracker_key", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("user_id", "tracker_key", name="uq_tracker_user_key"),
    )
    op.create_table(
        "metric_definitions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tracker_id", sa.Integer(), sa.ForeignKey("trackers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("data_type", sa.String(length=16), nullable=False),
        sa.Column("preferred_unit", sa.String(length=40), nullable=True),
        sa.Column("aggregation", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tracker_id", "key", name="uq_metric_tracker_key"),
    )
    op.create_table(
        "life_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tracker_id", sa.Integer(), sa.ForeignKey("trackers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("activity", sa.String(length=100), nullable=False),
        sa.Column("occurred_on", sa.Date(), nullable=False),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "metric_observations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("life_event_id", sa.Integer(), sa.ForeignKey("life_events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("metric_definition_id", sa.Integer(), sa.ForeignKey("metric_definitions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("value_number", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("value_text", sa.Text(), nullable=True),
        sa.Column("value_boolean", sa.Boolean(), nullable=True),
        sa.Column("unit", sa.String(length=40), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "(CASE WHEN value_number IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN value_text IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN value_boolean IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name="ck_observation_one_value",
        ),
    )


def downgrade() -> None:
    op.drop_table("metric_observations")
    op.drop_table("life_events")
    op.drop_table("metric_definitions")
    op.drop_table("trackers")
    op.drop_table("users")
