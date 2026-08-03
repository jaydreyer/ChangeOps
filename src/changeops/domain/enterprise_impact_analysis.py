from collections import defaultdict
from collections.abc import Iterable

from changeops.domain.types import (
    AnalysisResult,
    CommitmentAssignmentInput,
    EnterpriseAnalysisResult,
    EnterpriseContextInput,
    EnterpriseImpactResult,
    EnterpriseProposedActionResult,
    ImpactClassification,
    ImpactDomain,
    PolicyInput,
    RelationshipPathElementResult,
    TrainingInput,
    TripInput,
    WorkerAnalysis,
    WorkerInput,
)

DOMAIN_ORDER: dict[ImpactDomain, str] = {
    "people": "01",
    "teams": "02",
    "systems": "03",
    "documents": "04",
    "training": "05",
    "customer_commitments": "06",
}


def analyze_enterprise_impacts(
    policy: PolicyInput,
    workers: Iterable[WorkerInput],
    trips: Iterable[TripInput],
    training_records: Iterable[TrainingInput],
    context: EnterpriseContextInput,
    worker_analysis: AnalysisResult,
) -> EnterpriseAnalysisResult:
    workers_by_id = {item.id: item for item in workers}
    trips_by_id = {item.id: item for item in trips}
    training_by_worker_course = {
        (item.worker_id, item.course_identifier): item for item in training_records
    }
    affected_results = tuple(
        sorted(
            (item for item in worker_analysis.worker_results if item.classification == "affected"),
            key=lambda item: (item.worker_id, item.trip_id),
        )
    )

    impacts: dict[str, EnterpriseImpactResult] = {}
    actions: dict[str, EnterpriseProposedActionResult] = {}

    _add_worker_impacts(
        impacts,
        policy,
        affected_results,
        workers_by_id,
        trips_by_id,
    )
    _add_manager_impacts(
        impacts,
        policy,
        affected_results,
        workers_by_id,
    )
    _add_team_impacts(impacts, actions, policy, affected_results, workers_by_id, context)
    _add_system_impacts(impacts, actions, policy, affected_results, context)
    _add_document_impacts(impacts, actions, policy, context)
    _add_training_impacts(
        impacts,
        policy,
        affected_results,
        workers_by_id,
        trips_by_id,
        training_by_worker_course,
        context,
    )
    _add_commitment_impacts(
        impacts,
        actions,
        policy,
        affected_results,
        workers_by_id,
        trips_by_id,
        context,
    )

    return EnterpriseAnalysisResult(
        impacts=tuple(sorted(impacts.values(), key=lambda item: item.sort_key)),
        proposed_actions=tuple(sorted(actions.values(), key=lambda item: item.key)),
    )


def _add_worker_impacts(
    impacts: dict[str, EnterpriseImpactResult],
    policy: PolicyInput,
    affected_results: tuple[WorkerAnalysis, ...],
    workers_by_id: dict[str, WorkerInput],
    trips_by_id: dict[str, TripInput],
) -> None:
    for result in affected_results:
        worker = workers_by_id[result.worker_id]
        trip = trips_by_id[result.trip_id]
        key = f"people:worker:{worker.id}"
        impacts[key] = _impact(
            key=key,
            domain="people",
            object_type="worker",
            source_key=worker.id,
            display_name=worker.full_name,
            classification="directly_affected",
            explanation=(
                f"{worker.full_name} is directly affected because trip {trip.id} is covered "
                "by the policy change."
            ),
            reason_code="WORKER_DIRECTLY_AFFECTED",
            evidence_keys=(
                f"worker:{worker.id}",
                f"trip:{trip.id}",
                f"policy:{policy.id}:worker_scope",
                f"policy:{policy.id}:destination_scope",
                f"policy:{policy.id}:effective_date",
            ),
            path=(
                _path("policy_change", policy.id, policy.title, "applies_to"),
                _path("trip", trip.id, _trip_label(trip), "assigned_to"),
                _path("worker", worker.id, worker.full_name, None),
            ),
        )


def _add_manager_impacts(
    impacts: dict[str, EnterpriseImpactResult],
    policy: PolicyInput,
    affected_results: tuple[WorkerAnalysis, ...],
    workers_by_id: dict[str, WorkerInput],
) -> None:
    results_by_manager: dict[str, list[WorkerAnalysis]] = defaultdict(list)
    for result in affected_results:
        if not {
            "MANAGER_APPROVAL_REQUIRED",
            "BOOKING_DATE_EXCEPTION",
        }.intersection(result.reason_codes):
            continue
        worker = workers_by_id[result.worker_id]
        if worker.manager_worker_id is not None:
            results_by_manager[worker.manager_worker_id].append(result)

    for manager_id, results in sorted(results_by_manager.items()):
        manager = workers_by_id[manager_id]
        first = sorted(results, key=lambda item: (item.worker_id, item.trip_id))[0]
        worker = workers_by_id[first.worker_id]
        affected_names = sorted(workers_by_id[item.worker_id].full_name for item in results)
        key = f"people:manager:{manager.id}"
        impacts[key] = _impact(
            key=key,
            domain="people",
            object_type="manager",
            source_key=manager.id,
            display_name=manager.full_name,
            classification="operationally_affected",
            explanation=(
                f"{manager.full_name} is operationally affected because connected worker"
                f"{'s' if len(results) > 1 else ''} {', '.join(affected_names)} "
                f"{'require' if len(results) > 1 else 'requires'}"
                " approval or booking-exception review."
            ),
            reason_code="WORKER_MANAGER_APPROVAL_REQUIRED",
            evidence_keys=tuple(
                sorted(
                    {
                        f"worker:{manager.id}",
                        f"policy:{policy.id}:manager_approval",
                        *(f"worker:{item.worker_id}" for item in results),
                        *(f"trip:{item.trip_id}" for item in results),
                    }
                )
            ),
            path=(
                _path("policy_change", policy.id, policy.title, "contains_rule"),
                _path(
                    "policy_rule",
                    f"{policy.id}:manager_approval",
                    "Manager approval rule",
                    "applies_to",
                ),
                _path("worker", worker.id, worker.full_name, "managed_by"),
                _path("manager", manager.id, manager.full_name, None),
            ),
        )


def _add_team_impacts(
    impacts: dict[str, EnterpriseImpactResult],
    actions: dict[str, EnterpriseProposedActionResult],
    policy: PolicyInput,
    affected_results: tuple[WorkerAnalysis, ...],
    workers_by_id: dict[str, WorkerInput],
    context: EnterpriseContextInput,
) -> None:
    teams_by_id = {item.id: item for item in context.teams}
    membership_by_worker_id = {item.worker_id: item for item in context.team_memberships}
    results_by_team: dict[str, list[WorkerAnalysis]] = defaultdict(list)
    for result in affected_results:
        team_id = workers_by_id[result.worker_id].team_id
        if team_id is not None and team_id in teams_by_id:
            results_by_team[team_id].append(result)

    for team_id, results in sorted(results_by_team.items()):
        team = teams_by_id[team_id]
        workers = sorted(
            (workers_by_id[item.worker_id] for item in results),
            key=lambda item: item.id,
        )
        first = workers[0]
        key = f"teams:team:{team.id}"
        impacts[key] = _impact(
            key=key,
            domain="teams",
            object_type="team",
            source_key=team.id,
            display_name=team.name,
            classification="operationally_affected",
            explanation=(
                f"{team.name} is operationally affected because it contains "
                f"{len(workers)} directly affected worker{'s' if len(workers) != 1 else ''}."
            ),
            reason_code="TEAM_HAS_AFFECTED_WORKERS",
            evidence_keys=tuple(
                sorted(
                    {
                        f"team:{team.id}",
                        *(f"worker:{worker.id}" for worker in workers),
                        *(
                            f"team_membership:{membership_by_worker_id[worker.id].id}"
                            for worker in workers
                        ),
                    }
                )
            ),
            path=(
                _path("policy_change", policy.id, policy.title, "affects"),
                _path("worker", first.id, first.full_name, "member_of"),
                _path("team", team.id, team.name, None),
            ),
        )
        action_key = f"{key}:review_team_travel"
        actions[action_key] = _action(
            key=action_key,
            impact_key=key,
            action_type="review_team_travel",
            target_type="team",
            target_identifier=team.id,
            description=f"Review travel readiness for affected workers on {team.name}.",
        )


def _add_system_impacts(
    impacts: dict[str, EnterpriseImpactResult],
    actions: dict[str, EnterpriseProposedActionResult],
    policy: PolicyInput,
    affected_results: tuple[WorkerAnalysis, ...],
    context: EnterpriseContextInput,
) -> None:
    systems_by_id = {item.id: item for item in context.systems}
    all_reason_codes = {code for item in affected_results for code in item.reason_codes}
    for dependency in sorted(context.system_dependencies, key=lambda item: item.id):
        system = systems_by_id[dependency.system_id]
        if not system.active:
            continue
        if dependency.rule_code == "MANAGER_APPROVAL_REQUIRED":
            applies = bool(
                {"MANAGER_APPROVAL_REQUIRED", "BOOKING_DATE_EXCEPTION"} & all_reason_codes
            )
            reason_code = "SYSTEM_SUPPORTS_CHANGED_APPROVAL_PROCESS"
        elif dependency.rule_code == "TRAINING_REQUIRED":
            applies = bool(affected_results)
            reason_code = "SYSTEM_SUPPORTS_TRAINING_REQUIREMENT"
        else:
            applies = False
            reason_code = "SYSTEM_DEPENDENCY_APPLIES"
        if not applies:
            continue

        key = f"systems:enterprise_system:{system.id}"
        impacts[key] = _impact(
            key=key,
            domain="systems",
            object_type="enterprise_system",
            source_key=system.id,
            display_name=system.name,
            classification="operationally_affected",
            explanation=f"{system.name} is operationally affected. {dependency.explanation}",
            reason_code=reason_code,
            evidence_keys=(
                f"policy:{policy.id}:{_policy_rule_suffix(dependency.rule_code)}",
                f"system:{system.id}",
                f"policy_system_dependency:{dependency.id}",
            ),
            path=(
                _path("policy_change", policy.id, policy.title, "contains_rule"),
                _path(
                    "policy_rule",
                    f"{policy.id}:{dependency.rule_code}",
                    dependency.rule_code,
                    dependency.relationship_type,
                ),
                _path("enterprise_system", system.id, system.name, None),
            ),
        )
        action_key = f"{key}:review_system_workflow"
        actions[action_key] = _action(
            key=action_key,
            impact_key=key,
            action_type="review_system_workflow",
            target_type="enterprise_system",
            target_identifier=system.id,
            description=f"Review the {system.name} workflow for the changed policy rule.",
        )


def _add_document_impacts(
    impacts: dict[str, EnterpriseImpactResult],
    actions: dict[str, EnterpriseProposedActionResult],
    policy: PolicyInput,
    context: EnterpriseContextInput,
) -> None:
    documents_by_id = {item.id: item for item in context.documents}
    for dependency in sorted(context.document_dependencies, key=lambda item: item.id):
        document = documents_by_id[dependency.document_id]
        key = f"documents:enterprise_document:{document.id}"
        reason_code = (
            "DOCUMENT_CONTAINS_CHANGED_POLICY"
            if dependency.relationship_type == "contains_changed_policy"
            else "DOCUMENT_REFERENCES_CHANGED_POLICY"
        )
        impacts[key] = _impact(
            key=key,
            domain="documents",
            object_type="enterprise_document",
            source_key=document.id,
            display_name=document.title,
            classification=dependency.impact_classification,
            explanation=dependency.explanation,
            reason_code=reason_code,
            evidence_keys=(
                f"document:{document.id}",
                f"policy_document_dependency:{dependency.id}",
                f"policy:{policy.id}:{_policy_rule_suffix(dependency.rule_code)}",
            ),
            path=(
                _path("policy_change", policy.id, policy.title, "contains_rule"),
                _path(
                    "policy_rule",
                    f"{policy.id}:{dependency.rule_code}",
                    dependency.rule_code,
                    dependency.relationship_type,
                ),
                _path("enterprise_document", document.id, document.title, None),
            ),
        )
        action_key = f"{key}:update_document"
        action_type = (
            "operational_remediation"
            if dependency.relationship_type == "contains_changed_policy"
            else "update_document"
            if dependency.impact_classification == "update_required"
            else "review_document"
        )
        actions[action_key] = _action(
            key=action_key,
            impact_key=key,
            action_type=action_type,
            target_type="enterprise_document",
            target_identifier=document.id,
            description=(
                f"Apply the approved policy remediation to {document.title}."
                if action_type == "operational_remediation"
                else f"{action_type.replace('_', ' ').capitalize()}: {document.title}."
            ),
        )


def _add_training_impacts(
    impacts: dict[str, EnterpriseImpactResult],
    policy: PolicyInput,
    affected_results: tuple[WorkerAnalysis, ...],
    workers_by_id: dict[str, WorkerInput],
    trips_by_id: dict[str, TripInput],
    training_by_worker_course: dict[tuple[str, str], TrainingInput],
    context: EnterpriseContextInput,
) -> None:
    courses_by_id = {item.id: item for item in context.courses}
    for dependency in sorted(context.training_dependencies, key=lambda item: item.id):
        course = courses_by_id[dependency.course_id]
        if not course.active or course.id != policy.rules.security_training.course_identifier:
            continue
        key = f"training:training_course:{course.id}"
        impacts[key] = _impact(
            key=key,
            domain="training",
            object_type="training_course",
            source_key=course.id,
            display_name=course.name,
            classification="operationally_affected",
            explanation=f"{course.name} is required by the changed policy.",
            reason_code="TRAINING_REQUIRED_BY_POLICY",
            evidence_keys=(
                f"course:{course.id}",
                f"policy_training_dependency:{dependency.id}",
                f"policy:{policy.id}:security_training",
            ),
            path=(
                _path("policy_change", policy.id, policy.title, "contains_rule"),
                _path(
                    "policy_rule",
                    f"{policy.id}:security_training",
                    "Security training rule",
                    dependency.relationship_type,
                ),
                _path("training_course", course.id, course.name, None),
            ),
        )

        for result in affected_results:
            worker = workers_by_id[result.worker_id]
            trip = trips_by_id[result.trip_id]
            record = training_by_worker_course.get((worker.id, course.id))
            if record is not None and record.completion_status == "completed":
                continue
            issue_key = f"training:worker_training_requirement:{worker.id}:{course.id}"
            evidence_keys = {
                f"worker:{worker.id}",
                f"trip:{trip.id}",
                f"course:{course.id}",
                f"policy_training_dependency:{dependency.id}",
                f"policy:{policy.id}:security_training",
            }
            if record is not None:
                evidence_keys.add(f"training:{record.id}")
            impacts[issue_key] = _impact(
                key=issue_key,
                domain="training",
                object_type="worker_training_requirement",
                source_key=f"{worker.id}:{course.id}",
                display_name=f"{worker.full_name} — {course.name}",
                classification="notification_required",
                explanation=(
                    f"{worker.full_name} lacks a completed {course.name} record for "
                    f"affected trip {trip.id}."
                ),
                reason_code="WORKER_TRAINING_INCOMPLETE",
                evidence_keys=tuple(sorted(evidence_keys)),
                path=(
                    _path("policy_change", policy.id, policy.title, "contains_rule"),
                    _path(
                        "policy_rule",
                        f"{policy.id}:security_training",
                        "Security training rule",
                        "applies_to",
                    ),
                    _path("worker", worker.id, worker.full_name, "requires"),
                    _path("training_course", course.id, course.name, None),
                ),
            )


def _add_commitment_impacts(
    impacts: dict[str, EnterpriseImpactResult],
    actions: dict[str, EnterpriseProposedActionResult],
    policy: PolicyInput,
    affected_results: tuple[WorkerAnalysis, ...],
    workers_by_id: dict[str, WorkerInput],
    trips_by_id: dict[str, TripInput],
    context: EnterpriseContextInput,
) -> None:
    affected_by_worker: dict[str, list[WorkerAnalysis]] = defaultdict(list)
    for result in affected_results:
        affected_by_worker[result.worker_id].append(result)
    commitments_by_id = {item.id: item for item in context.commitments}
    qualifying: dict[str, list[tuple[CommitmentAssignmentInput, WorkerAnalysis]]] = defaultdict(
        list
    )
    for assignment in sorted(context.commitment_assignments, key=lambda item: item.id):
        commitment = commitments_by_id[assignment.commitment_id]
        if not assignment.required or commitment.status != "active":
            continue
        for result in affected_by_worker.get(assignment.worker_id, []):
            trip = trips_by_id[result.trip_id]
            if commitment.start_date <= trip.departure_date <= commitment.end_date:
                qualifying[commitment.id].append((assignment, result))

    for commitment_id, matches in sorted(qualifying.items()):
        commitment = commitments_by_id[commitment_id]
        assignment, result = sorted(
            matches,
            key=lambda item: (item[0].id, item[1].trip_id),
        )[0]
        worker = workers_by_id[result.worker_id]
        trip = trips_by_id[result.trip_id]
        key = f"customer_commitments:customer_commitment:{commitment.id}"
        impacts[key] = _impact(
            key=key,
            domain="customer_commitments",
            object_type="customer_commitment",
            source_key=commitment.id,
            display_name=f"{commitment.customer_name} — {commitment.commitment_type}",
            classification="review_required",
            explanation=(
                f"{commitment.customer_name}'s {commitment.commitment_type} requires "
                f"{worker.full_name}, and trip {trip.id} departs within the commitment period."
            ),
            reason_code="CUSTOMER_COMMITMENT_OVERLAPS_AFFECTED_TRAVEL",
            evidence_keys=(
                f"commitment:{commitment.id}",
                f"commitment_assignment:{assignment.id}",
                f"worker:{worker.id}",
                f"trip:{trip.id}",
            ),
            path=(
                _path("policy_change", policy.id, policy.title, "affects"),
                _path("trip", trip.id, _trip_label(trip), "assigned_to"),
                _path("worker", worker.id, worker.full_name, "assigned_to"),
                _path(
                    "customer_commitment",
                    commitment.id,
                    commitment.customer_name,
                    None,
                ),
            ),
        )
        action_key = f"{key}:review_customer_commitment"
        actions[action_key] = _action(
            key=action_key,
            impact_key=key,
            action_type="review_customer_commitment",
            target_type="customer_commitment",
            target_identifier=commitment.id,
            description=(
                f"Review {commitment.customer_name}'s commitment for the affected travel."
            ),
            worker_id=worker.id,
        )


def _impact(
    *,
    key: str,
    domain: ImpactDomain,
    object_type: str,
    source_key: str,
    display_name: str,
    classification: ImpactClassification,
    explanation: str,
    reason_code: str,
    evidence_keys: tuple[str, ...],
    path: tuple[RelationshipPathElementResult, ...],
) -> EnterpriseImpactResult:
    return EnterpriseImpactResult(
        key=key,
        domain=domain,
        object_type=object_type,
        source_key=source_key,
        display_name=display_name,
        classification=classification,
        explanation=explanation,
        reason_code=reason_code,
        evidence_keys=tuple(sorted(set(evidence_keys))),
        relationship_path=path,
        sort_key=f"{DOMAIN_ORDER[domain]}:{object_type}:{source_key}:{reason_code}",
    )


def _action(
    *,
    key: str,
    impact_key: str,
    action_type: str,
    target_type: str,
    target_identifier: str,
    description: str,
    worker_id: str | None = None,
) -> EnterpriseProposedActionResult:
    return EnterpriseProposedActionResult(
        key=key,
        impact_key=impact_key,
        action_type=action_type,
        target_type=target_type,
        target_identifier=target_identifier,
        description=description,
        worker_id=worker_id,
    )


def _path(
    object_type: str,
    stable_key: str,
    display_label: str,
    relationship_to_next: str | None,
) -> RelationshipPathElementResult:
    return RelationshipPathElementResult(
        object_type=object_type,
        stable_key=stable_key,
        display_label=display_label,
        relationship_to_next=relationship_to_next,
    )


def _trip_label(trip: TripInput) -> str:
    return (
        f"{trip.origin_country} to {trip.destination_country} on {trip.departure_date.isoformat()}"
    )


def _policy_rule_suffix(rule_code: str) -> str:
    return {
        "MANAGER_APPROVAL_REQUIRED": "manager_approval",
        "TRAINING_REQUIRED": "security_training",
        "POLICY_CHANGE": "effective_date",
    }.get(rule_code, "effective_date")
