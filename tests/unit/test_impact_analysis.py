from datetime import date

import pytest
from pydantic import ValidationError

from changeops.domain.impact_analysis import analyze_policy
from changeops.domain.types import (
    InternationalTravelPolicyRules,
    PolicyInput,
    TrainingInput,
    TripInput,
    WorkerInput,
)


def make_rules() -> InternationalTravelPolicyRules:
    return InternationalTravelPolicyRules.model_validate(
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
                "course_identifier": "international-travel-security",
            },
        }
    )


def make_policy() -> PolicyInput:
    return PolicyInput(
        id="policy-travel",
        title="International Travel",
        version="1",
        effective_date=date(2026, 9, 1),
        policy_text="Policy text",
        rules=make_rules(),
    )


def make_worker(
    worker_id: str,
    name: str,
    *,
    worker_type: str = "employee",
    country: str = "US",
    manager: str = "Manager",
) -> WorkerInput:
    return WorkerInput(
        id=worker_id,
        full_name=name,
        worker_type=worker_type,
        department="Operations",
        manager_name=manager,
        assigned_work_country=country,
    )


def make_trip(
    worker_id: str,
    destination: str,
    departure: date,
    *,
    origin: str = "US",
    booking: date | None = None,
) -> TripInput:
    return TripInput(
        id=f"trip-{worker_id}",
        worker_id=worker_id,
        origin_country=origin,
        destination_country=destination,
        departure_date=departure,
        booking_date=booking,
        booking_status="booked" if booking else "planned",
    )


def make_training(worker_id: str, *, completed: bool) -> TrainingInput:
    return TrainingInput(
        id=f"training-{worker_id}",
        worker_id=worker_id,
        course_identifier="international-travel-security",
        completion_status="completed" if completed else "not_completed",
        completion_date=None,
    )


def golden_inputs() -> tuple[list[WorkerInput], list[TripInput], list[TrainingInput]]:
    workers = [
        make_worker(
            "worker-sarah-johnson",
            "Sarah Johnson",
            manager="Mike Wilson",
        ),
        make_worker(
            "worker-marcus-lee",
            "Marcus Lee",
            worker_type="contractor",
            manager="Anita Patel",
        ),
        make_worker("worker-elena-garcia", "Elena García", country="ES"),
        make_worker("worker-david-miller", "David Miller"),
        make_worker("worker-priya-shah", "Priya Shah"),
        make_worker("worker-thomas-green", "Thomas Green"),
    ]
    trips = [
        make_trip(
            "worker-sarah-johnson",
            "FR",
            date(2026, 9, 15),
        ),
        make_trip(
            "worker-marcus-lee",
            "JP",
            date(2026, 10, 2),
        ),
        make_trip(
            "worker-elena-garcia",
            "US",
            date(2026, 9, 20),
            origin="ES",
            booking=date(2026, 8, 25),
        ),
        make_trip(
            "worker-david-miller",
            "DE",
            date(2026, 9, 10),
            booking=date(2026, 8, 20),
        ),
        make_trip(
            "worker-priya-shah",
            "CA",
            date(2026, 9, 18),
        ),
        make_trip(
            "worker-thomas-green",
            "MX",
            date(2026, 8, 20),
            booking=date(2026, 8, 1),
        ),
    ]
    training = [
        make_training(worker.id, completed=worker.id == "worker-marcus-lee") for worker in workers
    ]
    return workers, trips, training


def test_golden_scenario_classifications_findings_and_actions() -> None:
    workers, trips, training = golden_inputs()

    result = analyze_policy(make_policy(), workers, trips, training)

    classifications = {item.worker_id: item.classification for item in result.worker_results}
    assert classifications == {
        "worker-david-miller": "affected",
        "worker-elena-garcia": "unaffected",
        "worker-marcus-lee": "affected",
        "worker-priya-shah": "unaffected",
        "worker-sarah-johnson": "affected",
        "worker-thomas-green": "unaffected",
    }
    assert len(result.findings) == 6
    assert {finding.rule_code for finding in result.findings} == {
        "BOOKING_DATE_EXCEPTION",
        "MANAGER_APPROVAL_REQUIRED",
        "TRAINING_ALREADY_COMPLETED",
        "TRAINING_REQUIRED",
    }
    assert [action.key for action in result.proposed_actions] == [
        "worker-david-miller:assign_security_training",
        "worker-marcus-lee:obtain_manager_approval",
        "worker-sarah-johnson:assign_security_training",
        "worker-sarah-johnson:obtain_manager_approval",
    ]
    assert all(action.execution_status == "not_executed" for action in result.proposed_actions)


def test_golden_scenario_exclusion_reasons() -> None:
    workers, trips, training = golden_inputs()

    result = analyze_policy(make_policy(), workers, trips, training)

    reasons = {item.worker_id: item.reason_codes for item in result.worker_results}
    assert reasons["worker-elena-garcia"] == ("WORK_COUNTRY_OUT_OF_SCOPE",)
    assert reasons["worker-priya-shah"] == ("DESTINATION_EXCLUDED",)
    assert reasons["worker-thomas-green"] == ("DEPARTURE_BEFORE_EFFECTIVE_DATE",)


@pytest.mark.parametrize(
    ("departure", "booking", "approval_expected"),
    [
        (date(2026, 9, 1), None, True),
        (date(2026, 9, 1), date(2026, 9, 1), True),
        (date(2026, 9, 1), date(2026, 8, 31), False),
    ],
)
def test_effective_and_booking_date_boundaries(
    departure: date,
    booking: date | None,
    approval_expected: bool,
) -> None:
    worker = make_worker("worker-boundary", "Boundary Worker")
    trip = make_trip("worker-boundary", "FR", departure, booking=booking)

    result = analyze_policy(
        make_policy(),
        [worker],
        [trip],
        [make_training(worker.id, completed=False)],
    )

    finding_types = {finding.finding_type for finding in result.findings}
    assert ("manager_approval_required" in finding_types) is approval_expected
    assert ("manager_approval_exempt" in finding_types) is not approval_expected
    assert "security_training_required" in finding_types


@pytest.mark.parametrize(
    ("worker", "trip", "reason"),
    [
        (
            make_worker("worker-type", "Worker Type", worker_type="vendor"),
            make_trip("worker-type", "FR", date(2026, 9, 2)),
            "WORKER_TYPE_OUT_OF_SCOPE",
        ),
        (
            make_worker("worker-origin", "Worker Origin"),
            make_trip(
                "worker-origin",
                "FR",
                date(2026, 9, 2),
                origin="GB",
            ),
            "ORIGIN_OUT_OF_SCOPE",
        ),
    ],
)
def test_additional_scope_exclusions(
    worker: WorkerInput,
    trip: TripInput,
    reason: str,
) -> None:
    result = analyze_policy(make_policy(), [worker], [trip], [])

    assert result.worker_results[0].classification == "unaffected"
    assert result.worker_results[0].reason_codes == (reason,)
    assert result.findings == ()
    assert result.proposed_actions == ()


def test_input_order_does_not_change_result_order() -> None:
    workers, trips, training = golden_inputs()

    forward = analyze_policy(make_policy(), workers, trips, training)
    reverse = analyze_policy(
        make_policy(),
        reversed(workers),
        reversed(trips),
        reversed(training),
    )

    assert forward == reverse


def test_structured_rules_reject_unknown_or_invalid_fields() -> None:
    invalid_rules = make_rules().model_dump()
    invalid_rules["worker_scope"]["assigned_work_country"] = "usa"
    invalid_rules["unexpected"] = True

    with pytest.raises(ValidationError):
        InternationalTravelPolicyRules.model_validate(invalid_rules)
