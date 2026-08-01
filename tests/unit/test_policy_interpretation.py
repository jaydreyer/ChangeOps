import uuid
from datetime import date

import pytest

from changeops.ai.policy_interpreter import _resolve_candidate_references
from changeops.domain.policy_interpretation import (
    CandidateChangePlan,
    CandidateCoverageGapFinding,
    ChangePlanValidationError,
    EvidenceReference,
    ImpactReference,
    InterpretationEvidence,
    InterpretationFinding,
    InterpretationImpact,
    PolicyInterpretationInput,
    PolicySpanReference,
)
from changeops.domain.policy_interpretation_validation import validate_candidate_change_plan

ASSESSMENT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
IMPACT_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")


def interpretation_input() -> PolicyInterpretationInput:
    return PolicyInterpretationInput(
        policy_change_id="policy-1",
        policy_text="Employees must complete security training.",
        policy_effective_date=date(2026, 9, 1),
        policy_analysis_run_id=uuid.UUID("00000000-0000-0000-0000-000000000003"),
        accepted_extraction_attempt_id=uuid.UUID("00000000-0000-0000-0000-000000000004"),
        accepted_rules={"kind": "international_travel"},
        accepted_source_provenance=(),
        answered_clarifications=(),
        impact_assessment_id=ASSESSMENT_ID,
        assessment_summary={"enterprise_impacts": 1},
        impacts=(
            InterpretationImpact(
                id=IMPACT_ID,
                assessment_id=ASSESSMENT_ID,
                domain="training",
                object_type="training_course",
                source_key="course-1",
                display_name="Security",
                classification="operationally_affected",
                explanation="Mapped course.",
                reason_code="required_course",
                evidence_keys=("policy:text",),
                relationship_path=({"sequence": 0},),
            ),
        ),
        findings=(),
        evidence=(
            InterpretationEvidence(
                id=uuid.uuid4(),
                evidence_key="policy:text",
                evidence_type="policy",
                source_type="policy_change",
                source_id="policy-1",
                label="Policy",
                snapshot={},
            ),
        ),
        proposed_actions=(),
        unresolved_questions=(),
        prompt_version="coverage-gap-interpretation-v1",
        schema_version="policy-interpretation-v1",
    )


def finding(**changes) -> CandidateCoverageGapFinding:
    quote = "security training"
    text = interpretation_input().policy_text
    values = {
        "finding_key": "review-training-mapping",
        "title": "Review mapping coverage",
        "observed_limitation": "Only the supplied mapping was evaluated.",
        "why_it_matters": "Other governed material may require review.",
        "recommended_review_action": "Review policy-to-course mapping completeness.",
        "policy_spans": (
            PolicySpanReference(
                policy_change_id="policy-1",
                start=text.index(quote),
                end=text.index(quote) + len(quote),
                quote=quote,
            ),
        ),
        "impact_references": (ImpactReference(assessment_id=ASSESSMENT_ID, impact_id=IMPACT_ID),),
        "evidence_references": (
            EvidenceReference(
                assessment_id=ASSESSMENT_ID,
                evidence_key="policy:text",
                impact_id=IMPACT_ID,
            ),
        ),
    }
    values.update(changes)
    return CandidateCoverageGapFinding(**values)


def test_grounded_plan_and_empty_plan_are_accepted() -> None:
    validated = validate_candidate_change_plan(
        CandidateChangePlan(summary="Review concern.", coverage_gaps=(finding(),)),
        interpretation_input(),
    )
    empty = validate_candidate_change_plan(
        CandidateChangePlan(summary="No grounded gaps.", coverage_gaps=()),
        interpretation_input(),
    )
    assert validated.schema_version == "policy-interpretation-v1"
    assert empty.coverage_gaps == ()


def test_interpreter_resolves_mechanical_evidence_owner_errors() -> None:
    finding_id = uuid.UUID("00000000-0000-0000-0000-000000000005")
    wrong_finding_id = uuid.UUID("00000000-0000-0000-0000-000000000006")
    input_with_finding = interpretation_input().model_copy(
        update={
            "findings": (
                InterpretationFinding(
                    id=finding_id,
                    rule_code="TRAINING_REVIEW",
                    finding_type="review",
                    severity="warning",
                    explanation="Review training timing.",
                    evidence_keys=("policy:text", "trip:trip-1"),
                ),
            ),
            "evidence": (
                *interpretation_input().evidence,
                InterpretationEvidence(
                    id=uuid.uuid4(),
                    evidence_key="trip:trip-1",
                    evidence_type="trip",
                    source_type="trip",
                    source_id="trip-1",
                    label="Trip",
                    snapshot={},
                ),
            ),
        }
    )
    candidate = CandidateChangePlan(
        summary="Grounded concern.",
        coverage_gaps=(
            finding(
                evidence_references=(
                    EvidenceReference(
                        assessment_id=ASSESSMENT_ID,
                        evidence_key="policy:text",
                        impact_id=IMPACT_ID,
                        finding_id=finding_id,
                    ),
                    EvidenceReference(
                        assessment_id=ASSESSMENT_ID,
                        evidence_key="trip:trip-1",
                        finding_id=wrong_finding_id,
                    ),
                )
            ),
        ),
    )

    resolved = _resolve_candidate_references(candidate, input_with_finding)
    references = resolved.coverage_gaps[0].evidence_references

    assert references[0].impact_id == IMPACT_ID
    assert references[0].finding_id is None
    assert references[1].impact_id is None
    assert references[1].finding_id == finding_id
    validate_candidate_change_plan(resolved, input_with_finding)


def test_interpreter_leaves_invented_evidence_owners_invalid() -> None:
    unresolved = CandidateChangePlan(
        summary="Unsupported concern.",
        coverage_gaps=(
            finding(
                evidence_references=(
                    EvidenceReference(
                        assessment_id=ASSESSMENT_ID,
                        evidence_key="invented",
                        finding_id=uuid.uuid4(),
                    ),
                )
            ),
        ),
    )

    resolved = _resolve_candidate_references(unresolved, interpretation_input())

    with pytest.raises(ChangePlanValidationError) as captured:
        validate_candidate_change_plan(resolved, interpretation_input())
    assert "invalid_evidence_reference" in {item.code for item in captured.value.issues}


@pytest.mark.parametrize(
    ("change", "code"),
    [
        (
            {
                "impact_references": (
                    ImpactReference(assessment_id=ASSESSMENT_ID, impact_id=uuid.uuid4()),
                )
            },
            "invalid_impact_reference",
        ),
        (
            {
                "evidence_references": (
                    EvidenceReference(assessment_id=ASSESSMENT_ID, evidence_key="invented"),
                )
            },
            "invalid_evidence_reference",
        ),
        (
            {
                "policy_spans": (
                    PolicySpanReference(policy_change_id="policy-1", start=0, end=4, quote="wrong"),
                )
            },
            "policy_quote_mismatch",
        ),
    ],
)
def test_invalid_grounding_is_rejected(change, code) -> None:
    with pytest.raises(ChangePlanValidationError) as captured:
        validate_candidate_change_plan(
            CandidateChangePlan(summary="", coverage_gaps=(finding(**change),)),
            interpretation_input(),
        )
    assert code in {item.code for item in captured.value.issues}


def test_duplicate_normalized_finding_keys_are_rejected() -> None:
    duplicate = finding(finding_key="review-training-mapping")
    with pytest.raises(ChangePlanValidationError) as captured:
        validate_candidate_change_plan(
            CandidateChangePlan(summary="", coverage_gaps=(finding(), duplicate)),
            interpretation_input(),
        )
    assert "duplicate_finding_key" in {item.code for item in captured.value.issues}
