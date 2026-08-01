import logging
import uuid
from datetime import UTC, date, datetime
from time import monotonic

from sqlalchemy import select
from sqlalchemy.orm import Session

from changeops.ai.policy_extractor import (
    PROMPT_VERSION,
    SCHEMA_VERSION,
    ConfiguredExtractionModel,
    ExtractionInvocation,
    invoke_policy_extractor,
)
from changeops.db.models import PolicyChange, PolicyExtractionAttempt, TrainingCourse
from changeops.domain.policy_extraction import (
    ExtractionValidationResult,
    TrainingCourseReference,
    ValidationIssue,
)
from changeops.domain.policy_extraction_validation import validate_policy_extraction

logger = logging.getLogger(__name__)


class PolicyChangeNotFoundError(Exception):
    pass


class PolicyExtractionAttemptNotFoundError(Exception):
    pass


def create_policy_extraction_attempt(
    session: Session,
    policy_change_id: str,
    configured_model: ConfiguredExtractionModel,
    *,
    policy_analysis_run_id: uuid.UUID | None = None,
    retry_reason: str | None = None,
) -> PolicyExtractionAttempt:
    with session.begin():
        policy = session.get(PolicyChange, policy_change_id)
        if policy is None:
            raise PolicyChangeNotFoundError(policy_change_id)
        policy_text = policy.policy_text
        policy_effective_date = policy.effective_date
        organization_id = policy.organization_id

    started_at = monotonic()
    logger.info(
        "Policy extraction model call started: policy_change_id=%s run_id=%s provider=%s model=%s",
        policy_change_id,
        policy_analysis_run_id,
        configured_model.provider,
        configured_model.identifier,
    )
    invocation = invoke_policy_extractor(configured_model.model, policy_text)
    error_code = invocation.parsing_error.split(":", 1)[0] if invocation.parsing_error else None
    logger.info(
        "Policy extraction model call completed: policy_change_id=%s run_id=%s "
        "provider=%s model=%s elapsed_seconds=%.3f parsed=%s error=%s",
        policy_change_id,
        policy_analysis_run_id,
        configured_model.provider,
        configured_model.identifier,
        monotonic() - started_at,
        invocation.proposal is not None,
        error_code,
    )

    with session.begin():
        courses = tuple(
            TrainingCourseReference(
                identifier=course.id,
                name=course.name,
                active=course.active,
            )
            for course in session.scalars(
                select(TrainingCourse)
                .where(TrainingCourse.organization_id == organization_id)
                .order_by(TrainingCourse.id)
            )
        )
        validation = _validation_result(
            invocation=invocation,
            policy_text=policy_text,
            policy_effective_date=policy_effective_date,
            courses=courses,
        )
        proposal = invocation.proposal
        attempt = PolicyExtractionAttempt(
            policy_analysis_run_id=policy_analysis_run_id,
            retry_reason=retry_reason,
            policy_change_id=policy_change_id,
            policy_text_snapshot=policy_text,
            support_status=proposal.support_status if proposal is not None else None,
            validation_outcome=validation.outcome,
            model_provider=configured_model.provider,
            model_identifier=configured_model.identifier,
            prompt_version=PROMPT_VERSION,
            schema_version=SCHEMA_VERSION,
            raw_output=invocation.raw_output,
            parsed_output=proposal.model_dump(mode="json") if proposal is not None else None,
            candidate_rules=(
                proposal.candidate_rules.model_dump(mode="json")
                if proposal is not None and proposal.candidate_rules is not None
                else None
            ),
            accepted_rules=(
                validation.accepted_rules.model_dump(mode="json")
                if validation.accepted_rules is not None
                else None
            ),
            provenance=(
                [item.model_dump(mode="json") for item in proposal.provenance]
                if proposal is not None
                else []
            ),
            findings=(
                [item.model_dump(mode="json") for item in proposal.findings]
                if proposal is not None
                else []
            ),
            validation_errors=[item.model_dump(mode="json") for item in validation.issues],
            created_at=datetime.now(UTC),
        )
        session.add(attempt)
        session.flush()
        attempt_id = attempt.id

    return get_policy_extraction_attempt(session, attempt_id)


def get_policy_extraction_attempt(
    session: Session,
    attempt_id: uuid.UUID,
) -> PolicyExtractionAttempt:
    attempt = session.get(PolicyExtractionAttempt, attempt_id)
    if attempt is None:
        raise PolicyExtractionAttemptNotFoundError(str(attempt_id))
    return attempt


def _validation_result(
    *,
    invocation: ExtractionInvocation,
    policy_text: str,
    policy_effective_date: date,
    courses: tuple[TrainingCourseReference, ...],
) -> ExtractionValidationResult:
    if invocation.proposal is None:
        return ExtractionValidationResult(
            outcome="validation_failed",
            accepted_rules=None,
            issues=(
                ValidationIssue(
                    code="structured_output_failure",
                    message=(
                        invocation.parsing_error or "The model did not return structured output."
                    ),
                ),
            ),
        )
    return validate_policy_extraction(
        invocation.proposal,
        policy_text=policy_text,
        policy_effective_date=policy_effective_date,
        training_courses=courses,
    )
