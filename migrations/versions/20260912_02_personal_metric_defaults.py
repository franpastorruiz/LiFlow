"""Add scoped personal metric defaults and observation origin.

Revision ID: 20260912_02
Revises: 20260912_01
Create Date: 2026-09-12
"""

from alembic import op
import sqlalchemy as sa


revision = "20260912_02"
down_revision = "20260912_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "metric_defaults",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "metric_definition_id",
            sa.Integer(),
            sa.ForeignKey("metric_definitions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("scope_key", sa.String(length=64), nullable=False),
        sa.Column("value_number", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("value_text", sa.Text(), nullable=True),
        sa.Column("value_boolean", sa.Boolean(), nullable=True),
        sa.Column("unit", sa.String(length=40), nullable=True),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("source_kind", sa.String(length=32), nullable=False, server_default="user_statement"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("metric_definition_id", "scope_key", name="uq_metric_default_scope"),
        sa.CheckConstraint(
            "(CASE WHEN value_number IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN value_text IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN value_boolean IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name="ck_default_one_value",
        ),
    )
    op.add_column(
        "metric_observations",
        sa.Column("value_origin", sa.String(length=16), nullable=False, server_default="explicit"),
    )


def downgrade() -> None:
    op.drop_column("metric_observations", "value_origin")
    op.drop_table("metric_defaults")
