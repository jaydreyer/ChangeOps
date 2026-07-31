from collections.abc import Iterable

from changeops.domain.types import (
    AnalysisResult,
    FindingResult,
    PolicyInput,
    ProposedActionResult,
    TrainingInput,
    TripInput,
    WorkerAnalysis,
    WorkerInput,
)

ANALYZER_VERSION = "international-travel-v1"


def analyze_policy(
    policy: PolicyInput,
    workers: Iterable[WorkerInput],
    trips: Iterable[TripInput],
    training_records: Iterable[TrainingInput],
) -> AnalysisResult:
    worker_by_id = {worker.id: worker for worker in workers}
    training_by_worker_and_course = {
        (record.worker_id, record.course_identifier): record for record in training_records
    }

    worker_results: list[WorkerAnalysis] = []
    findings: list[FindingResult] = []
    proposed_actions: list[ProposedActionResult] = []

    for trip in sorted(trips, key=lambda item: (item.worker_id, item.id)):
        worker = worker_by_id[trip.worker_id]
        exclusion = _exclusion(worker, trip, policy)
        if exclusion is not None:
            reason_code, explanation = exclusion
            worker_results.append(
                WorkerAnalysis(
                    worker_id=worker.id,
                    trip_id=trip.id,
                    classification="unaffected",
                    explanation=explanation,
                    reason_codes=(reason_code,),
                )
            )
            continue

        course_id = policy.rules.security_training.course_identifier
        training = training_by_worker_and_course.get((worker.id, course_id))
        training_complete = training is not None and training.completion_status == "completed"
        approval_required = trip.booking_date is None or trip.booking_date >= policy.effective_date

        reason_codes = [
            "WORKER_IN_SCOPE",
            "DESTINATION_IN_SCOPE",
            "DEPARTURE_ON_OR_AFTER_EFFECTIVE_DATE",
            "MANAGER_APPROVAL_REQUIRED" if approval_required else "BOOKING_DATE_EXCEPTION",
            "TRAINING_ALREADY_COMPLETED" if training_complete else "TRAINING_REQUIRED",
        ]
        worker_results.append(
            WorkerAnalysis(
                worker_id=worker.id,
                trip_id=trip.id,
                classification="affected",
                explanation=_affected_explanation(
                    worker,
                    trip,
                    policy,
                    approval_required=approval_required,
                    training_complete=training_complete,
                ),
                reason_codes=tuple(reason_codes),
            )
        )

        if approval_required:
            finding = _manager_approval_finding(worker, trip, policy)
            findings.append(finding)
            proposed_actions.append(
                ProposedActionResult(
                    key=f"{worker.id}:obtain_manager_approval",
                    finding_key=finding.key,
                    worker_id=worker.id,
                    action_type="manager_approval_request",
                    target_type="manager",
                    target_identifier=worker.manager_name,
                    description=(
                        "Obtain documented manager approval before any nonrefundable "
                        "travel is booked."
                    ),
                    due_date=None,
                )
            )
        else:
            findings.append(_booking_exception_finding(worker, trip, policy))

        if training_complete:
            findings.append(_training_complete_finding(worker, training, policy))
        else:
            finding = _training_required_finding(worker, trip, training, policy)
            findings.append(finding)
            proposed_actions.append(
                ProposedActionResult(
                    key=f"{worker.id}:assign_security_training",
                    finding_key=finding.key,
                    worker_id=worker.id,
                    action_type="training_assignment",
                    target_type="worker",
                    target_identifier=worker.id,
                    description=(
                        "Assign the International Travel Security course and require "
                        f"completion before {trip.departure_date.isoformat()}."
                    ),
                    due_date=trip.departure_date,
                )
            )

    return AnalysisResult(
        worker_results=tuple(sorted(worker_results, key=lambda item: item.worker_id)),
        findings=tuple(sorted(findings, key=lambda item: item.key)),
        proposed_actions=tuple(sorted(proposed_actions, key=lambda item: item.key)),
    )


def _exclusion(
    worker: WorkerInput,
    trip: TripInput,
    policy: PolicyInput,
) -> tuple[str, str] | None:
    rules = policy.rules
    if worker.assigned_work_country != rules.worker_scope.assigned_work_country:
        return (
            "WORK_COUNTRY_OUT_OF_SCOPE",
            f"{worker.full_name} is assigned to {worker.assigned_work_country}, "
            f"not {rules.worker_scope.assigned_work_country}, and is outside the policy scope.",
        )
    if worker.worker_type not in rules.worker_scope.worker_types:
        return (
            "WORKER_TYPE_OUT_OF_SCOPE",
            f"{worker.full_name}'s worker type is outside the policy scope.",
        )
    if trip.origin_country != rules.trip_scope.origin_country:
        return (
            "ORIGIN_OUT_OF_SCOPE",
            f"{worker.full_name}'s trip does not originate in {rules.trip_scope.origin_country}.",
        )
    if trip.destination_country in rules.trip_scope.excluded_destination_countries:
        return (
            "DESTINATION_EXCLUDED",
            f"{worker.full_name}'s destination, {trip.destination_country}, "
            "is explicitly excluded from the policy.",
        )
    if trip.departure_date < policy.effective_date:
        return (
            "DEPARTURE_BEFORE_EFFECTIVE_DATE",
            f"{worker.full_name}'s departure occurs before the policy effective date.",
        )
    return None


def _affected_explanation(
    worker: WorkerInput,
    trip: TripInput,
    policy: PolicyInput,
    *,
    approval_required: bool,
    training_complete: bool,
) -> str:
    approval = (
        "manager approval is required"
        if approval_required
        else "the pre-effective-date booking exception applies"
    )
    training = (
        "the security training is already complete"
        if training_complete
        else "security training is required"
    )
    return (
        f"{worker.full_name} is a covered {worker.worker_type} traveling to "
        f"{trip.destination_country} on or after {policy.effective_date.isoformat()}; "
        f"{approval}, and {training}."
    )


def _manager_approval_finding(
    worker: WorkerInput,
    trip: TripInput,
    policy: PolicyInput,
) -> FindingResult:
    return FindingResult(
        key=f"{worker.id}:manager_approval_required",
        worker_id=worker.id,
        finding_type="manager_approval_required",
        severity="action_required",
        rule_code="MANAGER_APPROVAL_REQUIRED",
        explanation=(
            f"{worker.full_name}'s planned trip to {trip.destination_country} is covered "
            "by the policy, so manager approval is required before a nonrefundable booking."
        ),
        evidence_keys=(
            f"worker:{worker.id}",
            f"trip:{trip.id}",
            f"policy:{policy.id}:worker_scope",
            f"policy:{policy.id}:destination_scope",
            f"policy:{policy.id}:effective_date",
            f"policy:{policy.id}:manager_approval",
        ),
    )


def _booking_exception_finding(
    worker: WorkerInput,
    trip: TripInput,
    policy: PolicyInput,
) -> FindingResult:
    return FindingResult(
        key=f"{worker.id}:manager_approval_exempt",
        worker_id=worker.id,
        finding_type="manager_approval_exempt",
        severity="informational",
        rule_code="BOOKING_DATE_EXCEPTION",
        explanation=(
            f"{worker.full_name}'s trip was booked before {policy.effective_date.isoformat()} "
            "and is exempt from the new manager-approval requirement."
        ),
        evidence_keys=(
            f"trip:{trip.id}",
            f"policy:{policy.id}:effective_date",
            f"policy:{policy.id}:booking_exception",
        ),
    )


def _training_required_finding(
    worker: WorkerInput,
    trip: TripInput,
    training: TrainingInput | None,
    policy: PolicyInput,
) -> FindingResult:
    evidence_keys = [
        f"worker:{worker.id}",
        f"trip:{trip.id}",
        f"policy:{policy.id}:effective_date",
        f"policy:{policy.id}:security_training",
    ]
    if training is not None:
        evidence_keys.append(f"training:{training.id}")
    return FindingResult(
        key=f"{worker.id}:training_required",
        worker_id=worker.id,
        finding_type="security_training_required",
        severity="action_required",
        rule_code="TRAINING_REQUIRED",
        explanation=(
            f"{worker.full_name} departs after the policy effective date and has not "
            "completed the International Travel Security course."
        ),
        evidence_keys=tuple(evidence_keys),
    )


def _training_complete_finding(
    worker: WorkerInput,
    training: TrainingInput,
    policy: PolicyInput,
) -> FindingResult:
    return FindingResult(
        key=f"{worker.id}:training_complete",
        worker_id=worker.id,
        finding_type="security_training_complete",
        severity="informational",
        rule_code="TRAINING_ALREADY_COMPLETED",
        explanation=(
            f"{worker.full_name} has already completed the International Travel "
            "Security course; no duplicate assignment is needed."
        ),
        evidence_keys=(
            f"training:{training.id}",
            f"policy:{policy.id}:security_training",
        ),
    )
