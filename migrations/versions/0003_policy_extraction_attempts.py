"""Add append-only structured policy extraction attempts.

Revision ID: 0003_policy_extraction
Revises: 0002_enterprise_impact
Create Date: 2026-08-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_policy_extraction"
down_revision: str | None = "0002_enterprise_impact"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "policy_extraction_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("policy_change_id", sa.String(length=100), nullable=False),
        sa.Column("policy_text_snapshot", sa.Text(), nullable=False),
        sa.Column("support_status", sa.String(length=30), nullable=True),
        sa.Column("validation_outcome", sa.String(length=30), nullable=False),
        sa.Column("model_provider", sa.String(length=100), nullable=False),
        sa.Column("model_identifier", sa.String(length=200), nullable=False),
        sa.Column("prompt_version", sa.String(length=100), nullable=False),
        sa.Column("schema_version", sa.String(length=100), nullable=False),
        sa.Column(
            "raw_output",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "parsed_output",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "candidate_rules",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "accepted_rules",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "provenance",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "findings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "validation_errors",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "support_status IS NULL OR support_status IN ('supported', 'unsupported')",
            name="ck_policy_extraction_attempts_support_status",
        ),
        sa.CheckConstraint(
            "validation_outcome IN ('accepted', 'unsupported', 'validation_failed')",
            name="ck_policy_extraction_attempts_validation_outcome",
        ),
        sa.ForeignKeyConstraint(["policy_change_id"], ["policy_changes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_policy_extraction_attempts_policy_change_id",
        "policy_extraction_attempts",
        ["policy_change_id"],
    )
    op.execute(
        """
        CREATE FUNCTION reject_policy_extraction_attempt_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'policy extraction attempts are append-only';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER policy_extraction_attempts_append_only
        BEFORE UPDATE OR DELETE ON policy_extraction_attempts
        FOR EACH ROW EXECUTE FUNCTION reject_policy_extraction_attempt_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER policy_extraction_attempts_append_only ON policy_extraction_attempts")
    op.execute("DROP FUNCTION reject_policy_extraction_attempt_mutation()")
    op.drop_index(
        "ix_policy_extraction_attempts_policy_change_id",
        table_name="policy_extraction_attempts",
    )
    op.drop_table("policy_extraction_attempts")
