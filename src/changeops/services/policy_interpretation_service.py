import logging
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from time import monotonic

from sqlalchemy import select
from sqlalchemy.orm import Session

from changeops.ai.policy_interpreter import (
    PROMPT_VERSION,
    ConfiguredInterpretationModel,
    invoke_policy_interpreter,
)
from changeops.db.models import (
    ChangePlan,
    ImpactAssessment,
    PolicyExtractionAttempt,
    PolicyInterpretationAttempt,
)
from changeops.domain.policy_interpretation import (
    INTERPRETATION_SCHEMA_VERSION,
    ChangePlanValidationError,
)
from changeops.domain.policy_interpretation_validation import validate_candidate_change_plan
from changeops.services.assessment_service import (
    ImpactAssessmentNotFoundError,
    get_impact_assessment,
)
from changeops.services.policy_analysis_service import get_policy_analysis_run
from changeops.services.policy_interpretation_serializer import (
    build_policy_interpretation_input,
)

logger = logging.getLogger(__name__)


class AssessmentNotInterpretableError(Exception):
    pass


class ChangePlanNotFoundError(Exception):
    pass


class PolicyInterpretationAttemptNotFoundError(Exception):
    pass


class InterpretationFailedError(Exception):
    def __init__(self, attempt_id: uuid.UUID, failure_code: str) -> None:
        self.attempt_id = attempt_id
        self.failure_code = failure_code
        super().__init__(failure_code)


def create_or_get_change_plan(
    session: Session,
    assessment_id: uuid.UUID,
    model_factory: Callable[[], ConfiguredInterpretationModel],
) -> tuple[ChangePlan, bool]:
    existing = session.scalar(
        select(ChangePlan).where(ChangePlan.impact_assessment_id == assessment_id)
    )
    if existing is not None:
        return existing, False

    try:
        assessment = get_impact_assessment(session, assessment_id)
    except ImpactAssessmentNotFoundError:
        raise
    if assessment.status != "completed" or assessment.policy_analysis_run_id is None:
        raise AssessmentNotInterpretableError(str(assessment_id))
    run = get_policy_analysis_run(session, assessment.policy_analysis_run_id)
    if (
        run.status != "completed"
        or run.assessment_id != assessment.id
        or run.latest_extraction_attempt_id is None
    ):
        raise AssessmentNotInterpretableError(str(assessment_id))
    accepted_attempt = session.get(PolicyExtractionAttempt, run.latest_extraction_attempt_id)
    if (
        accepted_attempt is None
        or accepted_attempt.validation_outcome != "accepted"
        or accepted_attempt.accepted_rules is None
        or accepted_attempt.candidate_rules is None
    ):
        raise AssessmentNotInterpretableError(str(assessment_id))

    configured_model = model_factory()
    interpretation_input = build_policy_interpretation_input(assessment, run, accepted_attempt)
    persisted_run_id = run.id
    persisted_assessment_id = assessment.id
    session.rollback()
    started_at = monotonic()
    logger.info(
        "Policy interpretation model call started: run_id=%s assessment_id=%s provider=%s model=%s",
        persisted_run_id,
        persisted_assessment_id,
        configured_model.provider,
        configured_model.identifier,
    )
    invocation = invoke_policy_interpreter(configured_model.model, interpretation_input)
    error_code = invocation.parsing_error.split(":", 1)[0] if invocation.parsing_error else None
    logger.info(
        "Policy interpretation model call completed: run_id=%s assessment_id=%s "
        "provider=%s model=%s elapsed_seconds=%.3f parsed=%s error=%s",
        persisted_run_id,
        persisted_assessment_id,
        configured_model.provider,
        configured_model.identifier,
        monotonic() - started_at,
        invocation.candidate is not None,
        error_code,
    )
    now = datetime.now(UTC)
    candidate_json = (
        invocation.candidate.model_dump(mode="json") if invocation.candidate is not None else None
    )

    if invocation.parsing_error is not None:
        provider_failed = invocation.parsing_error.startswith("model_invocation_failed")
        failure_code = "interpretation_malformed_output"
        if provider_failed:
            failure_code = "interpretation_provider_error"
        elif invocation.parsing_error == "structured_output_boundary_violation":
            failure_code = "interpretation_boundary_violation"
        attempt_id = _persist_attempt(
            session,
            run_id=persisted_run_id,
            assessment_id=persisted_assessment_id,
            configured_model=configured_model,
            now=now,
            status="provider_failed" if provider_failed else "invalid",
            raw_output=invocation.raw_output,
            candidate=None,
            validated=None,
            errors=[
                {
                    "code": failure_code,
                    "message": "Interpretation did not return valid structured output.",
                }
            ],
            failure_code=failure_code,
            failure_message="The interpretation provider response could not be accepted.",
        )
        raise InterpretationFailedError(attempt_id, failure_code)

    try:
        validated = validate_candidate_change_plan(invocation.candidate, interpretation_input)
    except ChangePlanValidationError as error:
        codes = {item.code for item in error.issues}
        failure_code = (
            "interpretation_boundary_violation"
            if codes & {"impact_mutation", "invented_enterprise_fact"}
            else "interpretation_invalid_reference"
        )
        attempt_id = _persist_attempt(
            session,
            run_id=persisted_run_id,
            assessment_id=persisted_assessment_id,
            configured_model=configured_model,
            now=now,
            status="invalid",
            raw_output=invocation.raw_output,
            candidate=candidate_json,
            validated=None,
            errors=[item.model_dump(mode="json") for item in error.issues],
            failure_code=failure_code,
            failure_message="Deterministic grounding validation rejected the interpretation.",
        )
        raise InterpretationFailedError(attempt_id, failure_code) from error

    with session.begin():
        locked_assessment = session.get(
            ImpactAssessment, persisted_assessment_id, with_for_update=True
        )
        if locked_assessment is None:
            raise ImpactAssessmentNotFoundError(str(persisted_assessment_id))
        existing = session.scalar(
            select(ChangePlan).where(ChangePlan.impact_assessment_id == persisted_assessment_id)
        )
        if existing is not None:
            plan_id = existing.id
            created = False
        else:
            attempt = PolicyInterpretationAttempt(
                policy_analysis_run_id=persisted_run_id,
                impact_assessment_id=persisted_assessment_id,
                status="accepted",
                raw_output=invocation.raw_output,
                candidate_change_plan=candidate_json,
                validated_change_plan=validated.model_dump(mode="json"),
                validation_errors=[],
                model_provider=configured_model.provider,
                model_identifier=configured_model.identifier,
                prompt_version=PROMPT_VERSION,
                schema_version=INTERPRETATION_SCHEMA_VERSION,
                created_at=now,
                completed_at=now,
                failure_code=None,
                failure_message=None,
            )
            session.add(attempt)
            session.flush()
            plan = ChangePlan(
                policy_analysis_run_id=persisted_run_id,
                impact_assessment_id=persisted_assessment_id,
                interpretation_attempt_id=attempt.id,
                schema_version=INTERPRETATION_SCHEMA_VERSION,
                validated_plan=validated.model_dump(mode="json"),
                created_at=now,
            )
            session.add(plan)
            session.flush()
            plan_id = plan.id
            created = True
    return get_change_plan(session, plan_id), created


def _persist_attempt(
    session: Session,
    *,
    run_id: uuid.UUID,
    assessment_id: uuid.UUID,
    configured_model: ConfiguredInterpretationModel,
    now: datetime,
    status: str,
    raw_output,
    candidate,
    validated,
    errors: list[dict],
    failure_code: str,
    failure_message: str,
) -> uuid.UUID:
    with session.begin():
        attempt = PolicyInterpretationAttempt(
            policy_analysis_run_id=run_id,
            impact_assessment_id=assessment_id,
            status=status,
            raw_output=raw_output,
            candidate_change_plan=candidate,
            validated_change_plan=validated,
            validation_errors=errors,
            model_provider=configured_model.provider,
            model_identifier=configured_model.identifier,
            prompt_version=PROMPT_VERSION,
            schema_version=INTERPRETATION_SCHEMA_VERSION,
            created_at=now,
            completed_at=now,
            failure_code=failure_code,
            failure_message=failure_message,
        )
        session.add(attempt)
        session.flush()
        attempt_id = attempt.id
    return attempt_id


def get_change_plan(session: Session, plan_id: uuid.UUID) -> ChangePlan:
    plan = session.get(ChangePlan, plan_id)
    if plan is None:
        raise ChangePlanNotFoundError(str(plan_id))
    return plan


def get_change_plan_for_assessment(session: Session, assessment_id: uuid.UUID) -> ChangePlan:
    plan = session.scalar(
        select(ChangePlan).where(ChangePlan.impact_assessment_id == assessment_id)
    )
    if plan is None:
        raise ChangePlanNotFoundError(str(assessment_id))
    return plan


def get_interpretation_attempt(
    session: Session, attempt_id: uuid.UUID
) -> PolicyInterpretationAttempt:
    attempt = session.get(PolicyInterpretationAttempt, attempt_id)
    if attempt is None:
        raise PolicyInterpretationAttemptNotFoundError(str(attempt_id))
    return attempt
