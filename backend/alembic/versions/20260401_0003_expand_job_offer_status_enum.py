"""expand job offer status enum values

Revision ID: 20260401_0003
Revises: 20260325_0002
Create Date: 2026-04-01 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260401_0003"
down_revision = "20260325_0002"
branch_labels = None
depends_on = None


old_job_offer_status_enum = sa.Enum(
    "draft",
    name="jobofferstatus",
    native_enum=False,
    create_constraint=True,
)
new_job_offer_status_enum = sa.Enum(
    "draft",
    "published",
    "archived",
    name="jobofferstatus",
    native_enum=False,
    create_constraint=True,
)


def upgrade() -> None:
    with op.batch_alter_table("job_offers", recreate="always") as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=old_job_offer_status_enum,
            type_=new_job_offer_status_enum,
            existing_nullable=False,
            existing_server_default="draft",
            server_default="draft",
        )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE job_offers SET status = 'draft' WHERE status IN ('published', 'archived')"
        )
    )
    with op.batch_alter_table("job_offers", recreate="always") as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=new_job_offer_status_enum,
            type_=old_job_offer_status_enum,
            existing_nullable=False,
            existing_server_default="draft",
            server_default="draft",
        )
