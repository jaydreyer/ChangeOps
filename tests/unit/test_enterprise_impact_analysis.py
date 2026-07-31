from dataclasses import replace
from datetime import date

from changeops.domain.enterprise_impact_analysis import analyze_enterprise_impacts
from changeops.domain.fingerprinting import calculate_input_fingerprint
from changeops.domain.impact_analysis import analyze_policy
from changeops.domain.types import (
    CommitmentAssignmentInput,
    CustomerCommitmentInput,
    EnterpriseContextInput,
    EnterpriseDocumentInput,
    EnterpriseSystemInput,
    InternationalTravelPolicyRules,
    PolicyDocumentDependencyInput,
    PolicyInput,
    PolicySystemDependencyInput,
    PolicyTrainingDependencyInput,
    QuestionInput,
    TeamInput,
    TeamMembershipInput,
    TrainingCourseInput,
    TrainingInput,
    TripInput,
    WorkerInput,
)


def make_policy() -> PolicyInput:
    rules = InternationalTravelPolicyRules.model_validate(
        {
            "kind": "international_travel",
            "schema_version": 1,
            "worker_scope": {
                "assigned_work_country": "US",
                "worker_types": ["employee", "contractor"],
            },
            "trip_scope": {
                "origin_country": "US",
                "excluded_destination_countries": ["US", "CA"],
            },
            "manager_approval": {
                "booking_before_effective_date_is_exempt": True,
            },
            "security_training": {
                "course_identifier": "course-security",
            },
        }
    )
    return PolicyInput(
        id="policy-travel",
        title="International Travel",
        version="1",
        effective_date=date(2026, 9, 1),
        policy_text="Policy text",
        rules=rules,
    )


def make_inputs() -> tuple[
    list[WorkerInput],
    list[TripInput],
    list[TrainingInput],
    EnterpriseContextInput,
]:
    workers = [
        WorkerInput(
            id="manager-anita",
            full_name="Anita Manager",
            worker_type="employee",
            department="Technology",
            manager_name="Executive",
            assigned_work_country="US",
        ),
        WorkerInput(
            id="manager-mike",
            full_name="Mike Manager",
            worker_type="employee",
            department="People",
            manager_name="Executive",
            assigned_work_country="US",
        ),
        WorkerInput(
            id="worker-marcus",
            full_name="Marcus Worker",
            worker_type="contractor",
            department="Technology",
            manager_name="Anita Manager",
            assigned_work_country="US",
            manager_worker_id="manager-anita",
            team_id="team-technology",
        ),
        WorkerInput(
            id="worker-priya",
            full_name="Priya Worker",
            worker_type="employee",
            department="Domestic",
            manager_name="Domestic Manager",
            assigned_work_country="US",
            team_id="team-domestic",
        ),
        WorkerInput(
            id="worker-sarah",
            full_name="Sarah Worker",
            worker_type="employee",
            department="People",
            manager_name="Mike Manager",
            assigned_work_country="US",
            manager_worker_id="manager-mike",
            team_id="team-people",
        ),
    ]
    trips = [
        TripInput(
            id="trip-marcus",
            worker_id="worker-marcus",
            origin_country="US",
            destination_country="JP",
            departure_date=date(2026, 10, 2),
            booking_date=None,
            booking_status="planned",
        ),
        TripInput(
            id="trip-priya",
            worker_id="worker-priya",
            origin_country="US",
            destination_country="CA",
            departure_date=date(2026, 9, 18),
            booking_date=None,
            booking_status="planned",
        ),
        TripInput(
            id="trip-sarah",
            worker_id="worker-sarah",
            origin_country="US",
            destination_country="FR",
            departure_date=date(2026, 9, 15),
            booking_date=None,
            booking_status="planned",
        ),
    ]
    training = [
        TrainingInput(
            id="training-marcus",
            worker_id="worker-marcus",
            course_identifier="course-security",
            completion_status="completed",
            completion_date=date(2026, 1, 1),
        ),
        TrainingInput(
            id="training-sarah",
            worker_id="worker-sarah",
            course_identifier="course-security",
            completion_status="not_completed",
            completion_date=None,
        ),
    ]
    context = EnterpriseContextInput(
        teams=(
            TeamInput("team-domestic", "Domestic Team", "manager-mike"),
            TeamInput("team-people", "People Team", "manager-mike"),
            TeamInput("team-technology", "Technology Team", "manager-anita"),
        ),
        team_memberships=(
            TeamMembershipInput(
                "membership-marcus",
                "worker-marcus",
                "team-technology",
            ),
            TeamMembershipInput(
                "membership-priya",
                "worker-priya",
                "team-domestic",
            ),
            TeamMembershipInput(
                "membership-sarah",
                "worker-sarah",
                "team-people",
            ),
        ),
        systems=(
            EnterpriseSystemInput(
                "system-expense",
                "Expense",
                "expense",
                "Expense reporting.",
                True,
            ),
            EnterpriseSystemInput(
                "system-learning",
                "Learning",
                "learning",
                "Training records.",
                True,
            ),
            EnterpriseSystemInput(
                "system-travel",
                "Travel",
                "travel",
                "Travel approvals.",
                True,
            ),
        ),
        documents=(
            EnterpriseDocumentInput(
                "document-expense",
                "Expense Guide",
                "guide",
                "Knowledge",
                "1",
                "published",
            ),
            EnterpriseDocumentInput(
                "document-travel",
                "Travel Guide",
                "guide",
                "Knowledge",
                "1",
                "published",
            ),
        ),
        courses=(
            TrainingCourseInput(
                "course-security",
                "SEC-100",
                "Travel Security",
                True,
            ),
        ),
        system_dependencies=(
            PolicySystemDependencyInput(
                "dependency-learning",
                "TRAINING_REQUIRED",
                "system-learning",
                "verifies_training_completion",
                "The learning system verifies training.",
            ),
            PolicySystemDependencyInput(
                "dependency-travel",
                "MANAGER_APPROVAL_REQUIRED",
                "system-travel",
                "supports_approval_workflow",
                "The travel system supports approvals.",
            ),
        ),
        document_dependencies=(
            PolicyDocumentDependencyInput(
                "dependency-document-travel",
                "MANAGER_APPROVAL_REQUIRED",
                "document-travel",
                "explains_changed_process",
                "update_required",
                "The travel guide explains the changed approval process.",
            ),
        ),
        training_dependencies=(
            PolicyTrainingDependencyInput(
                "dependency-course",
                "TRAINING_REQUIRED",
                "course-security",
                "requires_course",
                "The policy requires the course.",
            ),
        ),
        commitments=(
            CustomerCommitmentInput(
                "commitment-overlap",
                "Northwind",
                "onsite_delivery",
                "On-site delivery.",
                date(2026, 9, 14),
                date(2026, 9, 18),
                "active",
            ),
            CustomerCommitmentInput(
                "commitment-no-overlap",
                "Contoso",
                "launch",
                "Remote launch.",
                date(2026, 10, 10),
                date(2026, 10, 12),
                "active",
            ),
        ),
        commitment_assignments=(
            CommitmentAssignmentInput(
                "assignment-contoso",
                "commitment-no-overlap",
                "worker-marcus",
                "technical_lead",
                True,
            ),
            CommitmentAssignmentInput(
                "assignment-northwind",
                "commitment-overlap",
                "worker-sarah",
                "workshop_lead",
                True,
            ),
        ),
        questions=(QuestionInput("question-1", 1, "How long is training valid?"),),
    )
    return workers, trips, training, context


def analyze(
    *,
    context_override: EnterpriseContextInput | None = None,
) -> tuple:
    workers, trips, training, context = make_inputs()
    policy = make_policy()
    worker_result = analyze_policy(policy, workers, trips, training)
    enterprise_result = analyze_enterprise_impacts(
        policy,
        workers,
        trips,
        training,
        context_override or context,
        worker_result,
    )
    return enterprise_result.impacts, enterprise_result.proposed_actions


def test_each_domain_uses_explicit_positive_and_negative_rules() -> None:
    impacts, actions = analyze()
    by_domain: dict[str, list] = {}
    for impact in impacts:
        by_domain.setdefault(impact.domain, []).append(impact)

    assert {item.source_key for item in by_domain["people"]} == {
        "manager-anita",
        "manager-mike",
        "worker-marcus",
        "worker-sarah",
    }
    assert {item.source_key for item in by_domain["teams"]} == {
        "team-people",
        "team-technology",
    }
    assert {item.source_key for item in by_domain["systems"]} == {
        "system-learning",
        "system-travel",
    }
    assert {item.source_key for item in by_domain["documents"]} == {"document-travel"}
    assert {item.source_key for item in by_domain["training"]} == {
        "course-security",
        "worker-sarah:course-security",
    }
    assert {item.source_key for item in by_domain["customer_commitments"]} == {"commitment-overlap"}
    assert "system-expense" not in {item.source_key for item in impacts}
    assert "document-expense" not in {item.source_key for item in impacts}
    assert "team-domestic" not in {item.source_key for item in impacts}
    assert "commitment-no-overlap" not in {item.source_key for item in impacts}
    assert all(action.execution_status == "not_executed" for action in actions)
    assert {
        "review_team_travel",
        "review_system_workflow",
        "update_document",
        "review_customer_commitment",
    } <= {action.action_type for action in actions}


def test_reason_codes_paths_duplicate_prevention_and_ordering_are_stable() -> None:
    impacts, _ = analyze()

    assert [item.sort_key for item in impacts] == sorted(item.sort_key for item in impacts)
    assert len({item.key for item in impacts}) == len(impacts)
    assert all(item.reason_code.isupper() for item in impacts)
    assert all(item.evidence_keys for item in impacts)
    assert all(item.relationship_path for item in impacts)
    assert all(item.relationship_path[-1].relationship_to_next is None for item in impacts)

    commitment = next(item for item in impacts if item.domain == "customer_commitments")
    assert [element.object_type for element in commitment.relationship_path] == [
        "policy_change",
        "trip",
        "worker",
        "customer_commitment",
    ]


def test_duplicate_dependency_does_not_duplicate_impact_or_action() -> None:
    _, _, _, context = make_inputs()
    duplicate = replace(
        context.document_dependencies[0],
        id="dependency-document-travel-duplicate",
    )
    impacts, actions = analyze(
        context_override=replace(
            context,
            document_dependencies=(*context.document_dependencies, duplicate),
        )
    )

    assert sum(item.source_key == "document-travel" for item in impacts) == 1
    assert (
        sum(
            item.target_identifier == "document-travel" and item.action_type == "update_document"
            for item in actions
        )
        == 1
    )


def test_customer_commitment_date_overlap_is_inclusive_and_required() -> None:
    _, _, _, context = make_inputs()
    commitment = context.commitments[0]

    boundary_context = replace(
        context,
        commitments=(
            replace(
                commitment,
                start_date=date(2026, 9, 15),
                end_date=date(2026, 9, 15),
            ),
            context.commitments[1],
        ),
    )
    impacts, _ = analyze(context_override=boundary_context)
    assert "commitment-overlap" in {item.source_key for item in impacts}

    no_overlap_context = replace(
        boundary_context,
        commitments=(
            replace(commitment, end_date=date(2026, 9, 14)),
            context.commitments[1],
        ),
    )
    impacts, _ = analyze(context_override=no_overlap_context)
    assert "commitment-overlap" not in {item.source_key for item in impacts}

    optional_context = replace(
        context,
        commitment_assignments=(
            replace(context.commitment_assignments[1], required=False),
            context.commitment_assignments[0],
        ),
    )
    impacts, _ = analyze(context_override=optional_context)
    assert "commitment-overlap" not in {item.source_key for item in impacts}


def test_input_order_does_not_change_enterprise_result() -> None:
    workers, trips, training, context = make_inputs()
    policy = make_policy()
    forward_worker_result = analyze_policy(policy, workers, trips, training)
    forward = analyze_enterprise_impacts(
        policy,
        workers,
        trips,
        training,
        context,
        forward_worker_result,
    )
    reverse_context = replace(
        context,
        teams=tuple(reversed(context.teams)),
        team_memberships=tuple(reversed(context.team_memberships)),
        systems=tuple(reversed(context.systems)),
        documents=tuple(reversed(context.documents)),
        courses=tuple(reversed(context.courses)),
        system_dependencies=tuple(reversed(context.system_dependencies)),
        document_dependencies=tuple(reversed(context.document_dependencies)),
        training_dependencies=tuple(reversed(context.training_dependencies)),
        commitments=tuple(reversed(context.commitments)),
        commitment_assignments=tuple(reversed(context.commitment_assignments)),
        questions=tuple(reversed(context.questions)),
    )
    reversed_workers = list(reversed(workers))
    reversed_trips = list(reversed(trips))
    reversed_training = list(reversed(training))
    reverse_worker_result = analyze_policy(
        policy,
        reversed_workers,
        reversed_trips,
        reversed_training,
    )
    reverse = analyze_enterprise_impacts(
        policy,
        reversed_workers,
        reversed_trips,
        reversed_training,
        reverse_context,
        reverse_worker_result,
    )

    assert reverse == forward


def test_fingerprint_is_canonical_and_changes_for_relevant_input() -> None:
    workers, trips, training, context = make_inputs()
    policy = make_policy()
    forward = calculate_input_fingerprint(
        analyzer_version="enterprise-impact-v1",
        policy=policy,
        workers=workers,
        trips=trips,
        training_records=training,
        context=context,
    )
    reverse = calculate_input_fingerprint(
        analyzer_version="enterprise-impact-v1",
        policy=policy,
        workers=list(reversed(workers)),
        trips=list(reversed(trips)),
        training_records=list(reversed(training)),
        context=replace(
            context,
            teams=tuple(reversed(context.teams)),
            team_memberships=tuple(reversed(context.team_memberships)),
            systems=tuple(reversed(context.systems)),
            documents=tuple(reversed(context.documents)),
            commitment_assignments=tuple(reversed(context.commitment_assignments)),
        ),
    )
    changed = calculate_input_fingerprint(
        analyzer_version="enterprise-impact-v1",
        policy=policy,
        workers=workers,
        trips=trips,
        training_records=training,
        context=replace(
            context,
            documents=(
                replace(context.documents[0], version="2"),
                context.documents[1],
            ),
        ),
    )

    assert reverse == forward
    assert changed != forward
