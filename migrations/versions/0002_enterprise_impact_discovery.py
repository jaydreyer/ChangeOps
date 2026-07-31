"""Add deterministic enterprise impact discovery.

Revision ID: 0002_enterprise_impact
Revises: 0001_initial
Create Date: 2026-07-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_enterprise_impact"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "training_courses",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column("organization_id", sa.String(length=100), nullable=False),
        sa.Column("course_code", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("course_code"),
    )
    op.create_index(
        "ix_training_courses_organization_id",
        "training_courses",
        ["organization_id"],
    )
    op.execute(
        """
        INSERT INTO training_courses (id, organization_id, course_code, name, active)
        SELECT DISTINCT
            tr.course_identifier,
            w.organization_id,
            tr.course_identifier,
            CASE
                WHEN tr.course_identifier = 'international-travel-security'
                THEN 'International Travel Security'
                ELSE tr.course_identifier
            END,
            true
        FROM training_records tr
        JOIN workers w ON w.id = tr.worker_id
        ON CONFLICT (id) DO NOTHING
        """
    )
    op.create_foreign_key(
        "fk_training_records_course_identifier",
        "training_records",
        "training_courses",
        ["course_identifier"],
        ["id"],
    )
    op.create_index(
        "ix_training_records_course_identifier",
        "training_records",
        ["course_identifier"],
    )

    op.create_table(
        "teams",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column("organization_id", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("manager_worker_id", sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(["manager_worker_id"], ["workers.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_teams_manager_worker_id", "teams", ["manager_worker_id"])
    op.create_index("ix_teams_organization_id", "teams", ["organization_id"])
    op.add_column("workers", sa.Column("manager_worker_id", sa.String(length=100)))
    op.create_foreign_key(
        "fk_workers_manager_worker_id",
        "workers",
        "workers",
        ["manager_worker_id"],
        ["id"],
    )
    op.create_index("ix_workers_manager_worker_id", "workers", ["manager_worker_id"])
    op.create_table(
        "worker_team_memberships",
        sa.Column("id", sa.String(length=150), nullable=False),
        sa.Column("worker_id", sa.String(length=100), nullable=False),
        sa.Column("team_id", sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
        sa.ForeignKeyConstraint(["worker_id"], ["workers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "worker_id",
            name="uq_worker_team_memberships_worker",
        ),
    )
    op.create_index(
        "ix_worker_team_memberships_team_id",
        "worker_team_memberships",
        ["team_id"],
    )
    op.create_index(
        "ix_worker_team_memberships_worker_id",
        "worker_team_memberships",
        ["worker_id"],
    )

    op.create_table(
        "enterprise_systems",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column("organization_id", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("system_type", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_enterprise_systems_organization_id",
        "enterprise_systems",
        ["organization_id"],
    )
    op.create_table(
        "enterprise_documents",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column("organization_id", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("document_type", sa.String(length=30), nullable=False),
        sa.Column("source_system", sa.String(length=100), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.CheckConstraint(
            "document_type IN ('policy', 'procedure', 'guide', 'knowledge_article')",
            name="ck_enterprise_documents_type",
        ),
        sa.CheckConstraint(
            "status IN ('published', 'draft', 'archived')",
            name="ck_enterprise_documents_status",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_enterprise_documents_organization_id",
        "enterprise_documents",
        ["organization_id"],
    )
    op.create_table(
        "customer_commitments",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column("organization_id", sa.String(length=100), nullable=False),
        sa.Column("customer_name", sa.String(length=200), nullable=False),
        sa.Column("commitment_type", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.CheckConstraint(
            "end_date >= start_date",
            name="ck_customer_commitments_dates",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'completed', 'cancelled')",
            name="ck_customer_commitments_status",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_customer_commitments_organization_id",
        "customer_commitments",
        ["organization_id"],
    )

    op.create_table(
        "policy_system_dependencies",
        sa.Column("id", sa.String(length=150), nullable=False),
        sa.Column("policy_change_id", sa.String(length=100), nullable=False),
        sa.Column("rule_code", sa.String(length=100), nullable=False),
        sa.Column("system_id", sa.String(length=100), nullable=False),
        sa.Column("relationship_type", sa.String(length=100), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["policy_change_id"], ["policy_changes.id"]),
        sa.ForeignKeyConstraint(["system_id"], ["enterprise_systems.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "policy_change_id",
            "rule_code",
            "system_id",
            name="uq_policy_system_dependencies_target",
        ),
    )
    op.create_index(
        "ix_policy_system_dependencies_policy_change_id",
        "policy_system_dependencies",
        ["policy_change_id"],
    )
    op.create_index(
        "ix_policy_system_dependencies_system_id",
        "policy_system_dependencies",
        ["system_id"],
    )
    op.create_table(
        "policy_document_dependencies",
        sa.Column("id", sa.String(length=150), nullable=False),
        sa.Column("policy_change_id", sa.String(length=100), nullable=False),
        sa.Column("rule_code", sa.String(length=100), nullable=False),
        sa.Column("document_id", sa.String(length=100), nullable=False),
        sa.Column("relationship_type", sa.String(length=100), nullable=False),
        sa.Column("impact_classification", sa.String(length=30), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "impact_classification IN ('review_required', 'update_required')",
            name="ck_policy_document_dependencies_classification",
        ),
        sa.ForeignKeyConstraint(["document_id"], ["enterprise_documents.id"]),
        sa.ForeignKeyConstraint(["policy_change_id"], ["policy_changes.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "policy_change_id",
            "rule_code",
            "document_id",
            name="uq_policy_document_dependencies_target",
        ),
    )
    op.create_index(
        "ix_policy_document_dependencies_document_id",
        "policy_document_dependencies",
        ["document_id"],
    )
    op.create_index(
        "ix_policy_document_dependencies_policy_change_id",
        "policy_document_dependencies",
        ["policy_change_id"],
    )
    op.create_table(
        "policy_training_dependencies",
        sa.Column("id", sa.String(length=150), nullable=False),
        sa.Column("policy_change_id", sa.String(length=100), nullable=False),
        sa.Column("rule_code", sa.String(length=100), nullable=False),
        sa.Column("course_id", sa.String(length=100), nullable=False),
        sa.Column("relationship_type", sa.String(length=100), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["training_courses.id"]),
        sa.ForeignKeyConstraint(["policy_change_id"], ["policy_changes.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "policy_change_id",
            "rule_code",
            "course_id",
            name="uq_policy_training_dependencies_target",
        ),
    )
    op.create_index(
        "ix_policy_training_dependencies_course_id",
        "policy_training_dependencies",
        ["course_id"],
    )
    op.create_index(
        "ix_policy_training_dependencies_policy_change_id",
        "policy_training_dependencies",
        ["policy_change_id"],
    )
    op.create_table(
        "commitment_assignments",
        sa.Column("id", sa.String(length=150), nullable=False),
        sa.Column("commitment_id", sa.String(length=100), nullable=False),
        sa.Column("worker_id", sa.String(length=100), nullable=False),
        sa.Column("assignment_role", sa.String(length=100), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["commitment_id"], ["customer_commitments.id"]),
        sa.ForeignKeyConstraint(["worker_id"], ["workers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "commitment_id",
            "worker_id",
            "assignment_role",
            name="uq_commitment_assignments_worker_role",
        ),
    )
    op.create_index(
        "ix_commitment_assignments_commitment_id",
        "commitment_assignments",
        ["commitment_id"],
    )
    op.create_index(
        "ix_commitment_assignments_worker_id",
        "commitment_assignments",
        ["worker_id"],
    )

    op.create_table(
        "assessment_enterprise_impacts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("assessment_id", sa.Uuid(), nullable=False),
        sa.Column("domain", sa.String(length=30), nullable=False),
        sa.Column("object_type", sa.String(length=50), nullable=False),
        sa.Column("source_key", sa.String(length=200), nullable=False),
        sa.Column("display_name", sa.String(length=300), nullable=False),
        sa.Column("classification", sa.String(length=40), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("reason_code", sa.String(length=120), nullable=False),
        sa.Column("sort_key", sa.String(length=400), nullable=False),
        sa.CheckConstraint(
            "domain IN ('people', 'teams', 'systems', 'documents', 'training', "
            "'customer_commitments')",
            name="ck_assessment_enterprise_impacts_domain",
        ),
        sa.CheckConstraint(
            "classification IN ('directly_affected', 'operationally_affected', "
            "'review_required', 'update_required', 'notification_required')",
            name="ck_assessment_enterprise_impacts_classification",
        ),
        sa.ForeignKeyConstraint(["assessment_id"], ["impact_assessments.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "assessment_id",
            "domain",
            "source_key",
            "reason_code",
            name="uq_assessment_enterprise_impacts_semantic",
        ),
        sa.UniqueConstraint(
            "assessment_id",
            "sort_key",
            name="uq_assessment_enterprise_impacts_sort_key",
        ),
    )
    op.create_index(
        "ix_assessment_enterprise_impacts_assessment_id",
        "assessment_enterprise_impacts",
        ["assessment_id"],
    )
    op.create_table(
        "assessment_impact_evidence",
        sa.Column("impact_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence.id"]),
        sa.ForeignKeyConstraint(["impact_id"], ["assessment_enterprise_impacts.id"]),
        sa.PrimaryKeyConstraint("impact_id", "evidence_id"),
    )
    op.create_table(
        "assessment_impact_path_elements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("impact_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("object_type", sa.String(length=50), nullable=False),
        sa.Column("stable_key", sa.String(length=200), nullable=False),
        sa.Column("display_label", sa.String(length=300), nullable=False),
        sa.Column("relationship_to_next", sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(["impact_id"], ["assessment_enterprise_impacts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "impact_id",
            "sequence",
            name="uq_assessment_impact_path_elements_sequence",
        ),
    )
    op.create_index(
        "ix_assessment_impact_path_elements_impact_id",
        "assessment_impact_path_elements",
        ["impact_id"],
    )

    op.add_column(
        "proposed_actions",
        sa.Column("enterprise_impact_id", sa.Uuid(), nullable=True),
    )
    op.alter_column("proposed_actions", "finding_id", nullable=True)
    op.alter_column("proposed_actions", "worker_id", nullable=True)
    op.create_foreign_key(
        "fk_proposed_actions_enterprise_impact_id",
        "proposed_actions",
        "assessment_enterprise_impacts",
        ["enterprise_impact_id"],
        ["id"],
    )
    op.create_index(
        "ix_proposed_actions_enterprise_impact_id",
        "proposed_actions",
        ["enterprise_impact_id"],
    )
    op.create_check_constraint(
        "ck_proposed_actions_has_parent",
        "proposed_actions",
        "finding_id IS NOT NULL OR enterprise_impact_id IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_proposed_actions_has_parent",
        "proposed_actions",
        type_="check",
    )
    op.drop_index(
        "ix_proposed_actions_enterprise_impact_id",
        table_name="proposed_actions",
    )
    op.drop_constraint(
        "fk_proposed_actions_enterprise_impact_id",
        "proposed_actions",
        type_="foreignkey",
    )
    op.drop_column("proposed_actions", "enterprise_impact_id")
    op.alter_column("proposed_actions", "worker_id", nullable=False)
    op.alter_column("proposed_actions", "finding_id", nullable=False)

    op.drop_index(
        "ix_assessment_impact_path_elements_impact_id",
        table_name="assessment_impact_path_elements",
    )
    op.drop_table("assessment_impact_path_elements")
    op.drop_table("assessment_impact_evidence")
    op.drop_index(
        "ix_assessment_enterprise_impacts_assessment_id",
        table_name="assessment_enterprise_impacts",
    )
    op.drop_table("assessment_enterprise_impacts")
    op.drop_index(
        "ix_commitment_assignments_worker_id",
        table_name="commitment_assignments",
    )
    op.drop_index(
        "ix_commitment_assignments_commitment_id",
        table_name="commitment_assignments",
    )
    op.drop_table("commitment_assignments")
    op.drop_index(
        "ix_policy_training_dependencies_policy_change_id",
        table_name="policy_training_dependencies",
    )
    op.drop_index(
        "ix_policy_training_dependencies_course_id",
        table_name="policy_training_dependencies",
    )
    op.drop_table("policy_training_dependencies")
    op.drop_index(
        "ix_policy_document_dependencies_policy_change_id",
        table_name="policy_document_dependencies",
    )
    op.drop_index(
        "ix_policy_document_dependencies_document_id",
        table_name="policy_document_dependencies",
    )
    op.drop_table("policy_document_dependencies")
    op.drop_index(
        "ix_policy_system_dependencies_system_id",
        table_name="policy_system_dependencies",
    )
    op.drop_index(
        "ix_policy_system_dependencies_policy_change_id",
        table_name="policy_system_dependencies",
    )
    op.drop_table("policy_system_dependencies")
    op.drop_index(
        "ix_customer_commitments_organization_id",
        table_name="customer_commitments",
    )
    op.drop_table("customer_commitments")
    op.drop_index(
        "ix_enterprise_documents_organization_id",
        table_name="enterprise_documents",
    )
    op.drop_table("enterprise_documents")
    op.drop_index(
        "ix_enterprise_systems_organization_id",
        table_name="enterprise_systems",
    )
    op.drop_table("enterprise_systems")

    op.drop_index(
        "ix_worker_team_memberships_worker_id",
        table_name="worker_team_memberships",
    )
    op.drop_index(
        "ix_worker_team_memberships_team_id",
        table_name="worker_team_memberships",
    )
    op.drop_table("worker_team_memberships")
    op.drop_index("ix_workers_manager_worker_id", table_name="workers")
    op.drop_constraint("fk_workers_manager_worker_id", "workers", type_="foreignkey")
    op.drop_column("workers", "manager_worker_id")
    op.drop_index("ix_teams_organization_id", table_name="teams")
    op.drop_index("ix_teams_manager_worker_id", table_name="teams")
    op.drop_table("teams")

    op.drop_index(
        "ix_training_records_course_identifier",
        table_name="training_records",
    )
    op.drop_constraint(
        "fk_training_records_course_identifier",
        "training_records",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_training_courses_organization_id",
        table_name="training_courses",
    )
    op.drop_table("training_courses")
