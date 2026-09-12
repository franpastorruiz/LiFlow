"""Persist tracker activity definitions and event activity references.

Revision ID: 20260912_04
Revises: 20260912_03
Create Date: 2026-09-12
"""

from alembic import op
import sqlalchemy as sa


revision = "20260912_04"
down_revision = "20260912_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "activity_definitions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tracker_id", sa.Integer(), sa.ForeignKey("trackers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "parent_activity_definition_id",
            sa.Integer(),
            sa.ForeignKey("activity_definitions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("tracker_id", "key", name="uq_activity_tracker_key"),
    )
    op.add_column(
        "life_events",
        sa.Column(
            "activity_definition_id",
            sa.Integer(),
            sa.ForeignKey("activity_definitions.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    # Legacy rows that already had an activity_key become definitions without
    # guessing synonyms or inventing relationships.
    op.execute(
        "INSERT INTO activity_definitions (tracker_id, key, display_name, description) "
        "SELECT DISTINCT tracker_id, activity_key, activity_key, 'Migrated legacy activity' "
        "FROM life_events WHERE activity_key IS NOT NULL "
        "ON CONFLICT (tracker_id, key) DO NOTHING"
    )
    op.execute(
        "UPDATE life_events AS event SET activity_definition_id = definition.id "
        "FROM activity_definitions AS definition "
        "WHERE event.tracker_id = definition.tracker_id AND event.activity_key = definition.key"
    )


def downgrade() -> None:
    op.drop_column("life_events", "activity_definition_id")
    op.drop_table("activity_definitions")
