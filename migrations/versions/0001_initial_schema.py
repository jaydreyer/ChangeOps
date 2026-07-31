"""Create the Milestone 0 schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("industry", sa.String(length=100), nullable=True),
        sa.Column("headquarters", sa.String(length=200), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "workers",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column("organization_id", sa.String(length=100), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("worker_type", sa.String(length=30), nullable=False),
        sa.Column("department", sa.String(length=100), nullable=False),
        sa.Column("manager_name", sa.String(length=200), nullable=False),
        sa.Column("assigned_work_country", sa.String(length=2), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workers_organization_id", "workers", ["organization_id"])
    op.create_table(
        "policy_changes",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column("organization_id", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("owner", sa.String(length=200), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("policy_text", sa.Text(), nullable=False),
        sa.Column(
            "structured_rules",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_policy_changes_organization_id",
        "policy_changes",
        ["organization_id"],
    )
    op.create_table(
        "trips",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column("worker_id", sa.String(length=100), nullable=False),
        sa.Column("origin_country", sa.String(length=2), nullable=False),
        sa.Column("destination_country", sa.String(length=2), nullable=False),
        sa.Column("departure_date", sa.Date(), nullable=False),
        sa.Column("booking_date", sa.Date(), nullable=True),
        sa.Column("booking_status", sa.String(length=20), nullable=False),
        sa.CheckConstraint(
            "booking_status IN ('planned', 'booked')",
            name="ck_trips_booking_status",
        ),
        sa.ForeignKeyConstraint(["worker_id"], ["workers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trips_worker_id", "trips", ["worker_id"])
    op.create_table(
        "training_records",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column("worker_id", sa.String(length=100), nullable=False),
        sa.Column("course_identifier", sa.String(length=100), nullable=False),
        sa.Column("completion_status", sa.String(length=30), nullable=False),
        sa.Column("completion_date", sa.Date(), nullable=True),
        sa.CheckConstraint(
            "completion_status IN ('completed', 'not_completed')",
            name="ck_training_records_completion_status",
        ),
        sa.ForeignKeyConstraint(["worker_id"], ["workers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "worker_id",
            "course_identifier",
            name="uq_training_records_worker_course",
        ),
    )
    op.create_index("ix_training_records_worker_id", "training_records", ["worker_id"])
    op.create_table(
        "policy_change_questions",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column("policy_change_id", sa.String(length=100), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["policy_change_id"], ["policy_changes.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "policy_change_id",
            "sequence",
            name="uq_policy_change_questions_policy_sequence",
        ),
    )
    op.create_index(
        "ix_policy_change_questions_policy_change_id",
        "policy_change_questions",
        ["policy_change_id"],
    )
    op.create_table(
        "impact_assessments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("policy_change_id", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("analyzer_version", sa.String(length=100), nullable=False),
        sa.Column("input_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status = 'completed'",
            name="ck_impact_assessments_status",
        ),
        sa.ForeignKeyConstraint(["policy_change_id"], ["policy_changes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_impact_assessments_policy_change_id",
        "impact_assessments",
        ["policy_change_id"],
    )
    op.create_table(
        "assessment_worker_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("assessment_id", sa.Uuid(), nullable=False),
        sa.Column("worker_id", sa.String(length=100), nullable=False),
        sa.Column("trip_id", sa.String(length=100), nullable=False),
        sa.Column("classification", sa.String(length=20), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column(
            "reason_codes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.CheckConstraint(
            "classification IN ('affected', 'unaffected')",
            name="ck_assessment_worker_results_classification",
        ),
        sa.ForeignKeyConstraint(["assessment_id"], ["impact_assessments.id"]),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"]),
        sa.ForeignKeyConstraint(["worker_id"], ["workers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "assessment_id",
            "trip_id",
            name="uq_assessment_worker_results_assessment_trip",
        ),
    )
    op.create_index(
        "ix_assessment_worker_results_assessment_id",
        "assessment_worker_results",
        ["assessment_id"],
    )
    op.create_index(
        "ix_assessment_worker_results_trip_id",
        "assessment_worker_results",
        ["trip_id"],
    )
    op.create_index(
        "ix_assessment_worker_results_worker_id",
        "assessment_worker_results",
        ["worker_id"],
    )
    op.create_table(
        "evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("assessment_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_key", sa.String(length=200), nullable=False),
        sa.Column("evidence_type", sa.String(length=50), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("source_id", sa.String(length=150), nullable=False),
        sa.Column("label", sa.String(length=300), nullable=False),
        sa.Column(
            "snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["assessment_id"], ["impact_assessments.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "assessment_id",
            "evidence_key",
            name="uq_evidence_assessment_key",
        ),
    )
    op.create_index("ix_evidence_assessment_id", "evidence", ["assessment_id"])
    op.create_table(
        "assessment_unresolved_questions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("assessment_id", sa.Uuid(), nullable=False),
        sa.Column("source_question_id", sa.String(length=100), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["assessment_id"], ["impact_assessments.id"]),
        sa.ForeignKeyConstraint(
            ["source_question_id"],
            ["policy_change_questions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "assessment_id",
            "sequence",
            name="uq_assessment_questions_assessment_sequence",
        ),
    )
    op.create_index(
        "ix_assessment_unresolved_questions_assessment_id",
        "assessment_unresolved_questions",
        ["assessment_id"],
    )
    op.create_table(
        "findings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("assessment_id", sa.Uuid(), nullable=False),
        sa.Column("worker_result_id", sa.Uuid(), nullable=False),
        sa.Column("finding_type", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.String(length=30), nullable=False),
        sa.Column("rule_code", sa.String(length=100), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["assessment_id"], ["impact_assessments.id"]),
        sa.ForeignKeyConstraint(
            ["worker_result_id"],
            ["assessment_worker_results.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_findings_assessment_id", "findings", ["assessment_id"])
    op.create_index("ix_findings_worker_result_id", "findings", ["worker_result_id"])
    op.create_table(
        "finding_evidence",
        sa.Column("finding_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence.id"]),
        sa.ForeignKeyConstraint(["finding_id"], ["findings.id"]),
        sa.PrimaryKeyConstraint("finding_id", "evidence_id"),
    )
    op.create_table(
        "proposed_actions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("assessment_id", sa.Uuid(), nullable=False),
        sa.Column("finding_id", sa.Uuid(), nullable=False),
        sa.Column("worker_id", sa.String(length=100), nullable=False),
        sa.Column("action_type", sa.String(length=100), nullable=False),
        sa.Column("target_type", sa.String(length=50), nullable=False),
        sa.Column("target_identifier", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("execution_status", sa.String(length=30), nullable=False),
        sa.CheckConstraint(
            "execution_status = 'not_executed'",
            name="ck_proposed_actions_execution_status",
        ),
        sa.ForeignKeyConstraint(["assessment_id"], ["impact_assessments.id"]),
        sa.ForeignKeyConstraint(["finding_id"], ["findings.id"]),
        sa.ForeignKeyConstraint(["worker_id"], ["workers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_proposed_actions_assessment_id",
        "proposed_actions",
        ["assessment_id"],
    )
    op.create_index(
        "ix_proposed_actions_finding_id",
        "proposed_actions",
        ["finding_id"],
    )
    op.create_index(
        "ix_proposed_actions_worker_id",
        "proposed_actions",
        ["worker_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_proposed_actions_worker_id", table_name="proposed_actions")
    op.drop_index("ix_proposed_actions_finding_id", table_name="proposed_actions")
    op.drop_index("ix_proposed_actions_assessment_id", table_name="proposed_actions")
    op.drop_table("proposed_actions")
    op.drop_table("finding_evidence")
    op.drop_index("ix_findings_worker_result_id", table_name="findings")
    op.drop_index("ix_findings_assessment_id", table_name="findings")
    op.drop_table("findings")
    op.drop_index(
        "ix_assessment_unresolved_questions_assessment_id",
        table_name="assessment_unresolved_questions",
    )
    op.drop_table("assessment_unresolved_questions")
    op.drop_index("ix_evidence_assessment_id", table_name="evidence")
    op.drop_table("evidence")
    op.drop_index(
        "ix_assessment_worker_results_worker_id",
        table_name="assessment_worker_results",
    )
    op.drop_index(
        "ix_assessment_worker_results_trip_id",
        table_name="assessment_worker_results",
    )
    op.drop_index(
        "ix_assessment_worker_results_assessment_id",
        table_name="assessment_worker_results",
    )
    op.drop_table("assessment_worker_results")
    op.drop_index(
        "ix_impact_assessments_policy_change_id",
        table_name="impact_assessments",
    )
    op.drop_table("impact_assessments")
    op.drop_index(
        "ix_policy_change_questions_policy_change_id",
        table_name="policy_change_questions",
    )
    op.drop_table("policy_change_questions")
    op.drop_index("ix_training_records_worker_id", table_name="training_records")
    op.drop_table("training_records")
    op.drop_index("ix_trips_worker_id", table_name="trips")
    op.drop_table("trips")
    op.drop_index("ix_policy_changes_organization_id", table_name="policy_changes")
    op.drop_table("policy_changes")
    op.drop_index("ix_workers_organization_id", table_name="workers")
    op.drop_table("workers")
    op.drop_table("organizations")
