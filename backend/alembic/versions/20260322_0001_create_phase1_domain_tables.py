"""create phase 1 domain tables

Revision ID: 20260322_0001
Revises:
Create Date: 2026-03-22 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260322_0001"
down_revision = None
branch_labels = None
depends_on = None


user_role_enum = sa.Enum(
    "job_seeker",
    "recruiter",
    name="userrole",
    native_enum=False,
    create_constraint=True,
)
competency_level_enum = sa.Enum(
    "beginner",
    "intermediate",
    "advanced",
    name="competencylevel",
    native_enum=False,
    create_constraint=True,
)
job_offer_status_enum = sa.Enum(
    "draft",
    name="jobofferstatus",
    native_enum=False,
    create_constraint=True,
)
requirement_priority_enum = sa.Enum(
    "must_have",
    "important",
    "nice_to_have",
    name="requirementpriority",
    native_enum=False,
    create_constraint=True,
)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", user_role_enum, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "job_seeker_profiles",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("occupation_key", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name="fk_job_seeker_profiles_user_id_users"),
        sa.PrimaryKeyConstraint("user_id", name="pk_job_seeker_profiles"),
    )

    op.create_table(
        "job_seeker_competencies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("competency_key", sa.String(length=255), nullable=False),
        sa.Column("level", competency_level_enum, nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
            name="fk_job_seeker_competencies_user_id_users",
        ),
        sa.UniqueConstraint(
            "user_id",
            "competency_key",
            name="uq_job_seeker_competencies_user_id_competency_key",
        ),
    )
    op.create_index(
        "ix_job_seeker_competencies_user_id",
        "job_seeker_competencies",
        ["user_id"],
    )
    op.create_index(
        "ix_job_seeker_competencies_competency_key",
        "job_seeker_competencies",
        ["competency_key"],
    )

    op.create_table(
        "recruiter_profiles",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("contact_name", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name="fk_recruiter_profiles_user_id_users"),
        sa.PrimaryKeyConstraint("user_id", name="pk_recruiter_profiles"),
    )

    op.create_table(
        "job_offers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("recruiter_user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", job_offer_status_enum, nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["recruiter_user_id"], ["users.id"], ondelete="CASCADE", name="fk_job_offers_recruiter_user_id_users"),
    )
    op.create_index("ix_job_offers_recruiter_user_id", "job_offers", ["recruiter_user_id"])

    op.create_table(
        "job_offer_requirements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_offer_id", sa.Integer(), nullable=False),
        sa.Column("competency_key", sa.String(length=255), nullable=False),
        sa.Column("priority", requirement_priority_enum, nullable=False),
        sa.ForeignKeyConstraint(
            ["job_offer_id"],
            ["job_offers.id"],
            ondelete="CASCADE",
            name="fk_job_offer_requirements_job_offer_id_job_offers",
        ),
        sa.UniqueConstraint(
            "job_offer_id",
            "competency_key",
            name="uq_job_offer_requirements_job_offer_id_competency_key",
        ),
    )
    op.create_index(
        "ix_job_offer_requirements_job_offer_id",
        "job_offer_requirements",
        ["job_offer_id"],
    )
    op.create_index(
        "ix_job_offer_requirements_competency_key",
        "job_offer_requirements",
        ["competency_key"],
    )


def downgrade() -> None:
    op.drop_index("ix_job_offer_requirements_competency_key", table_name="job_offer_requirements")
    op.drop_index("ix_job_offer_requirements_job_offer_id", table_name="job_offer_requirements")
    op.drop_table("job_offer_requirements")

    op.drop_index("ix_job_offers_recruiter_user_id", table_name="job_offers")
    op.drop_table("job_offers")

    op.drop_table("recruiter_profiles")

    op.drop_index("ix_job_seeker_competencies_competency_key", table_name="job_seeker_competencies")
    op.drop_index("ix_job_seeker_competencies_user_id", table_name="job_seeker_competencies")
    op.drop_table("job_seeker_competencies")

    op.drop_table("job_seeker_profiles")
    op.drop_table("users")
