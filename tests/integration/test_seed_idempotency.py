import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from changeops.db.models import (
    CommitmentAssignment,
    CustomerCommitment,
    EnterpriseDocument,
    EnterpriseSystem,
    ImpactAssessment,
    Organization,
    PolicyChange,
    PolicyChangeQuestion,
    PolicyDocumentDependency,
    PolicyExtractionAttempt,
    PolicySystemDependency,
    PolicyTrainingDependency,
    Team,
    TrainingCourse,
    TrainingRecord,
    Trip,
    Worker,
    WorkerTeamMembership,
)
from changeops.db.session import SessionLocal
from changeops.services.demo_assessment_seed_service import (
    DEMO_ASSESSMENT_ID,
    seed_demo_assessment,
)
from changeops.services.demo_reset_service import reset_demo_workflows
from changeops.services.seed_service import seed_database


def source_counts(session: Session) -> dict[str, int]:
    return {
        model.__tablename__: session.scalar(select(func.count()).select_from(model))
        for model in (
            Organization,
            PolicyChange,
            PolicyChangeQuestion,
            PolicyExtractionAttempt,
            Worker,
            Team,
            WorkerTeamMembership,
            Trip,
            EnterpriseSystem,
            EnterpriseDocument,
            TrainingCourse,
            TrainingRecord,
            PolicySystemDependency,
            PolicyDocumentDependency,
            PolicyTrainingDependency,
            CustomerCommitment,
            CommitmentAssignment,
        )
    }


def test_seed_is_repeatable_without_duplicates() -> None:
    with SessionLocal.begin() as session:
        before = source_counts(session)
        seed_database(session)
        seed_database(session)

    with SessionLocal() as session:
        after = source_counts(session)

    assert (
        before
        == after
        == {
            "organizations": 1,
            "policy_changes": 2,
            "policy_change_questions": 8,
            "policy_extraction_attempts": 0,
            "workers": 12,
            "teams": 4,
            "worker_team_memberships": 6,
            "trips": 6,
            "enterprise_systems": 3,
            "enterprise_documents": 4,
            "training_courses": 1,
            "training_records": 6,
            "policy_system_dependencies": 4,
            "policy_document_dependencies": 6,
            "policy_training_dependencies": 2,
            "customer_commitments": 2,
            "commitment_assignments": 2,
        }
    )
    with SessionLocal() as session:
        dependency_rows = [
            *session.scalars(select(PolicySystemDependency)),
            *session.scalars(select(PolicyDocumentDependency)),
            *session.scalars(select(PolicyTrainingDependency)),
        ]
        assert len(dependency_rows) == 12
        assert {row.provenance_category for row in dependency_rows} == {"seeded_demonstration"}
        assert {row.provenance_authority for row in dependency_rows} == {
            "ChangeOps demonstration seed"
        }
        assert {row.provenance_reference for row in dependency_rows} == {
            "changeops.seed.relationships.v1"
        }
        assert {row.provenance_recorded_at.isoformat() for row in dependency_rows} == {
            "2026-08-06T00:00:00+00:00"
        }


@pytest.mark.parametrize(
    ("model", "field_name", "invalid_value"),
    [
        (PolicySystemDependency, "provenance_category", "human_approved_ai"),
        (PolicySystemDependency, "provenance_authority", " "),
        (PolicySystemDependency, "provenance_reference", ""),
        (PolicySystemDependency, "provenance_recorded_at", None),
        (PolicyDocumentDependency, "provenance_category", "human_curated"),
        (PolicyDocumentDependency, "provenance_authority", ""),
        (PolicyDocumentDependency, "provenance_reference", " "),
        (PolicyDocumentDependency, "provenance_recorded_at", None),
        (PolicyTrainingDependency, "provenance_category", "imported_authoritative"),
        (PolicyTrainingDependency, "provenance_authority", " "),
        (PolicyTrainingDependency, "provenance_reference", ""),
        (PolicyTrainingDependency, "provenance_recorded_at", None),
    ],
)
def test_dependency_provenance_rejects_unsupported_or_incomplete_lineage(
    model,
    field_name: str,
    invalid_value,
) -> None:
    with pytest.raises(IntegrityError), SessionLocal.begin() as session:
        dependency = session.scalars(select(model).order_by(model.id)).first()
        assert dependency is not None
        setattr(dependency, field_name, invalid_value)
        session.flush()


def test_provider_free_demo_assessment_seed_is_stable_and_idempotent() -> None:
    with SessionLocal() as session:
        first = seed_demo_assessment(session)
        second = seed_demo_assessment(session)

    assert first == second == DEMO_ASSESSMENT_ID
    with SessionLocal() as session:
        assessment = session.get(ImpactAssessment, DEMO_ASSESSMENT_ID)
        assert assessment is not None
        assert assessment.status == "completed"
        assert len(assessment.proposed_actions) == 13
        assert all(
            action.execution_status == "not_executed" for action in assessment.proposed_actions
        )


def test_demo_reset_removes_workflow_history_preserves_catalog_and_is_repeatable() -> None:
    with SessionLocal() as session:
        seed_demo_assessment(session)

    with SessionLocal() as session:
        first = reset_demo_workflows(session)
    with SessionLocal() as session:
        second = reset_demo_workflows(session)

    assert first == second
    assert first.policy_analysis_runs == 2
    assert first.policy_comparisons == 1
    assert first.impact_assessments == 2
    assert first.approval_runs == 1
    assert first.execution_commands == 1
    assert first.execution_results == 2
    assert first.learning_assignments == 0
    with SessionLocal() as session:
        assert session.get(Organization, "org-acme-global-manufacturing") is not None
        assert session.get(PolicyChange, "policy-international-travel-2026-09") is not None
        assert session.get(PolicyChange, "policy-international-travel-proposed-2026-10") is not None
