from datetime import date

from changeops.domain.policy_extraction import (
    CandidateInternationalTravelPolicyRules,
    ExtractionValidationResult,
    PolicyExtractionProposal,
    TrainingCourseReference,
    ValidationIssue,
)
from changeops.domain.types import InternationalTravelPolicyRules

MATERIAL_FIELD_PATHS = frozenset(
    {
        "policy_family",
        "candidate_rules.kind",
        "candidate_rules.schema_version",
        "candidate_rules.effective_date",
        "candidate_rules.worker_scope.assigned_work_country",
        "candidate_rules.worker_scope.worker_types",
        "candidate_rules.trip_scope.origin_country",
        "candidate_rules.trip_scope.excluded_destination_countries",
        "candidate_rules.manager_approval.booking_before_effective_date_is_exempt",
        "candidate_rules.security_training.course_name",
    }
)

SUPPORTED_WORKER_TYPES = frozenset({"employee", "contractor"})


def validate_policy_extraction(
    proposal: PolicyExtractionProposal,
    *,
    policy_text: str,
    policy_effective_date: date,
    training_courses: tuple[TrainingCourseReference, ...],
) -> ExtractionValidationResult:
    issues = _validate_provenance(proposal, policy_text)
    if issues:
        return _failed(*issues)

    if proposal.policy_family != "international_travel":
        return ExtractionValidationResult(
            outcome="unsupported",
            accepted_rules=None,
            issues=(
                ValidationIssue(
                    code="unsupported_policy_family",
                    field_path="policy_family",
                    message=(
                        f"Policy family {proposal.policy_family!r} is outside the supported scope."
                    ),
                ),
            ),
        )

    if proposal.support_status == "unsupported":
        unsupported_findings = tuple(
            ValidationIssue(
                code=finding.code,
                field_path=finding.field_path,
                message=finding.message,
            )
            for finding in proposal.findings
            if finding.kind == "unsupported"
        )
        if not unsupported_findings:
            return _failed(
                ValidationIssue(
                    code="unsupported_finding_required",
                    message="An unsupported outcome must explain the unsupported construct.",
                )
            )
        return ExtractionValidationResult(
            outcome="unsupported",
            accepted_rules=None,
            issues=unsupported_findings,
        )

    if proposal.candidate_rules is None:
        return _failed(
            ValidationIssue(
                code="candidate_rules_required",
                field_path="candidate_rules",
                message="Supported extraction output must include candidate rules.",
            )
        )

    unresolved = tuple(finding for finding in proposal.findings if finding.kind == "unresolved")
    unsupported = tuple(finding for finding in proposal.findings if finding.kind == "unsupported")
    if unresolved or unsupported:
        return _failed(
            *(
                ValidationIssue(
                    code=finding.code,
                    field_path=finding.field_path,
                    message=finding.message,
                )
                for finding in (*unresolved, *unsupported)
            )
        )

    rules = proposal.candidate_rules
    business_issues = _validate_business_rules(rules, policy_effective_date)
    if business_issues:
        return _failed(*business_issues)

    course_identifier, resolution_issue = _resolve_course_identifier(
        rules.security_training.course_name,
        training_courses,
    )
    if resolution_issue is not None:
        return _failed(resolution_issue)

    accepted_rules = InternationalTravelPolicyRules.model_validate(
        {
            "kind": rules.kind,
            "schema_version": rules.schema_version,
            "worker_scope": rules.worker_scope.model_dump(mode="json"),
            "trip_scope": rules.trip_scope.model_dump(mode="json"),
            "manager_approval": rules.manager_approval.model_dump(mode="json"),
            "security_training": {"course_identifier": course_identifier},
        }
    )
    return ExtractionValidationResult(
        outcome="accepted",
        accepted_rules=accepted_rules,
        issues=(),
    )


def _validate_provenance(
    proposal: PolicyExtractionProposal,
    policy_text: str,
) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    seen_paths: set[str] = set()

    for entry in proposal.provenance:
        if entry.end > len(policy_text) or policy_text[entry.start : entry.end] != entry.quote:
            issues.append(
                ValidationIssue(
                    code="invalid_provenance_span",
                    field_path=entry.field_path,
                    message="The provenance span does not resolve exactly against the policy text.",
                )
            )
        if entry.field_path in seen_paths:
            issues.append(
                ValidationIssue(
                    code="duplicate_provenance",
                    field_path=entry.field_path,
                    message="Each material field must have exactly one provenance span.",
                )
            )
        seen_paths.add(entry.field_path)

    for finding in proposal.findings:
        entry = finding.provenance
        if entry.end > len(policy_text) or policy_text[entry.start : entry.end] != entry.quote:
            issues.append(
                ValidationIssue(
                    code="invalid_provenance_span",
                    field_path=entry.field_path,
                    message="The finding provenance does not resolve against the policy text.",
                )
            )

    required_paths = (
        MATERIAL_FIELD_PATHS
        if proposal.candidate_rules is not None
        else frozenset({"policy_family"})
    )
    for field_path in sorted(required_paths - seen_paths):
        issues.append(
            ValidationIssue(
                code="missing_provenance",
                field_path=field_path,
                message="The material extracted field has no source provenance.",
            )
        )
    for field_path in sorted(seen_paths - MATERIAL_FIELD_PATHS):
        issues.append(
            ValidationIssue(
                code="unknown_provenance_field",
                field_path=field_path,
                message="The provenance field path is not part of the extraction schema.",
            )
        )
    return tuple(issues)


def _validate_business_rules(
    rules: CandidateInternationalTravelPolicyRules,
    policy_effective_date: date,
) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    worker_types = rules.worker_scope.worker_types
    if not worker_types:
        issues.append(
            ValidationIssue(
                code="empty_worker_scope",
                field_path="candidate_rules.worker_scope.worker_types",
                message="At least one worker type is required.",
            )
        )
    if len(set(worker_types)) != len(worker_types):
        issues.append(
            ValidationIssue(
                code="duplicate_worker_type",
                field_path="candidate_rules.worker_scope.worker_types",
                message="Worker types must be unique.",
            )
        )
    if set(worker_types) - SUPPORTED_WORKER_TYPES:
        issues.append(
            ValidationIssue(
                code="unsupported_worker_type",
                field_path="candidate_rules.worker_scope.worker_types",
                message="The current schema supports only employee and contractor worker types.",
            )
        )

    country_fields = [
        (
            "candidate_rules.worker_scope.assigned_work_country",
            rules.worker_scope.assigned_work_country,
        ),
        ("candidate_rules.trip_scope.origin_country", rules.trip_scope.origin_country),
        *[
            ("candidate_rules.trip_scope.excluded_destination_countries", country)
            for country in rules.trip_scope.excluded_destination_countries
        ],
    ]
    for field_path, country in country_fields:
        if len(country) != 2 or not country.isalpha() or country != country.upper():
            issues.append(
                ValidationIssue(
                    code="invalid_country_code",
                    field_path=field_path,
                    message="Country codes must be two uppercase letters.",
                )
            )

    excluded = rules.trip_scope.excluded_destination_countries
    if len(set(excluded)) != len(excluded):
        issues.append(
            ValidationIssue(
                code="duplicate_excluded_country",
                field_path="candidate_rules.trip_scope.excluded_destination_countries",
                message="Excluded destination countries must be unique.",
            )
        )
    if rules.worker_scope.assigned_work_country != rules.trip_scope.origin_country:
        issues.append(
            ValidationIssue(
                code="inconsistent_country_scope",
                field_path="candidate_rules.trip_scope.origin_country",
                message="Worker and trip origin country scopes must match in schema version 1.",
            )
        )
    if rules.effective_date != policy_effective_date:
        issues.append(
            ValidationIssue(
                code="effective_date_mismatch",
                field_path="candidate_rules.effective_date",
                message=(
                    "The extracted effective date does not match the stored policy effective date."
                ),
            )
        )
    if not rules.manager_approval.booking_before_effective_date_is_exempt:
        issues.append(
            ValidationIssue(
                code="unsupported_exception_behavior",
                field_path=(
                    "candidate_rules.manager_approval.booking_before_effective_date_is_exempt"
                ),
                message="Schema version 1 requires pre-effective-date bookings to be exempt.",
            )
        )
    return tuple(issues)


def _resolve_course_identifier(
    course_name: str,
    training_courses: tuple[TrainingCourseReference, ...],
) -> tuple[str, ValidationIssue | None]:
    normalized_name = " ".join(course_name.split()).casefold()
    matches = [
        course
        for course in training_courses
        if course.active and " ".join(course.name.split()).casefold() == normalized_name
    ]
    if len(matches) != 1:
        code = "training_course_not_found" if not matches else "training_course_name_ambiguous"
        return "", ValidationIssue(
            code=code,
            field_path="candidate_rules.security_training.course_name",
            message=(
                "The training-course name must resolve to exactly one active enterprise course."
            ),
        )
    return matches[0].identifier, None


def _failed(*issues: ValidationIssue) -> ExtractionValidationResult:
    return ExtractionValidationResult(
        outcome="validation_failed",
        accepted_rules=None,
        issues=tuple(issues),
    )
