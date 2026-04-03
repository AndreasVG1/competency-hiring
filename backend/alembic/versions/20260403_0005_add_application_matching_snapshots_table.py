"""add application matching snapshots table

Revision ID: 20260403_0005
Revises: 20260401_0004
Create Date: 2026-04-03 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260403_0005"
down_revision = "20260401_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "application_matching_snapshots",
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("algorithm_version", sa.String(length=255), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("result_payload", sa.JSON(none_as_null=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            ondelete="CASCADE",
            name="fk_application_matching_snapshots_application_id_applications",
        ),
        sa.PrimaryKeyConstraint("application_id", name="pk_application_matching_snapshots"),
    )


def downgrade() -> None:
    op.drop_table("application_matching_snapshots")
