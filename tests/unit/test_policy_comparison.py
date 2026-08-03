import uuid
from datetime import date

import pytest

from changeops.domain.policy_comparison import (
    PolicyComparisonSource,
    calculate_policy_comparison_fingerprint,
    compare_international_travel_policies,
)
from changeops.domain.types import (
    InternationalTravelPolicyRules,
    ManagerApprovalRules,
)

ATTEMPT_1 = uuid.UUID("00000000-0000-0000-0000-000000000101")
ATTEMPT_2 = uuid.UUID("00000000-0000-0000-0000-000000000102")


def _rules(**updates) -> InternationalTravelPolicyRules:
    payload = {
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
        "security_training": {"course_identifier": "travel-security"},
    }
    for key, value in updates.items():
        section, field = key.split("__", 1)
        payload[section][field] = value
    return InternationalTravelPolicyRules.model_validate(payload)


def _provenance(prefix: str = "source") -> dict[str, dict]:
    paths = (
        "candidate_rules.effective_date",
        "candidate_rules.worker_scope.assigned_work_country",
        "candidate_rules.worker_scope.worker_types",
        "candidate_rules.trip_scope.origin_country",
        "candidate_rules.trip_scope.excluded_destination_countries",
        "candidate_rules.manager_approval.booking_before_effective_date_is_exempt",
        "candidate_rules.security_training.course_name",
    )
    return {
        path: {
            "source": "policy_text",
            "field_path": path,
            "start": index,
            "end": index + 1,
            "quote": f"{prefix}-{index}",
        }
        for index, path in enumerate(paths)
    }


def _source(
    *,
    policy_id: str,
    attempt_id: uuid.UUID,
    effective_date: date = date(2026, 9, 1),
    rules: InternationalTravelPolicyRules | None = None,
    provenance: dict[str, dict] | None = None,
) -> PolicyComparisonSource:
    return PolicyComparisonSource(
        policy_change_id=policy_id,
        extraction_attempt_id=attempt_id,
        effective_date=effective_date,
        rules=rules or _rules(),
        provenance=provenance or _provenance(policy_id),
    )


def test_identical_semantics_produce_no_differences_despite_provenance_changes() -> None:
    baseline = _source(policy_id="baseline", attempt_id=ATTEMPT_1)
    proposed = _source(
        policy_id="proposed",
        attempt_id=ATTEMPT_2,
        provenance=_provenance("different-wording-and-spans"),
    )

    assert compare_international_travel_policies(baseline, proposed) == ()


@pytest.mark.parametrize(
    ("effective_date", "rules", "reason_code"),
    [
        (date(2026, 10, 1), _rules(), "POLICY_EFFECTIVE_DATE_MODIFIED"),
        (
            date(2026, 9, 1),
            _rules(worker_scope__assigned_work_country="GB"),
            "WORKER_LOCATION_MODIFIED",
        ),
        (
            date(2026, 9, 1),
            _rules(trip_scope__origin_country="GB"),
            "TRIP_ORIGIN_MODIFIED",
        ),
        (
            date(2026, 9, 1),
            _rules(security_training__course_identifier="advanced-travel-security"),
            "TRAINING_REQUIREMENT_MODIFIED",
        ),
    ],
)
def test_scalar_semantic_changes_are_material_modifications(
    effective_date: date,
    rules: InternationalTravelPolicyRules,
    reason_code: str,
) -> None:
    differences = compare_international_travel_policies(
        _source(policy_id="baseline", attempt_id=ATTEMPT_1),
        _source(
            policy_id="proposed",
            attempt_id=ATTEMPT_2,
            effective_date=effective_date,
            rules=rules,
        ),
    )

    difference = next(item for item in differences if item.reason_code == reason_code)
    assert difference.change_type == "modified"
    assert difference.material is True
    assert difference.baseline_provenance is not None
    assert difference.proposed_provenance is not None


def test_collection_changes_are_added_and_removed_in_stable_order() -> None:
    proposed_rules = _rules(
        worker_scope__worker_types=["employee"],
        trip_scope__excluded_destination_countries=["US", "MX"],
    )

    differences = compare_international_travel_policies(
        _source(policy_id="baseline", attempt_id=ATTEMPT_1),
        _source(policy_id="proposed", attempt_id=ATTEMPT_2, rules=proposed_rules),
    )

    assert [(item.rule_identity, item.change_type, item.reason_code) for item in differences] == [
        (
            "worker_scope.worker_types:contractor",
            "removed",
            "WORKER_TYPE_REMOVED",
        ),
        (
            "trip_scope.excluded_destination_countries:CA",
            "removed",
            "EXCLUDED_DESTINATION_REMOVED",
        ),
        (
            "trip_scope.excluded_destination_countries:MX",
            "added",
            "EXCLUDED_DESTINATION_ADDED",
        ),
    ]
    assert differences[0].baseline_provenance is not None
    assert differences[0].proposed_provenance is None
    assert differences[-1].baseline_provenance is None
    assert differences[-1].proposed_provenance is not None


def test_booking_exemption_comparator_is_explicit_even_though_schema_v1_requires_true() -> None:
    baseline_rules = _rules()
    proposed_rules = baseline_rules.model_copy(
        update={
            "manager_approval": ManagerApprovalRules.model_construct(
                booking_before_effective_date_is_exempt=False
            )
        }
    )

    differences = compare_international_travel_policies(
        _source(policy_id="baseline", attempt_id=ATTEMPT_1, rules=baseline_rules),
        _source(policy_id="proposed", attempt_id=ATTEMPT_2, rules=proposed_rules),
    )

    assert differences[0].reason_code == "BOOKING_EXEMPTION_MODIFIED"


def test_fingerprint_is_stable_for_equivalent_inputs() -> None:
    baseline = _source(policy_id="baseline", attempt_id=ATTEMPT_1)
    proposed = _source(
        policy_id="proposed",
        attempt_id=ATTEMPT_2,
        effective_date=date(2026, 10, 1),
    )
    differences = compare_international_travel_policies(baseline, proposed)

    assert calculate_policy_comparison_fingerprint(
        baseline, proposed, differences
    ) == calculate_policy_comparison_fingerprint(baseline, proposed, differences)
