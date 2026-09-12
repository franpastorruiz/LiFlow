"""Add canonical activity keys to life events.

Revision ID: 20260912_03
Revises: 20260912_02
Create Date: 2026-09-12
"""

from alembic import op
import sqlalchemy as sa


revision = "20260912_03"
down_revision = "20260912_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("life_events", sa.Column("activity_key", sa.String(length=64), nullable=True))
    op.execute(
        "UPDATE life_events SET activity_key = 'bjj' "
        "WHERE lower(regexp_replace(activity, '[^a-zA-Z0-9]+', '', 'g')) "
        "IN ('bjj', 'jiujitsu', 'brazilianjiujitsu')"
    )


def downgrade() -> None:
    op.drop_column("life_events", "activity_key")
