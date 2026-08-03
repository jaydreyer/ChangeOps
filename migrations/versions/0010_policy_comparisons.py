"""Add immutable deterministic policy comparisons.

Revision ID: 0010_policy_comparisons
Revises: 0009_learning_execution
Create Date: 2026-08-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010_policy_comparisons"
down_revision: str | None = "0009_learning_execution"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_policy_changes_id_organization",
        "policy_changes",
        ["id", "organization_id"],
    )
    op.create_unique_constraint(
        "uq_policy_extraction_attempts_id_policy",
        "policy_extraction_attempts",
        ["id", "policy_change_id"],
    )
    op.create_table(
        "policy_comparisons",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.String(length=100), nullable=False),
        sa.Column("baseline_policy_change_id", sa.String(length=100), nullable=False),
        sa.Column("proposed_policy_change_id", sa.String(length=100), nullable=False),
        sa.Column("baseline_extraction_attempt_id", sa.Uuid(), nullable=False),
        sa.Column("proposed_extraction_attempt_id", sa.Uuid(), nullable=False),
        sa.Column(
            "baseline_policy_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "proposed_policy_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("comparison_contract_version", sa.String(length=100), nullable=False),
        sa.Column("comparison_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "baseline_policy_change_id <> proposed_policy_change_id",
            name="ck_policy_comparisons_distinct_policies",
        ),
        sa.CheckConstraint(
            "comparison_contract_version = 'international-travel-policy-comparison-v1'",
            name="ck_policy_comparisons_contract_version",
        ),
        sa.CheckConstraint(
            "length(comparison_fingerprint) = 64",
            name="ck_policy_comparisons_fingerprint_length",
        ),
        sa.CheckConstraint(
            "length(btrim(created_by)) > 0",
            name="ck_policy_comparisons_creator",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(
            ["baseline_policy_change_id", "organization_id"],
            ["policy_changes.id", "policy_changes.organization_id"],
            name="fk_policy_comparisons_baseline_policy_organization",
        ),
        sa.ForeignKeyConstraint(
            ["proposed_policy_change_id", "organization_id"],
            ["policy_changes.id", "policy_changes.organization_id"],
            name="fk_policy_comparisons_proposed_policy_organization",
        ),
        sa.ForeignKeyConstraint(
            ["baseline_extraction_attempt_id", "baseline_policy_change_id"],
            ["policy_extraction_attempts.id", "policy_extraction_attempts.policy_change_id"],
            name="fk_policy_comparisons_baseline_attempt_policy",
        ),
        sa.ForeignKeyConstraint(
            ["proposed_extraction_attempt_id", "proposed_policy_change_id"],
            ["policy_extraction_attempts.id", "policy_extraction_attempts.policy_change_id"],
            name="fk_policy_comparisons_proposed_attempt_policy",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "comparison_fingerprint",
            name="uq_policy_comparisons_fingerprint",
        ),
    )
    for column in (
        "organization_id",
        "baseline_policy_change_id",
        "proposed_policy_change_id",
        "baseline_extraction_attempt_id",
        "proposed_extraction_attempt_id",
    ):
        op.create_index(
            f"ix_policy_comparisons_{column}",
            "policy_comparisons",
            [column],
        )

    op.create_table(
        "policy_comparison_differences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("policy_comparison_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("rule_identity", sa.String(length=300), nullable=False),
        sa.Column("field_path", sa.String(length=200), nullable=False),
        sa.Column("change_type", sa.String(length=20), nullable=False),
        sa.Column(
            "baseline_value",
            postgresql.JSONB(astext_type=sa.Text(), none_as_null=True),
            nullable=True,
        ),
        sa.Column(
            "proposed_value",
            postgresql.JSONB(astext_type=sa.Text(), none_as_null=True),
            nullable=True,
        ),
        sa.Column("material", sa.Boolean(), nullable=False),
        sa.Column("reason_code", sa.String(length=100), nullable=False),
        sa.Column(
            "baseline_provenance",
            postgresql.JSONB(astext_type=sa.Text(), none_as_null=True),
            nullable=True,
        ),
        sa.Column(
            "proposed_provenance",
            postgresql.JSONB(astext_type=sa.Text(), none_as_null=True),
            nullable=True,
        ),
        sa.CheckConstraint(
            "change_type IN ('added', 'removed', 'modified')",
            name="ck_policy_comparison_differences_change_type",
        ),
        sa.CheckConstraint(
            "sequence > 0",
            name="ck_policy_comparison_differences_sequence",
        ),
        sa.CheckConstraint(
            "material",
            name="ck_policy_comparison_differences_material",
        ),
        sa.CheckConstraint(
            "(change_type = 'added' AND baseline_value IS NULL "
            "AND proposed_value IS NOT NULL AND baseline_provenance IS NULL "
            "AND proposed_provenance IS NOT NULL) "
            "OR (change_type = 'removed' AND baseline_value IS NOT NULL "
            "AND proposed_value IS NULL AND baseline_provenance IS NOT NULL "
            "AND proposed_provenance IS NULL) "
            "OR (change_type = 'modified' AND baseline_value IS NOT NULL "
            "AND proposed_value IS NOT NULL AND baseline_provenance IS NOT NULL "
            "AND proposed_provenance IS NOT NULL)",
            name="ck_policy_comparison_differences_sides",
        ),
        sa.ForeignKeyConstraint(
            ["policy_comparison_id"],
            ["policy_comparisons.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "policy_comparison_id",
            "sequence",
            name="uq_policy_comparison_differences_sequence",
        ),
        sa.UniqueConstraint(
            "policy_comparison_id",
            "rule_identity",
            name="uq_policy_comparison_differences_identity",
        ),
    )
    op.create_index(
        "ix_policy_comparison_differences_policy_comparison_id",
        "policy_comparison_differences",
        ["policy_comparison_id"],
    )

    op.execute(
        """
        CREATE FUNCTION validate_policy_comparison_insert()
        RETURNS trigger AS $$
        DECLARE
            baseline_outcome text;
            proposed_outcome text;
        BEGIN
            SELECT validation_outcome INTO baseline_outcome
            FROM policy_extraction_attempts
            WHERE id = NEW.baseline_extraction_attempt_id;
            SELECT validation_outcome INTO proposed_outcome
            FROM policy_extraction_attempts
            WHERE id = NEW.proposed_extraction_attempt_id;

            IF baseline_outcome IS DISTINCT FROM 'accepted'
               OR proposed_outcome IS DISTINCT FROM 'accepted' THEN
                RAISE EXCEPTION 'policy comparison requires accepted extraction attempts';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER policy_comparisons_validate_insert
        BEFORE INSERT ON policy_comparisons
        FOR EACH ROW EXECUTE FUNCTION validate_policy_comparison_insert()
        """
    )
    op.execute(
        """
        CREATE FUNCTION reject_policy_comparison_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'policy comparisons are immutable';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER policy_comparisons_immutable
        BEFORE UPDATE OR DELETE ON policy_comparisons
        FOR EACH ROW EXECUTE FUNCTION reject_policy_comparison_mutation()
        """
    )
    op.execute(
        """
        CREATE TRIGGER policy_comparison_differences_immutable
        BEFORE UPDATE OR DELETE ON policy_comparison_differences
        FOR EACH ROW EXECUTE FUNCTION reject_policy_comparison_mutation()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER policy_comparison_differences_immutable ON policy_comparison_differences"
    )
    op.execute("DROP TRIGGER policy_comparisons_immutable ON policy_comparisons")
    op.execute("DROP FUNCTION reject_policy_comparison_mutation()")
    op.execute("DROP TRIGGER policy_comparisons_validate_insert ON policy_comparisons")
    op.execute("DROP FUNCTION validate_policy_comparison_insert()")
    op.drop_table("policy_comparison_differences")
    op.drop_table("policy_comparisons")
    op.drop_constraint(
        "uq_policy_extraction_attempts_id_policy",
        "policy_extraction_attempts",
        type_="unique",
    )
    op.drop_constraint(
        "uq_policy_changes_id_organization",
        "policy_changes",
        type_="unique",
    )
