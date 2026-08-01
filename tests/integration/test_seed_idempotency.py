from sqlalchemy import func, select
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
            "policy_changes": 1,
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
            "policy_system_dependencies": 2,
            "policy_document_dependencies": 3,
            "policy_training_dependencies": 1,
            "customer_commitments": 2,
            "commitment_assignments": 2,
        }
    )


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
