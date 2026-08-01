import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from changeops.db.models import ImpactAssessment, PolicyAnalysisRun, PolicyChange
from changeops.domain.policy_analysis import WORKFLOW_VERSION
from changeops.domain.types import InternationalTravelPolicyRules
from changeops.services.assessment_service import create_impact_assessment_from_rules
from changeops.services.seed_service import POLICY_CHANGE_ID

DEMO_POLICY_ANALYSIS_RUN_ID = uuid.UUID("8f4f647d-7f2d-4da8-8e02-77d5301f2001")
DEMO_ASSESSMENT_ID = uuid.UUID("8f4f647d-7f2d-4da8-8e02-77d5301f2002")


def seed_demo_assessment(session: Session) -> uuid.UUID:
    existing = session.get(ImpactAssessment, DEMO_ASSESSMENT_ID)
    if existing is not None:
        existing_id = existing.id
        session.rollback()
        with session.begin():
            run = session.get(
                PolicyAnalysisRun,
                DEMO_POLICY_ANALYSIS_RUN_ID,
                with_for_update=True,
            )
            if run is None or run.assessment_id not in {None, existing_id}:
                raise RuntimeError("Seeded demonstration lifecycle is inconsistent.")
            if run.status != "completed":
                now = datetime.now(UTC)
                run.status = "completed"
                run.current_step = "terminal"
                run.assessment_id = existing_id
                run.updated_at = now
                run.completed_at = now
        return existing_id
    session.rollback()

    now = datetime.now(UTC)
    with session.begin():
        policy = session.get(PolicyChange, POLICY_CHANGE_ID)
        if policy is None:
            raise RuntimeError("Seeded policy must exist before the demonstration assessment.")
        run = session.get(PolicyAnalysisRun, DEMO_POLICY_ANALYSIS_RUN_ID)
        if run is None:
            run = PolicyAnalysisRun(
                id=DEMO_POLICY_ANALYSIS_RUN_ID,
                organization_id=policy.organization_id,
                policy_change_id=policy.id,
                policy_text_snapshot=policy.policy_text,
                status="running",
                current_step="create_assessment",
                latest_extraction_attempt_id=None,
                assessment_id=None,
                retry_count=0,
                failure_code=None,
                failure_detail=None,
                workflow_version=WORKFLOW_VERSION,
                model_provider="seeded_demo",
                model_identifier="deterministic_seed_rules",
                prompt_version="not_applicable",
                schema_version="seeded-demo-v1",
                accepted_rule_provenance=[
                    {
                        "source": "seeded_demo",
                        "detail": "Provider-free local demonstration rules.",
                    }
                ],
                created_at=now,
                updated_at=now,
                completed_at=None,
            )
            session.add(run)
        rules = InternationalTravelPolicyRules.model_validate(policy.structured_rules)

    assessment = create_impact_assessment_from_rules(
        session,
        POLICY_CHANGE_ID,
        rules,
        policy_analysis_run_id=DEMO_POLICY_ANALYSIS_RUN_ID,
        assessment_id=DEMO_ASSESSMENT_ID,
    )
    session.rollback()
    with session.begin():
        run = session.get(PolicyAnalysisRun, DEMO_POLICY_ANALYSIS_RUN_ID, with_for_update=True)
        if run is None:
            raise RuntimeError("Seeded policy-analysis run was not persisted.")
        run.status = "completed"
        run.current_step = "terminal"
        run.assessment_id = assessment.id
        run.updated_at = now
        run.completed_at = now
    return assessment.id
