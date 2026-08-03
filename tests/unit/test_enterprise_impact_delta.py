import uuid

import pytest

from changeops.domain.enterprise_impact_delta import (
    AssessmentDeltaSource,
    EnterpriseImpactDeltaSource,
    FindingDeltaSource,
    WorkerDeltaSource,
    calculate_enterprise_impact_delta,
    calculate_enterprise_impact_delta_fingerprint,
)


def _worker(
    worker_id: str,
    trip_id: str,
    classification: str,
    *reason_codes: str,
) -> WorkerDeltaSource:
    return WorkerDeltaSource(
        record_id=uuid.uuid4(),
        worker_id=worker_id,
        trip_id=trip_id,
        classification=classification,
        reason_codes=reason_codes,
        snapshot={"worker_id": worker_id, "classification": classification},
    )


def _finding(worker_id: str, rule_code: str) -> FindingDeltaSource:
    return FindingDeltaSource(
        record_id=uuid.uuid4(),
        worker_id=worker_id,
        trip_id=f"trip-{worker_id}",
        finding_type=rule_code.lower(),
        severity="action_required",
        rule_code=rule_code,
        snapshot={"worker_id": worker_id, "rule_code": rule_code},
    )


def _impact(source_key: str, reason_code: str) -> EnterpriseImpactDeltaSource:
    return EnterpriseImpactDeltaSource(
        record_id=uuid.uuid4(),
        domain="systems",
        object_type="enterprise_system",
        source_key=source_key,
        classification="operationally_affected",
        reason_code=reason_code,
        snapshot={"source_key": source_key, "reason_code": reason_code},
    )


def _assessment(
    *,
    workers=(),
    findings=(),
    impacts=(),
    policy_id="policy",
) -> AssessmentDeltaSource:
    return AssessmentDeltaSource(
        policy_change_id=policy_id,
        workers=tuple(workers),
        findings=tuple(findings),
        enterprise_impacts=tuple(impacts),
    )


def test_calculates_closed_worker_finding_and_enterprise_impact_deltas() -> None:
    baseline = _assessment(
        policy_id="baseline",
        workers=(
            _worker("became", "trip-became", "unaffected", "DESTINATION_EXCLUDED"),
            _worker("cleared", "trip-cleared", "affected", "WORKER_IN_SCOPE"),
            _worker("remained", "trip-remained", "affected", "WORKER_IN_SCOPE"),
            _worker("unchanged", "trip-unchanged", "unaffected", "ORIGIN_OUT_OF_SCOPE"),
        ),
        findings=(_finding("cleared", "TRAINING_REQUIRED"),),
        impacts=(_impact("system-old", "OLD_REASON"),),
    )
    proposed = _assessment(
        policy_id="proposed",
        workers=(
            _worker("became", "trip-became", "affected", "WORKER_IN_SCOPE"),
            _worker("cleared", "trip-cleared", "unaffected", "WORKER_TYPE_OUT_OF_SCOPE"),
            _worker("remained", "trip-remained", "affected", "WORKER_IN_SCOPE"),
            _worker("unchanged", "trip-unchanged", "unaffected", "ORIGIN_OUT_OF_SCOPE"),
        ),
        findings=(_finding("became", "MANAGER_APPROVAL_REQUIRED"),),
        impacts=(_impact("system-new", "NEW_REASON"),),
    )

    items = calculate_enterprise_impact_delta(baseline, proposed)

    assert [(item.item_kind, item.change_type) for item in items] == [
        ("worker", "became_affected"),
        ("worker", "no_longer_affected"),
        ("worker", "remained_affected"),
        ("finding", "introduced"),
        ("finding", "disappeared"),
        ("enterprise_impact", "introduced"),
        ("enterprise_impact", "removed"),
    ]
    assert all(item.delta_reason_code for item in items)
    assert items[0].baseline_record_id is not None
    assert items[0].proposed_record_id is not None
    assert items[3].baseline_record_id is None
    assert items[4].proposed_record_id is None


def test_regenerated_uuid_records_compare_equal_when_business_meaning_is_unchanged() -> None:
    first_baseline = _assessment(
        policy_id="baseline",
        workers=(_worker("worker-1", "trip-1", "affected", "WORKER_IN_SCOPE"),),
    )
    first_proposed = _assessment(
        policy_id="proposed",
        workers=(_worker("worker-1", "trip-1", "unaffected", "WORKER_TYPE_OUT_OF_SCOPE"),),
    )
    regenerated_baseline = _assessment(
        policy_id="baseline",
        workers=(_worker("worker-1", "trip-1", "affected", "WORKER_IN_SCOPE"),),
    )
    regenerated_proposed = _assessment(
        policy_id="proposed",
        workers=(_worker("worker-1", "trip-1", "unaffected", "WORKER_TYPE_OUT_OF_SCOPE"),),
    )

    first = calculate_enterprise_impact_delta(first_baseline, first_proposed)
    regenerated = calculate_enterprise_impact_delta(
        regenerated_baseline,
        regenerated_proposed,
    )

    assert first[0].baseline_record_id != regenerated[0].baseline_record_id
    assert first[0].stable_identity == regenerated[0].stable_identity
    assert calculate_enterprise_impact_delta_fingerprint(
        "baseline", "proposed", first
    ) == calculate_enterprise_impact_delta_fingerprint("baseline", "proposed", regenerated)


def test_duplicate_business_identity_fails_closed() -> None:
    duplicate = _worker("worker-1", "trip-1", "affected", "WORKER_IN_SCOPE")

    with pytest.raises(ValueError, match="Duplicate stable business identity"):
        calculate_enterprise_impact_delta(
            _assessment(workers=(duplicate, duplicate)),
            _assessment(),
        )
