"""Add immutable enterprise impact deltas.

Revision ID: 0011_enterprise_impact_delta
Revises: 0010_policy_comparisons
Create Date: 2026-08-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011_enterprise_impact_delta"
down_revision: str | None = "0010_policy_comparisons"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "policy_comparison_impact_deltas",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("policy_comparison_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.String(length=100), nullable=False),
        sa.Column("baseline_assessment_id", sa.Uuid(), nullable=False),
        sa.Column("proposed_assessment_id", sa.Uuid(), nullable=False),
        sa.Column("impact_delta_contract_version", sa.String(length=100), nullable=False),
        sa.Column("impact_delta_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "impact_delta_contract_version = 'enterprise-impact-delta-v1'",
            name="ck_policy_comparison_impact_deltas_contract_version",
        ),
        sa.CheckConstraint(
            "baseline_assessment_id <> proposed_assessment_id",
            name="ck_policy_comparison_impact_deltas_distinct_assessments",
        ),
        sa.CheckConstraint(
            "length(impact_delta_fingerprint) = 64",
            name="ck_policy_comparison_impact_deltas_fingerprint_length",
        ),
        sa.CheckConstraint(
            "length(btrim(created_by)) > 0",
            name="ck_policy_comparison_impact_deltas_creator",
        ),
        sa.ForeignKeyConstraint(["policy_comparison_id"], ["policy_comparisons.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["baseline_assessment_id"], ["impact_assessments.id"]),
        sa.ForeignKeyConstraint(["proposed_assessment_id"], ["impact_assessments.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "policy_comparison_id",
            name="uq_policy_comparison_impact_deltas_comparison",
        ),
    )
    for column in (
        "policy_comparison_id",
        "organization_id",
        "baseline_assessment_id",
        "proposed_assessment_id",
        "impact_delta_fingerprint",
    ):
        op.create_index(
            f"ix_policy_comparison_impact_deltas_{column}",
            "policy_comparison_impact_deltas",
            [column],
        )

    op.create_table(
        "policy_comparison_impact_delta_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("impact_delta_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("item_kind", sa.String(length=30), nullable=False),
        sa.Column("change_type", sa.String(length=40), nullable=False),
        sa.Column("stable_identity", sa.String(length=700), nullable=False),
        sa.Column("delta_reason_code", sa.String(length=120), nullable=False),
        sa.Column("baseline_record_id", sa.Uuid(), nullable=True),
        sa.Column("proposed_record_id", sa.Uuid(), nullable=True),
        sa.Column(
            "baseline_snapshot",
            postgresql.JSONB(astext_type=sa.Text(), none_as_null=True),
            nullable=True,
        ),
        sa.Column(
            "proposed_snapshot",
            postgresql.JSONB(astext_type=sa.Text(), none_as_null=True),
            nullable=True,
        ),
        sa.CheckConstraint(
            "item_kind IN ('worker', 'finding', 'enterprise_impact')",
            name="ck_policy_comparison_impact_delta_items_kind",
        ),
        sa.CheckConstraint(
            "(item_kind = 'worker' AND change_type IN "
            "('became_affected', 'no_longer_affected', 'remained_affected')) "
            "OR (item_kind = 'finding' AND change_type IN ('introduced', 'disappeared')) "
            "OR (item_kind = 'enterprise_impact' AND change_type IN ('introduced', 'removed'))",
            name="ck_policy_comparison_impact_delta_items_change_type",
        ),
        sa.CheckConstraint(
            "sequence > 0",
            name="ck_policy_comparison_impact_delta_items_sequence",
        ),
        sa.CheckConstraint(
            "(baseline_record_id IS NULL) = (baseline_snapshot IS NULL) "
            "AND (proposed_record_id IS NULL) = (proposed_snapshot IS NULL)",
            name="ck_policy_comparison_impact_delta_items_snapshots",
        ),
        sa.CheckConstraint(
            "(change_type = 'introduced' AND baseline_record_id IS NULL "
            "AND proposed_record_id IS NOT NULL) "
            "OR (change_type IN ('disappeared', 'removed') "
            "AND baseline_record_id IS NOT NULL AND proposed_record_id IS NULL) "
            "OR (change_type = 'became_affected' AND proposed_record_id IS NOT NULL) "
            "OR (change_type = 'no_longer_affected' AND baseline_record_id IS NOT NULL) "
            "OR (change_type = 'remained_affected' AND baseline_record_id IS NOT NULL "
            "AND proposed_record_id IS NOT NULL)",
            name="ck_policy_comparison_impact_delta_items_sides",
        ),
        sa.ForeignKeyConstraint(
            ["impact_delta_id"],
            ["policy_comparison_impact_deltas.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "impact_delta_id",
            "sequence",
            name="uq_policy_comparison_impact_delta_items_sequence",
        ),
        sa.UniqueConstraint(
            "impact_delta_id",
            "stable_identity",
            name="uq_policy_comparison_impact_delta_items_identity",
        ),
    )
    op.create_index(
        "ix_policy_comparison_impact_delta_items_impact_delta_id",
        "policy_comparison_impact_delta_items",
        ["impact_delta_id"],
    )

    op.execute(
        """
        CREATE FUNCTION validate_policy_comparison_impact_delta_insert()
        RETURNS trigger AS $$
        DECLARE
            comparison_record policy_comparisons%ROWTYPE;
            baseline_record impact_assessments%ROWTYPE;
            proposed_record impact_assessments%ROWTYPE;
            baseline_attempt uuid;
            proposed_attempt uuid;
        BEGIN
            SELECT * INTO comparison_record
            FROM policy_comparisons
            WHERE id = NEW.policy_comparison_id;
            SELECT * INTO baseline_record
            FROM impact_assessments
            WHERE id = NEW.baseline_assessment_id;
            SELECT * INTO proposed_record
            FROM impact_assessments
            WHERE id = NEW.proposed_assessment_id;
            SELECT latest_extraction_attempt_id INTO baseline_attempt
            FROM policy_analysis_runs
            WHERE id = baseline_record.policy_analysis_run_id AND status = 'completed';
            SELECT latest_extraction_attempt_id INTO proposed_attempt
            FROM policy_analysis_runs
            WHERE id = proposed_record.policy_analysis_run_id AND status = 'completed';

            IF comparison_record.id IS NULL
               OR comparison_record.organization_id <> NEW.organization_id
               OR baseline_record.status IS DISTINCT FROM 'completed'
               OR proposed_record.status IS DISTINCT FROM 'completed'
               OR baseline_record.policy_change_id <> comparison_record.baseline_policy_change_id
               OR proposed_record.policy_change_id <> comparison_record.proposed_policy_change_id
               OR baseline_attempt IS DISTINCT FROM comparison_record.baseline_extraction_attempt_id
               OR proposed_attempt IS DISTINCT FROM
                  comparison_record.proposed_extraction_attempt_id THEN
                RAISE EXCEPTION 'impact delta assessment lineage is inconsistent';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER policy_comparison_impact_deltas_validate_insert
        BEFORE INSERT ON policy_comparison_impact_deltas
        FOR EACH ROW EXECUTE FUNCTION validate_policy_comparison_impact_delta_insert()
        """
    )
    op.execute(
        """
        CREATE FUNCTION validate_policy_comparison_impact_delta_item_insert()
        RETURNS trigger AS $$
        DECLARE
            baseline_assessment uuid;
            proposed_assessment uuid;
            baseline_owner uuid;
            proposed_owner uuid;
        BEGIN
            SELECT baseline_assessment_id, proposed_assessment_id
            INTO baseline_assessment, proposed_assessment
            FROM policy_comparison_impact_deltas
            WHERE id = NEW.impact_delta_id;

            IF NEW.item_kind = 'worker' THEN
                SELECT assessment_id INTO baseline_owner FROM assessment_worker_results
                WHERE id = NEW.baseline_record_id;
                SELECT assessment_id INTO proposed_owner FROM assessment_worker_results
                WHERE id = NEW.proposed_record_id;
            ELSIF NEW.item_kind = 'finding' THEN
                SELECT assessment_id INTO baseline_owner FROM findings
                WHERE id = NEW.baseline_record_id;
                SELECT assessment_id INTO proposed_owner FROM findings
                WHERE id = NEW.proposed_record_id;
            ELSE
                SELECT assessment_id INTO baseline_owner FROM assessment_enterprise_impacts
                WHERE id = NEW.baseline_record_id;
                SELECT assessment_id INTO proposed_owner FROM assessment_enterprise_impacts
                WHERE id = NEW.proposed_record_id;
            END IF;

            IF (NEW.baseline_record_id IS NOT NULL
                AND baseline_owner IS DISTINCT FROM baseline_assessment)
               OR (NEW.proposed_record_id IS NOT NULL
                AND proposed_owner IS DISTINCT FROM proposed_assessment) THEN
                RAISE EXCEPTION 'impact delta item lineage is inconsistent';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER policy_comparison_impact_delta_items_validate_insert
        BEFORE INSERT ON policy_comparison_impact_delta_items
        FOR EACH ROW EXECUTE FUNCTION validate_policy_comparison_impact_delta_item_insert()
        """
    )
    op.execute(
        """
        CREATE FUNCTION reject_policy_comparison_impact_delta_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'policy comparison impact deltas are immutable';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER policy_comparison_impact_deltas_immutable
        BEFORE UPDATE OR DELETE ON policy_comparison_impact_deltas
        FOR EACH ROW EXECUTE FUNCTION reject_policy_comparison_impact_delta_mutation()
        """
    )
    op.execute(
        """
        CREATE TRIGGER policy_comparison_impact_delta_items_immutable
        BEFORE UPDATE OR DELETE ON policy_comparison_impact_delta_items
        FOR EACH ROW EXECUTE FUNCTION reject_policy_comparison_impact_delta_mutation()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER policy_comparison_impact_delta_items_immutable "
        "ON policy_comparison_impact_delta_items"
    )
    op.execute(
        "DROP TRIGGER policy_comparison_impact_deltas_immutable ON policy_comparison_impact_deltas"
    )
    op.execute("DROP FUNCTION reject_policy_comparison_impact_delta_mutation()")
    op.execute(
        "DROP TRIGGER policy_comparison_impact_delta_items_validate_insert "
        "ON policy_comparison_impact_delta_items"
    )
    op.execute("DROP FUNCTION validate_policy_comparison_impact_delta_item_insert()")
    op.execute(
        "DROP TRIGGER policy_comparison_impact_deltas_validate_insert "
        "ON policy_comparison_impact_deltas"
    )
    op.execute("DROP FUNCTION validate_policy_comparison_impact_delta_insert()")
    op.drop_table("policy_comparison_impact_delta_items")
    op.drop_table("policy_comparison_impact_deltas")
