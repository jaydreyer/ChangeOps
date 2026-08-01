import uuid
from datetime import UTC, datetime

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from changeops.ai.policy_extractor import (
    PROMPT_VERSION,
    SCHEMA_VERSION,
    ConfiguredExtractionModel,
)
from changeops.db.models import (
    PolicyAnalysisClarification,
    PolicyAnalysisRun,
    PolicyChange,
    PolicyExtractionAttempt,
    TrainingCourse,
)
from changeops.domain.policy_analysis import (
    BOOKING_EXCEPTION_FIELD,
    BOOKING_EXCEPTION_QUESTION_CODE,
    WORKFLOW_VERSION,
    ExtractionDecision,
    decide_extraction_outcome,
)
from changeops.domain.policy_extraction import (
    PolicyExtractionProposal,
    TrainingCourseReference,
    ValidationIssue,
)
from changeops.domain.policy_extraction_validation import validate_policy_extraction
from changeops.domain.types import InternationalTravelPolicyRules
from changeops.services.assessment_service import create_impact_assessment_from_rules
from changeops.services.policy_extraction_service import create_policy_extraction_attempt


class PolicyAnalysisRunNotFoundError(Exception):
    pass


class PolicyAnalysisPolicyNotFoundError(Exception):
    pass


class ClarificationNotFoundError(Exception):
    pass


class ClarificationStateConflictError(Exception):
    pass


class ClarificationAnswerInvalidError(Exception):
    pass


class WorkflowStateError(Exception):
    pass


def create_policy_analysis_run_record(
    session: Session,
    policy_change_id: str,
    configured_model: ConfiguredExtractionModel,
) -> PolicyAnalysisRun:
    now = datetime.now(UTC)
    with session.begin():
        policy = session.get(PolicyChange, policy_change_id)
        if policy is None:
            raise PolicyAnalysisPolicyNotFoundError(policy_change_id)
        run = PolicyAnalysisRun(
            organization_id=policy.organization_id,
            policy_change_id=policy.id,
            policy_text_snapshot=policy.policy_text,
            status="pending",
            current_step="initialize",
            latest_extraction_attempt_id=None,
            assessment_id=None,
            retry_count=0,
            failure_code=None,
            failure_detail=None,
            workflow_version=WORKFLOW_VERSION,
            model_provider=configured_model.provider,
            model_identifier=configured_model.identifier,
            prompt_version=PROMPT_VERSION,
            schema_version=SCHEMA_VERSION,
            accepted_rule_provenance=[],
            created_at=now,
            updated_at=now,
            completed_at=None,
        )
        session.add(run)
        session.flush()
        run_id = run.id
    return get_policy_analysis_run(session, run_id)


def get_policy_analysis_run(session: Session, run_id: uuid.UUID) -> PolicyAnalysisRun:
    run = session.scalar(
        select(PolicyAnalysisRun)
        .where(PolicyAnalysisRun.id == run_id)
        .options(selectinload(PolicyAnalysisRun.clarifications))
    )
    if run is None:
        raise PolicyAnalysisRunNotFoundError(str(run_id))
    return run


def load_run_route(session: Session, run_id: uuid.UUID) -> str:
    run = get_policy_analysis_run(session, run_id)
    if run.status in {"completed", "unsupported", "failed"}:
        return "terminal"
    if run.status == "awaiting_clarification":
        answered = next(
            (item for item in run.clarifications if item.status == "answered"),
            None,
        )
        return "apply_clarification" if answered is not None else "pause"
    if run.latest_extraction_attempt_id is not None:
        return "evaluate"
    return "extract"


def extract_for_run(
    session: Session,
    run_id: uuid.UUID,
    configured_model: ConfiguredExtractionModel,
) -> PolicyExtractionAttempt:
    run = get_policy_analysis_run(session, run_id)
    if run.status not in {"pending", "running"}:
        raise WorkflowStateError(f"run status {run.status!r} cannot extract")
    retry_reason = run.failure_detail if run.retry_count else None
    policy_change_id = run.policy_change_id
    persisted_run_id = run.id
    session.rollback()
    with session.begin():
        locked = session.get(PolicyAnalysisRun, run_id, with_for_update=True)
        if locked is None:
            raise PolicyAnalysisRunNotFoundError(str(run_id))
        locked.status = "running"
        locked.current_step = "extract"
        locked.failure_code = None
        locked.updated_at = datetime.now(UTC)
    attempt = create_policy_extraction_attempt(
        session,
        policy_change_id,
        configured_model,
        policy_analysis_run_id=persisted_run_id,
        retry_reason=retry_reason,
    )
    with session.begin():
        locked = session.get(PolicyAnalysisRun, run_id, with_for_update=True)
        if locked is None:
            raise PolicyAnalysisRunNotFoundError(str(run_id))
        locked.status = "running"
        locked.current_step = "evaluate_extraction"
        locked.latest_extraction_attempt_id = attempt.id
        locked.failure_code = None
        locked.failure_detail = None
        locked.updated_at = datetime.now(UTC)
    return attempt


def evaluate_run_extraction(session: Session, run_id: uuid.UUID) -> ExtractionDecision:
    run = get_policy_analysis_run(session, run_id)
    if run.latest_extraction_attempt_id is None:
        raise WorkflowStateError("run has no extraction attempt")
    attempt = session.get(PolicyExtractionAttempt, run.latest_extraction_attempt_id)
    if attempt is None or attempt.policy_analysis_run_id != run.id:
        raise WorkflowStateError("run extraction attempt association is invalid")
    issues = tuple(ValidationIssue.model_validate(item) for item in attempt.validation_errors)
    decision = decide_extraction_outcome(
        validation_outcome=attempt.validation_outcome,
        issues=issues,
        retry_count=run.retry_count,
    )
    session.rollback()
    now = datetime.now(UTC)
    with session.begin():
        locked = session.get(PolicyAnalysisRun, run_id, with_for_update=True)
        if locked is None:
            raise PolicyAnalysisRunNotFoundError(str(run_id))
        if decision.route == "accepted":
            locked.current_step = "create_assessment"
            locked.accepted_rule_provenance = [
                {"source": "policy_text", **item} for item in attempt.provenance
            ]
        elif decision.route == "unsupported":
            _terminalize(locked, status="unsupported", now=now)
        elif decision.route == "clarify":
            locked.current_step = "evaluate_clarification"
        elif decision.route == "retry":
            locked.current_step = "extract"
            locked.retry_count += 1
            locked.failure_detail = decision.retry_reason
        else:
            _terminalize(
                locked,
                status="failed",
                now=now,
                failure_code=decision.failure_code,
                failure_detail=decision.detail,
            )
        locked.updated_at = now
    return decision


def persist_material_clarification(
    session: Session,
    run_id: uuid.UUID,
) -> PolicyAnalysisClarification:
    now = datetime.now(UTC)
    with session.begin():
        run = session.get(PolicyAnalysisRun, run_id, with_for_update=True)
        if run is None:
            raise PolicyAnalysisRunNotFoundError(str(run_id))
        existing = session.scalar(
            select(PolicyAnalysisClarification).where(
                PolicyAnalysisClarification.policy_analysis_run_id == run_id,
                PolicyAnalysisClarification.question_code == BOOKING_EXCEPTION_QUESTION_CODE,
            )
        )
        if existing is None:
            existing = PolicyAnalysisClarification(
                policy_analysis_run_id=run.id,
                question_code=BOOKING_EXCEPTION_QUESTION_CODE,
                question_text=(
                    "Confirm that trips booked before the policy effective date are exempt "
                    "from the new manager-approval requirement."
                ),
                expected_answer_contract={"type": "literal", "allowed_values": [True]},
                affected_fields=[BOOKING_EXCEPTION_FIELD],
                status="pending",
                answer=None,
                responder_identity=None,
                answer_provenance=None,
                created_at=now,
                answered_at=None,
            )
            session.add(existing)
            session.flush()
        run.status = "awaiting_clarification"
        run.current_step = "await_clarification"
        run.updated_at = now
        clarification_id = existing.id
    clarification = session.get(PolicyAnalysisClarification, clarification_id)
    if clarification is None:
        raise ClarificationNotFoundError(str(clarification_id))
    return clarification


def answer_clarification(
    session: Session,
    run_id: uuid.UUID,
    clarification_id: uuid.UUID,
    *,
    value: bool,
    responder_identity: str,
) -> None:
    now = datetime.now(UTC)
    with session.begin():
        run = session.get(PolicyAnalysisRun, run_id, with_for_update=True)
        if run is None:
            raise PolicyAnalysisRunNotFoundError(str(run_id))
        clarification = session.get(
            PolicyAnalysisClarification,
            clarification_id,
            with_for_update=True,
        )
        if clarification is None or clarification.policy_analysis_run_id != run.id:
            raise ClarificationNotFoundError(str(clarification_id))
        if run.status != "awaiting_clarification" or clarification.status != "pending":
            raise ClarificationStateConflictError(str(clarification_id))
        if value is not True:
            raise ClarificationAnswerInvalidError(str(clarification_id))
        clarification.status = "answered"
        clarification.answer = {"value": value}
        clarification.responder_identity = responder_identity
        clarification.answer_provenance = {
            "source": "human",
            "clarification_id": str(clarification.id),
            "responder_identity": responder_identity,
            "answered_at": now.isoformat(),
            "affected_fields": clarification.affected_fields,
        }
        clarification.answered_at = now
        run.updated_at = now


def apply_answered_clarification(
    session: Session,
    run_id: uuid.UUID,
) -> PolicyExtractionAttempt:
    run = get_policy_analysis_run(session, run_id)
    clarification = next(
        (
            item
            for item in run.clarifications
            if item.question_code == BOOKING_EXCEPTION_QUESTION_CODE and item.status == "answered"
        ),
        None,
    )
    if clarification is None or clarification.answer is None:
        raise ClarificationStateConflictError("no answered material clarification")
    clarified_value = clarification.answer.get("value")
    if clarified_value is not True:
        raise ClarificationAnswerInvalidError(str(clarification.id))

    original = session.get(PolicyExtractionAttempt, run.latest_extraction_attempt_id)
    policy = session.get(PolicyChange, run.policy_change_id)
    if original is None or policy is None or original.parsed_output is None:
        raise WorkflowStateError("clarification source attempt is unavailable")
    proposal = PolicyExtractionProposal.model_validate(original.parsed_output)
    if proposal.candidate_rules is None:
        raise WorkflowStateError("clarification source has no candidate rules")
    clarified_candidate = proposal.candidate_rules.model_copy(
        update={
            "manager_approval": proposal.candidate_rules.manager_approval.model_copy(
                update={"booking_before_effective_date_is_exempt": clarified_value}
            )
        }
    )
    clarified_proposal = proposal.model_copy(
        update={"candidate_rules": clarified_candidate, "findings": ()}
    )
    courses = tuple(
        TrainingCourseReference(
            identifier=item.id,
            name=item.name,
            active=item.active,
        )
        for item in session.scalars(
            select(TrainingCourse).where(TrainingCourse.organization_id == run.organization_id)
        )
    )
    validation = validate_policy_extraction(
        clarified_proposal,
        policy_text=run.policy_text_snapshot,
        policy_effective_date=policy.effective_date,
        training_courses=courses,
    )
    if validation.outcome != "accepted" or validation.accepted_rules is None:
        raise WorkflowStateError("answered clarification did not produce accepted rules")
    human_provenance = clarification.answer_provenance or {}
    session.rollback()
    now = datetime.now(UTC)
    with session.begin():
        derived = PolicyExtractionAttempt(
            policy_analysis_run_id=run.id,
            retry_reason=f"human_clarification:{clarification.id}",
            policy_change_id=run.policy_change_id,
            policy_text_snapshot=run.policy_text_snapshot,
            support_status="supported",
            validation_outcome="accepted",
            model_provider=run.model_provider,
            model_identifier=run.model_identifier,
            prompt_version=run.prompt_version,
            schema_version=run.schema_version,
            raw_output=None,
            parsed_output=clarified_proposal.model_dump(mode="json"),
            candidate_rules=clarified_candidate.model_dump(mode="json"),
            accepted_rules=validation.accepted_rules.model_dump(mode="json"),
            provenance=original.provenance,
            findings=[],
            validation_errors=[],
            created_at=now,
        )
        session.add(derived)
        session.flush()
        locked = session.get(PolicyAnalysisRun, run_id, with_for_update=True)
        if locked is None:
            raise PolicyAnalysisRunNotFoundError(str(run_id))
        locked.status = "running"
        locked.current_step = "create_assessment"
        locked.latest_extraction_attempt_id = derived.id
        locked.accepted_rule_provenance = [
            {"source": "policy_text", **item}
            for item in original.provenance
            if item.get("field_path") != BOOKING_EXCEPTION_FIELD
        ] + [human_provenance]
        locked.updated_at = now
        derived_id = derived.id
    result = session.get(PolicyExtractionAttempt, derived_id)
    if result is None:
        raise WorkflowStateError("derived extraction attempt was not persisted")
    return result


def create_assessment_for_run(session: Session, run_id: uuid.UUID) -> uuid.UUID:
    run = get_policy_analysis_run(session, run_id)
    if run.assessment_id is not None:
        return run.assessment_id
    if run.latest_extraction_attempt_id is None:
        raise WorkflowStateError("assessment boundary has no extraction attempt")
    attempt = session.get(PolicyExtractionAttempt, run.latest_extraction_attempt_id)
    pending = session.scalar(
        select(PolicyAnalysisClarification.id).where(
            PolicyAnalysisClarification.policy_analysis_run_id == run.id,
            PolicyAnalysisClarification.status == "pending",
        )
    )
    if (
        attempt is None
        or attempt.policy_analysis_run_id != run.id
        or attempt.validation_outcome != "accepted"
        or attempt.accepted_rules is None
        or pending is not None
    ):
        raise WorkflowStateError("only accepted rules with no pending clarification may proceed")
    try:
        rules = InternationalTravelPolicyRules.model_validate(attempt.accepted_rules)
    except ValidationError as error:
        raise WorkflowStateError("accepted rules failed the assessment contract") from error
    policy_change_id = run.policy_change_id
    persisted_run_id = run.id
    session.rollback()
    assessment = create_impact_assessment_from_rules(
        session,
        policy_change_id,
        rules,
        policy_analysis_run_id=persisted_run_id,
    )
    assessment_id = assessment.id
    session.rollback()
    with session.begin():
        locked = session.get(PolicyAnalysisRun, run_id, with_for_update=True)
        if locked is None:
            raise PolicyAnalysisRunNotFoundError(str(run_id))
        locked.assessment_id = assessment_id
        locked.current_step = "finalize"
        locked.updated_at = datetime.now(UTC)
    return assessment_id


def finalize_run(session: Session, run_id: uuid.UUID) -> None:
    now = datetime.now(UTC)
    with session.begin():
        run = session.get(PolicyAnalysisRun, run_id, with_for_update=True)
        if run is None:
            raise PolicyAnalysisRunNotFoundError(str(run_id))
        if run.assessment_id is None:
            raise WorkflowStateError("completed run requires an assessment")
        _terminalize(run, status="completed", now=now)


def fail_run_from_exception(session: Session, run_id: uuid.UUID, detail: str) -> None:
    session.rollback()
    now = datetime.now(UTC)
    with session.begin():
        run = session.get(PolicyAnalysisRun, run_id, with_for_update=True)
        if run is None or run.status in {"completed", "unsupported", "failed"}:
            return
        failure_code = (
            "assessment_creation_failed"
            if run.current_step in {"create_assessment", "finalize"}
            else "workflow_state_invalid"
        )
        _terminalize(
            run,
            status="failed",
            now=now,
            failure_code=failure_code,
            failure_detail=detail,
        )


def _terminalize(
    run: PolicyAnalysisRun,
    *,
    status: str,
    now: datetime,
    failure_code: str | None = None,
    failure_detail: str | None = None,
) -> None:
    run.status = status
    run.current_step = "terminal"
    run.failure_code = failure_code
    run.failure_detail = failure_detail
    run.updated_at = now
    run.completed_at = now
