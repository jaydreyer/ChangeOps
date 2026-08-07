import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from changeops.db.models import (
    ImpactAssessment,
    PolicyAnalysisRun,
    PolicyChange,
    PolicyExtractionAttempt,
)
from changeops.domain.policy_analysis import WORKFLOW_VERSION
from changeops.domain.types import InternationalTravelPolicyRules
from changeops.services.assessment_service import create_impact_assessment_from_rules
from changeops.services.seed_service import (
    POLICY_CHANGE_ID,
    PROPOSED_POLICY_CHANGE_ID,
)

DEMO_POLICY_ANALYSIS_RUN_ID = uuid.UUID("8f4f647d-7f2d-4da8-8e02-77d5301f2001")
DEMO_ASSESSMENT_ID = uuid.UUID("8f4f647d-7f2d-4da8-8e02-77d5301f2002")
DEMO_EXTRACTION_ATTEMPT_ID = uuid.UUID("8f4f647d-7f2d-4da8-8e02-77d5301f2003")
DEMO_PROPOSED_POLICY_ANALYSIS_RUN_ID = uuid.UUID("8f4f647d-7f2d-4da8-8e02-77d5301f2011")
DEMO_PROPOSED_ASSESSMENT_ID = uuid.UUID("8f4f647d-7f2d-4da8-8e02-77d5301f2012")
DEMO_PROPOSED_EXTRACTION_ATTEMPT_ID = uuid.UUID("8f4f647d-7f2d-4da8-8e02-77d5301f2013")


def seed_demo_assessment(session: Session) -> uuid.UUID:
    return seed_demo_policy_analysis(
        session,
        policy_change_id=POLICY_CHANGE_ID,
        run_id=DEMO_POLICY_ANALYSIS_RUN_ID,
        assessment_id=DEMO_ASSESSMENT_ID,
        extraction_attempt_id=DEMO_EXTRACTION_ATTEMPT_ID,
    )


def seed_demo_proposed_assessment(session: Session) -> uuid.UUID:
    return seed_demo_policy_analysis(
        session,
        policy_change_id=PROPOSED_POLICY_CHANGE_ID,
        run_id=DEMO_PROPOSED_POLICY_ANALYSIS_RUN_ID,
        assessment_id=DEMO_PROPOSED_ASSESSMENT_ID,
        extraction_attempt_id=DEMO_PROPOSED_EXTRACTION_ATTEMPT_ID,
    )


def seed_demo_policy_analysis(
    session: Session,
    *,
    policy_change_id: str,
    run_id: uuid.UUID,
    assessment_id: uuid.UUID,
    extraction_attempt_id: uuid.UUID,
) -> uuid.UUID:
    existing = session.get(ImpactAssessment, assessment_id)
    session.rollback()
    if existing is not None:
        with session.begin():
            run = session.get(PolicyAnalysisRun, run_id, with_for_update=True)
            policy = session.get(PolicyChange, policy_change_id)
            if run is None or policy is None or run.assessment_id != assessment_id:
                raise RuntimeError("Seeded demonstration lifecycle is inconsistent.")
            attempt = session.get(PolicyExtractionAttempt, extraction_attempt_id)
            if attempt is None:
                attempt = _accepted_attempt(policy, run.id, extraction_attempt_id)
                session.add(attempt)
                session.flush()
                run.latest_extraction_attempt_id = attempt.id
            if run.status != "completed":
                now = datetime.now(UTC)
                run.status = "completed"
                run.current_step = "terminal"
                run.updated_at = now
                run.completed_at = now
        return assessment_id

    now = datetime.now(UTC)
    with session.begin():
        policy = session.get(PolicyChange, policy_change_id)
        if policy is None:
            raise RuntimeError("Seeded policy must exist before the demonstration assessment.")
        run = session.get(PolicyAnalysisRun, run_id)
        if run is None:
            run = PolicyAnalysisRun(
                id=run_id,
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
                model_identifier="fixture_extractor_v1",
                prompt_version="seeded-demo-prompt-v1",
                schema_version="seeded-demo-v1",
                accepted_rule_provenance=[
                    {"source": "policy_text", **item} for item in _provenance(policy)
                ],
                created_at=now,
                updated_at=now,
                completed_at=None,
            )
            session.add(run)
            session.flush()
        attempt = session.get(PolicyExtractionAttempt, extraction_attempt_id)
        if attempt is None:
            attempt = _accepted_attempt(policy, run.id, extraction_attempt_id)
            session.add(attempt)
            session.flush()
        run.latest_extraction_attempt_id = attempt.id
        rules = InternationalTravelPolicyRules.model_validate(policy.structured_rules)

    assessment = create_impact_assessment_from_rules(
        session,
        policy_change_id,
        rules,
        policy_analysis_run_id=run_id,
        assessment_id=assessment_id,
    )
    session.rollback()
    with session.begin():
        run = session.get(PolicyAnalysisRun, run_id, with_for_update=True)
        if run is None:
            raise RuntimeError("Seeded policy-analysis run was not persisted.")
        run.status = "completed"
        run.current_step = "terminal"
        run.assessment_id = assessment.id
        run.updated_at = now
        run.completed_at = now
    return assessment.id


def _accepted_attempt(
    policy: PolicyChange,
    run_id: uuid.UUID,
    attempt_id: uuid.UUID,
) -> PolicyExtractionAttempt:
    accepted = dict(policy.structured_rules)
    candidate = {
        **accepted,
        "effective_date": policy.effective_date.isoformat(),
        "security_training": {"course_name": "International Travel Security"},
    }
    parsed = {
        "policy_family": "international_travel",
        "support_status": "supported",
        "candidate_rules": candidate,
        "provenance": _provenance(policy),
        "findings": [],
    }
    return PolicyExtractionAttempt(
        id=attempt_id,
        policy_analysis_run_id=run_id,
        retry_reason=None,
        policy_change_id=policy.id,
        policy_text_snapshot=policy.policy_text,
        support_status="supported",
        validation_outcome="accepted",
        model_provider="seeded_demo",
        model_identifier="fixture_extractor_v1",
        prompt_version="seeded-demo-prompt-v1",
        schema_version="seeded-demo-v1",
        raw_output={"source": "seeded_demo"},
        parsed_output=parsed,
        candidate_rules=candidate,
        accepted_rules=accepted,
        provenance=_provenance(policy),
        findings=[],
        validation_errors=[],
        created_at=datetime.now(UTC),
    )


def _provenance(policy: PolicyChange) -> list[dict[str, object]]:
    proposed = policy.id == PROPOSED_POLICY_CHANGE_ID
    effective = "Effective October 1, 2026" if proposed else "Effective September 1, 2026"
    workers = "employees" if proposed else "employees and contractors"
    excluded = "United States, Canada, and Mexico" if proposed else "United States and Canada"
    exemption = (
        "Travel booked before October 1, 2026 is exempt"
        if proposed
        else "Travel booked before September 1, 2026 is exempt"
    )
    quotes = {
        "policy_family": "traveling\ninternationally for business",
        "candidate_rules.kind": "traveling\ninternationally for business",
        "candidate_rules.schema_version": "traveling\ninternationally for business",
        "candidate_rules.effective_date": effective,
        "candidate_rules.worker_scope.assigned_work_country": "U.S.-based",
        "candidate_rules.worker_scope.worker_types": workers,
        "candidate_rules.trip_scope.origin_country": "United States",
        "candidate_rules.trip_scope.excluded_destination_countries": excluded,
        "candidate_rules.manager_approval.booking_before_effective_date_is_exempt": exemption,
        "candidate_rules.security_training.course_name": "International Travel Security",
    }
    return [
        {
            "field_path": field_path,
            "start": policy.policy_text.index(quote),
            "end": policy.policy_text.index(quote) + len(quote),
            "quote": quote,
        }
        for field_path, quote in quotes.items()
    ]
