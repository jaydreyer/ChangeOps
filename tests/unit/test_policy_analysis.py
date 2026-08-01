from changeops.domain.policy_analysis import decide_extraction_outcome
from changeops.domain.policy_extraction import ValidationIssue


def issue(code: str, message: str = "detail") -> ValidationIssue:
    return ValidationIssue(code=code, message=message)


def test_material_exception_conflict_requires_bounded_clarification() -> None:
    decision = decide_extraction_outcome(
        validation_outcome="validation_failed",
        issues=(issue("unsupported_exception_behavior"),),
        retry_count=0,
    )

    assert decision.route == "clarify"
    assert decision.question_code == "booking_before_effective_date_exemption"


def test_enterprise_reference_failure_is_not_retried() -> None:
    decision = decide_extraction_outcome(
        validation_outcome="validation_failed",
        issues=(issue("training_course_not_found"),),
        retry_count=0,
    )

    assert decision.route == "fail"
    assert decision.failure_code == "enterprise_reference_unresolved"


def test_structured_output_retry_is_bounded() -> None:
    first = decide_extraction_outcome(
        validation_outcome="validation_failed",
        issues=(issue("structured_output_failure", "structured_output_parsing_failed: bad"),),
        retry_count=0,
    )
    exhausted = decide_extraction_outcome(
        validation_outcome="validation_failed",
        issues=(issue("structured_output_failure", "structured_output_parsing_failed: bad"),),
        retry_count=1,
    )

    assert first.route == "retry"
    assert first.retry_reason == "structured_output_invalid"
    assert exhausted.route == "fail"
    assert exhausted.failure_code == "retry_limit_exhausted"
