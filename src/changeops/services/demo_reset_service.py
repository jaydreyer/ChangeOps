import os
from dataclasses import dataclass

from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from changeops.db.models import (
    ActionApprovalRun,
    ExecutionCommand,
    ExecutionResult,
    ImpactAssessment,
    Organization,
    PolicyAnalysisRun,
    SimulatedLearningAssignment,
)
from changeops.services.seed_service import ORGANIZATION_ID, seed_database

DEMO_RESET_CONFIRMATION = "reset-changeops-local-demo"
LOCAL_DATABASE_HOSTS = {"db", "localhost", "127.0.0.1", "::1"}
LOCAL_DATABASE_NAMES = {"changeops"}

WORKFLOW_TABLES = (
    "execution_results",
    "simulated_learning_assignments",
    "execution_commands",
    "action_approval_run_transitions",
    "action_approval_run_items",
    "action_review_decisions",
    "action_approval_runs",
    "action_reviews",
    "change_plans",
    "policy_interpretation_attempts",
    "assessment_unresolved_questions",
    "proposed_actions",
    "assessment_impact_path_elements",
    "assessment_impact_evidence",
    "assessment_enterprise_impacts",
    "finding_evidence",
    "findings",
    "evidence",
    "assessment_worker_results",
    "impact_assessments",
    "policy_analysis_clarifications",
    "policy_extraction_attempts",
    "policy_analysis_runs",
)


class DemoResetSafetyError(RuntimeError):
    pass


@dataclass(frozen=True)
class DemoResetSummary:
    policy_analysis_runs: int
    impact_assessments: int
    approval_runs: int
    execution_commands: int
    execution_results: int
    learning_assignments: int


def validate_demo_reset_target(database_url: str, confirmation: str | None) -> None:
    if confirmation != DEMO_RESET_CONFIRMATION:
        raise DemoResetSafetyError("The explicit local demo-reset confirmation is missing.")
    url = make_url(database_url)
    if url.get_backend_name() != "postgresql":
        raise DemoResetSafetyError("Demo reset supports only the local PostgreSQL stack.")
    if url.host not in LOCAL_DATABASE_HOSTS or url.database not in LOCAL_DATABASE_NAMES:
        raise DemoResetSafetyError(
            "Demo reset refused an unrecognized database host or database name."
        )


def reset_demo_workflows(session: Session) -> DemoResetSummary:
    marker = session.get(Organization, ORGANIZATION_ID)
    if marker is None:
        raise DemoResetSafetyError("The seeded demo organization marker is missing.")
    session.execute(text(f"TRUNCATE TABLE {', '.join(WORKFLOW_TABLES)}"))
    seed_database(session)
    return _summary(session)


def reset_from_environment(session: Session, database_url: str) -> DemoResetSummary:
    validate_demo_reset_target(
        database_url,
        os.environ.get("CHANGEOPS_DEMO_RESET_CONFIRMED"),
    )
    return reset_demo_workflows(session)


def _summary(session: Session) -> DemoResetSummary:
    def count(model) -> int:
        return session.scalar(select(func.count()).select_from(model)) or 0

    return DemoResetSummary(
        policy_analysis_runs=count(PolicyAnalysisRun),
        impact_assessments=count(ImpactAssessment),
        approval_runs=count(ActionApprovalRun),
        execution_commands=count(ExecutionCommand),
        execution_results=count(ExecutionResult),
        learning_assignments=count(SimulatedLearningAssignment),
    )
