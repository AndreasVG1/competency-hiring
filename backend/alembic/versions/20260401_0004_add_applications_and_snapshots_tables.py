"""add applications and snapshots tables

Revision ID: 20260401_0004
Revises: 20260401_0003
Create Date: 2026-04-01 00:00:01
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260401_0004"
down_revision = "20260401_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "applications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_offer_id", sa.Integer(), nullable=False),
        sa.Column("seeker_user_id", sa.Integer(), nullable=False),
        sa.Column("consent_given_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["job_offer_id"],
            ["job_offers.id"],
            ondelete="CASCADE",
            name="fk_applications_job_offer_id_job_offers",
        ),
        sa.ForeignKeyConstraint(
            ["seeker_user_id"],
            ["users.id"],
            ondelete="CASCADE",
            name="fk_applications_seeker_user_id_users",
        ),
        sa.UniqueConstraint(
            "job_offer_id",
            "seeker_user_id",
            name="uq_applications_job_offer_id_seeker_user_id",
        ),
    )
    op.create_index("ix_applications_job_offer_id", "applications", ["job_offer_id"])
    op.create_index("ix_applications_seeker_user_id", "applications", ["seeker_user_id"])

    op.create_table(
        "application_snapshots",
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("occupation_key", sa.String(length=255), nullable=True),
        sa.Column("competencies", sa.JSON(), nullable=False),
        sa.Column("audit_metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            ondelete="CASCADE",
            name="fk_application_snapshots_application_id_applications",
        ),
        sa.PrimaryKeyConstraint("application_id", name="pk_application_snapshots"),
    )


def downgrade() -> None:
    op.drop_table("application_snapshots")

    op.drop_index("ix_applications_seeker_user_id", table_name="applications")
    op.drop_index("ix_applications_job_offer_id", table_name="applications")
    op.drop_table("applications")
