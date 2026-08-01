"""Add immutable action reviews and append-only decisions.

Revision ID: 0006_action_reviews
Revises: 0005_policy_interpretation
Create Date: 2026-08-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_action_reviews"
down_revision: str | None = "0005_policy_interpretation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_proposed_actions_id_assessment",
        "proposed_actions",
        ["id", "assessment_id"],
    )
    op.execute(
        """
        CREATE FUNCTION reject_proposed_action_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'proposed actions are immutable assessment artifacts';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER proposed_actions_immutable
        BEFORE UPDATE OR DELETE ON proposed_actions
        FOR EACH ROW EXECUTE FUNCTION reject_proposed_action_mutation()
        """
    )
    op.create_table(
        "action_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("assessment_id", sa.Uuid(), nullable=False),
        sa.Column("proposed_action_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column(
            "original_action_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "review_context_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'deferred', 'revision_requested')",
            name="ck_action_reviews_status",
        ),
        sa.CheckConstraint(
            "(status = 'pending' AND completed_at IS NULL) OR "
            "(status <> 'pending' AND completed_at IS NOT NULL)",
            name="ck_action_reviews_completion",
        ),
        sa.ForeignKeyConstraint(["assessment_id"], ["impact_assessments.id"]),
        sa.ForeignKeyConstraint(["proposed_action_id"], ["proposed_actions.id"]),
        sa.ForeignKeyConstraint(
            ["proposed_action_id", "assessment_id"],
            ["proposed_actions.id", "proposed_actions.assessment_id"],
            name="fk_action_reviews_action_assessment",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "proposed_action_id",
            name="uq_action_reviews_proposed_action",
        ),
    )
    op.create_index("ix_action_reviews_assessment_id", "action_reviews", ["assessment_id"])
    op.create_index(
        "ix_action_reviews_proposed_action_id",
        "action_reviews",
        ["proposed_action_id"],
    )
    op.create_table(
        "action_review_decisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("action_review_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.String(length=30), nullable=False),
        sa.Column("reviewer_identity", sa.String(length=200), nullable=False),
        sa.Column("reviewer_role", sa.String(length=30), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column(
            "edited_action_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "decision IN ('approved', 'rejected', 'deferred', 'revision_requested')",
            name="ck_action_review_decisions_decision",
        ),
        sa.CheckConstraint(
            "(decision = 'approved') OR edited_action_snapshot IS NULL",
            name="ck_action_review_decisions_approved_edit",
        ),
        sa.CheckConstraint(
            "length(btrim(reviewer_identity)) > 0",
            name="ck_action_review_decisions_identity",
        ),
        sa.CheckConstraint(
            "reviewer_role IN ('reviewer', 'admin')",
            name="ck_action_review_decisions_role",
        ),
        sa.CheckConstraint(
            "length(btrim(rationale)) > 0",
            name="ck_action_review_decisions_rationale",
        ),
        sa.ForeignKeyConstraint(["action_review_id"], ["action_reviews.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "action_review_id",
            name="uq_action_review_decisions_review",
        ),
    )
    op.create_index(
        "ix_action_review_decisions_action_review_id",
        "action_review_decisions",
        ["action_review_id"],
    )

    op.execute(
        """
        CREATE FUNCTION enforce_action_review_mutation()
        RETURNS trigger AS $$
        DECLARE
            matching_decision text;
        BEGIN
            IF TG_OP = 'DELETE' THEN
                IF OLD.status <> 'pending' THEN
                    RAISE EXCEPTION 'terminal action reviews are immutable';
                END IF;
                RETURN OLD;
            END IF;

            IF OLD.assessment_id IS DISTINCT FROM NEW.assessment_id
               OR OLD.proposed_action_id IS DISTINCT FROM NEW.proposed_action_id
               OR OLD.original_action_snapshot IS DISTINCT FROM NEW.original_action_snapshot
               OR OLD.review_context_snapshot IS DISTINCT FROM NEW.review_context_snapshot
               OR OLD.created_at IS DISTINCT FROM NEW.created_at THEN
                RAISE EXCEPTION 'action review snapshots and identity are immutable';
            END IF;
            IF OLD.status <> 'pending' THEN
                RAISE EXCEPTION 'terminal action reviews are immutable';
            END IF;
            IF NEW.status = 'pending' THEN
                IF NEW.completed_at IS DISTINCT FROM OLD.completed_at THEN
                    RAISE EXCEPTION 'pending action review cannot be completed';
                END IF;
                RETURN NEW;
            END IF;

            SELECT decision INTO matching_decision
            FROM action_review_decisions
            WHERE action_review_id = OLD.id;
            IF matching_decision IS NULL OR matching_decision <> NEW.status THEN
                RAISE EXCEPTION 'action review transition must match its decision';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER action_reviews_immutable
        BEFORE UPDATE OR DELETE ON action_reviews
        FOR EACH ROW EXECUTE FUNCTION enforce_action_review_mutation()
        """
    )
    op.execute(
        """
        CREATE FUNCTION enforce_action_review_decision_insert()
        RETURNS trigger AS $$
        DECLARE
            review_status text;
            invalid_edit_key text;
        BEGIN
            SELECT status INTO review_status
            FROM action_reviews
            WHERE id = NEW.action_review_id
            FOR UPDATE;
            IF review_status IS NULL THEN
                RAISE EXCEPTION 'action review does not exist';
            END IF;
            IF review_status <> 'pending' THEN
                RAISE EXCEPTION 'action review is already decided';
            END IF;
            IF NEW.edited_action_snapshot IS NOT NULL THEN
                IF NEW.decision <> 'approved'
                   OR jsonb_typeof(NEW.edited_action_snapshot) <> 'object' THEN
                    RAISE EXCEPTION 'edited action is valid only for approval';
                END IF;
                IF NEW.edited_action_snapshot = '{}'::jsonb THEN
                    RAISE EXCEPTION 'edited action must contain a change';
                END IF;
                SELECT key INTO invalid_edit_key
                FROM jsonb_object_keys(NEW.edited_action_snapshot) AS key
                WHERE key NOT IN ('description', 'due_date')
                LIMIT 1;
                IF invalid_edit_key IS NOT NULL THEN
                    RAISE EXCEPTION 'edited action contains an immutable field';
                END IF;
                IF NEW.edited_action_snapshot ? 'description'
                   AND (jsonb_typeof(NEW.edited_action_snapshot->'description') <> 'string'
                        OR length(btrim(NEW.edited_action_snapshot->>'description')) = 0) THEN
                    RAISE EXCEPTION 'edited description must be nonempty';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER action_review_decisions_validate_insert
        BEFORE INSERT ON action_review_decisions
        FOR EACH ROW EXECUTE FUNCTION enforce_action_review_decision_insert()
        """
    )
    op.execute(
        """
        CREATE FUNCTION reject_action_review_decision_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'action review decisions are append-only';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER action_review_decisions_append_only
        BEFORE UPDATE OR DELETE ON action_review_decisions
        FOR EACH ROW EXECUTE FUNCTION reject_action_review_decision_mutation()
        """
    )
    op.execute(
        """
        CREATE FUNCTION validate_action_review_lifecycle()
        RETURNS trigger AS $$
        DECLARE
            review_id uuid;
            review_status text;
            review_completed_at timestamptz;
            persisted_decision text;
        BEGIN
            IF TG_TABLE_NAME = 'action_reviews' THEN
                review_id := NEW.id;
            ELSE
                review_id := NEW.action_review_id;
            END IF;
            SELECT status, completed_at
            INTO review_status, review_completed_at
            FROM action_reviews
            WHERE id = review_id;
            SELECT decision INTO persisted_decision
            FROM action_review_decisions
            WHERE action_review_id = review_id;

            IF review_status = 'pending'
               AND (persisted_decision IS NOT NULL OR review_completed_at IS NOT NULL) THEN
                RAISE EXCEPTION 'pending action review cannot have a decision';
            END IF;
            IF review_status <> 'pending'
               AND (persisted_decision IS NULL
                    OR persisted_decision <> review_status
                    OR review_completed_at IS NULL) THEN
                RAISE EXCEPTION 'terminal action review must match its decision';
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER action_reviews_lifecycle_consistent
        AFTER INSERT OR UPDATE ON action_reviews
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION validate_action_review_lifecycle()
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER action_review_decisions_lifecycle_consistent
        AFTER INSERT ON action_review_decisions
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION validate_action_review_lifecycle()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER action_review_decisions_lifecycle_consistent ON action_review_decisions"
    )
    op.execute("DROP TRIGGER action_reviews_lifecycle_consistent ON action_reviews")
    op.execute("DROP FUNCTION validate_action_review_lifecycle()")
    op.execute("DROP TRIGGER action_review_decisions_append_only ON action_review_decisions")
    op.execute("DROP FUNCTION reject_action_review_decision_mutation()")
    op.execute("DROP TRIGGER action_review_decisions_validate_insert ON action_review_decisions")
    op.execute("DROP FUNCTION enforce_action_review_decision_insert()")
    op.execute("DROP TRIGGER action_reviews_immutable ON action_reviews")
    op.execute("DROP FUNCTION enforce_action_review_mutation()")
    op.drop_table("action_review_decisions")
    op.drop_table("action_reviews")
    op.execute("DROP TRIGGER proposed_actions_immutable ON proposed_actions")
    op.execute("DROP FUNCTION reject_proposed_action_mutation()")
    op.drop_constraint(
        "uq_proposed_actions_id_assessment",
        "proposed_actions",
        type_="unique",
    )
