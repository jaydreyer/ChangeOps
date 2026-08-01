import re

from changeops.domain.policy_interpretation import (
    CandidateChangePlan,
    ChangePlanValidationError,
    InterpretationValidationIssue,
    PolicyInterpretationInput,
    ValidatedChangePlan,
)

_KEY_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def validate_candidate_change_plan(
    candidate: CandidateChangePlan,
    interpretation_input: PolicyInterpretationInput,
) -> ValidatedChangePlan:
    issues: list[InterpretationValidationIssue] = []
    impact_by_id = {item.id: item for item in interpretation_input.impacts}
    finding_by_id = {item.id: item for item in interpretation_input.findings}
    evidence_by_key = {item.evidence_key: item for item in interpretation_input.evidence}
    normalized_keys: set[str] = set()

    for finding in candidate.coverage_gaps:
        normalized = finding.finding_key.strip().lower().replace("_", "-")
        if not _KEY_PATTERN.fullmatch(finding.finding_key):
            issues.append(
                _issue("invalid_finding_key", "Finding key is not normalized.", finding.finding_key)
            )
        if normalized in normalized_keys:
            issues.append(
                _issue("duplicate_finding_key", "Finding keys must be unique.", finding.finding_key)
            )
        normalized_keys.add(normalized)

        for span in finding.policy_spans:
            if span.policy_change_id != interpretation_input.policy_change_id:
                issues.append(
                    _issue(
                        "invalid_policy_reference",
                        "Policy reference is not for this policy.",
                        finding.finding_key,
                    )
                )
            elif span.end <= span.start or span.end > len(interpretation_input.policy_text):
                issues.append(
                    _issue(
                        "invalid_policy_span",
                        "Policy span is outside the persisted text.",
                        finding.finding_key,
                    )
                )
            elif interpretation_input.policy_text[span.start : span.end] != span.quote:
                issues.append(
                    _issue(
                        "policy_quote_mismatch",
                        "Policy quote does not resolve exactly.",
                        finding.finding_key,
                    )
                )

        cited_impact_ids = {item.impact_id for item in finding.impact_references}
        for reference in finding.impact_references:
            if reference.assessment_id != interpretation_input.impact_assessment_id:
                issues.append(
                    _issue(
                        "wrong_assessment_reference",
                        "Impact reference uses another assessment.",
                        finding.finding_key,
                    )
                )
            elif reference.impact_id not in impact_by_id:
                issues.append(
                    _issue(
                        "invalid_impact_reference",
                        "Impact reference does not resolve.",
                        finding.finding_key,
                    )
                )

        for reference in finding.evidence_references:
            if reference.assessment_id != interpretation_input.impact_assessment_id:
                issues.append(
                    _issue(
                        "wrong_assessment_reference",
                        "Evidence reference uses another assessment.",
                        finding.finding_key,
                    )
                )
                continue
            evidence = evidence_by_key.get(reference.evidence_key)
            if evidence is None:
                issues.append(
                    _issue(
                        "invalid_evidence_reference",
                        "Evidence key does not resolve.",
                        finding.finding_key,
                    )
                )
                continue
            if reference.impact_id is not None and reference.finding_id is not None:
                issues.append(
                    _issue(
                        "ambiguous_evidence_owner",
                        "Evidence must cite exactly one owning impact or finding.",
                        finding.finding_key,
                    )
                )
                continue
            if reference.impact_id is not None:
                impact = impact_by_id.get(reference.impact_id)
                if impact is None or reference.evidence_key not in impact.evidence_keys:
                    issues.append(
                        _issue(
                            "invalid_evidence_ownership",
                            "Evidence does not belong to the cited impact.",
                            finding.finding_key,
                        )
                    )
                if reference.impact_id not in cited_impact_ids:
                    issues.append(
                        _issue(
                            "uncited_evidence_impact",
                            "Evidence impact must also be cited.",
                            finding.finding_key,
                        )
                    )
            elif reference.finding_id is not None:
                owner_finding = finding_by_id.get(reference.finding_id)
                if (
                    owner_finding is None
                    or reference.evidence_key not in owner_finding.evidence_keys
                ):
                    issues.append(
                        _issue(
                            "invalid_evidence_ownership",
                            "Evidence does not belong to the cited finding.",
                            finding.finding_key,
                        )
                    )
            else:
                issues.append(
                    _issue(
                        "missing_evidence_owner",
                        "Evidence must cite its owning impact or finding.",
                        finding.finding_key,
                    )
                )

        for reference in finding.relationship_path_references:
            impact = impact_by_id.get(reference.impact_id)
            if reference.assessment_id != interpretation_input.impact_assessment_id:
                issues.append(
                    _issue(
                        "wrong_assessment_reference",
                        "Path reference uses another assessment.",
                        finding.finding_key,
                    )
                )
            elif impact is None or reference.sequence >= len(impact.relationship_path):
                issues.append(
                    _issue(
                        "invalid_relationship_path",
                        "Relationship path element does not resolve.",
                        finding.finding_key,
                    )
                )

    if issues:
        raise ChangePlanValidationError(tuple(issues))
    return ValidatedChangePlan(**candidate.model_dump())


def _issue(code: str, message: str, finding_key: str) -> InterpretationValidationIssue:
    return InterpretationValidationIssue(code=code, message=message, finding_key=finding_key)
