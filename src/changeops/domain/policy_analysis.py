from dataclasses import dataclass
from typing import Literal

from changeops.domain.policy_extraction import ValidationIssue

RunStatus = Literal[
    "pending",
    "running",
    "awaiting_clarification",
    "completed",
    "unsupported",
    "failed",
]
RunStep = Literal[
    "initialize",
    "extract",
    "evaluate_extraction",
    "evaluate_clarification",
    "await_clarification",
    "create_assessment",
    "finalize",
    "terminal",
]
FailureCode = Literal[
    "provider_not_configured",
    "provider_invocation_failed",
    "structured_output_invalid",
    "extraction_validation_failed",
    "enterprise_reference_unresolved",
    "clarification_answer_invalid",
    "clarification_state_conflict",
    "retry_limit_exhausted",
    "assessment_creation_failed",
    "workflow_state_invalid",
]
ExtractionRoute = Literal["accepted", "unsupported", "clarify", "retry", "fail"]

WORKFLOW_VERSION = "policy-analysis-v1"
MAX_TECHNICAL_RETRIES = 1
BOOKING_EXCEPTION_QUESTION_CODE = "booking_before_effective_date_exemption"
BOOKING_EXCEPTION_FIELD = "candidate_rules.manager_approval.booking_before_effective_date_is_exempt"


@dataclass(frozen=True)
class ExtractionDecision:
    route: ExtractionRoute
    failure_code: FailureCode | None = None
    detail: str | None = None
    retry_reason: str | None = None
    question_code: str | None = None


def decide_extraction_outcome(
    *,
    validation_outcome: str,
    issues: tuple[ValidationIssue, ...],
    retry_count: int,
) -> ExtractionDecision:
    if validation_outcome == "accepted":
        return ExtractionDecision(route="accepted")
    if validation_outcome == "unsupported":
        return ExtractionDecision(route="unsupported")

    codes = {issue.code for issue in issues}
    if codes == {"unsupported_exception_behavior"}:
        return ExtractionDecision(
            route="clarify",
            question_code=BOOKING_EXCEPTION_QUESTION_CODE,
        )
    if codes & {"training_course_not_found", "training_course_name_ambiguous"}:
        return ExtractionDecision(
            route="fail",
            failure_code="enterprise_reference_unresolved",
            detail="The required training course did not resolve to one active enterprise course.",
        )
    if "structured_output_failure" in codes:
        detail = next(
            issue.message for issue in issues if issue.code == "structured_output_failure"
        )
        retry_reason = (
            "provider_invocation_failed"
            if detail.startswith("model_invocation_failed:")
            else "structured_output_invalid"
        )
        if retry_count < MAX_TECHNICAL_RETRIES:
            return ExtractionDecision(
                route="retry",
                retry_reason=retry_reason,
                detail=detail,
            )
        return ExtractionDecision(
            route="fail",
            failure_code="retry_limit_exhausted",
            detail=detail,
        )
    return ExtractionDecision(
        route="fail",
        failure_code="extraction_validation_failed",
        detail=", ".join(sorted(codes)) or "Extraction validation failed.",
    )
