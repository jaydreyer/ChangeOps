import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import date
from typing import Any, Literal

from changeops.domain.types import InternationalTravelPolicyRules

COMPARISON_CONTRACT_VERSION = "international-travel-policy-comparison-v1"

ChangeType = Literal["added", "removed", "modified"]


@dataclass(frozen=True)
class PolicyComparisonSource:
    policy_change_id: str
    extraction_attempt_id: uuid.UUID
    effective_date: date
    rules: InternationalTravelPolicyRules
    provenance: dict[str, dict[str, Any]]


@dataclass(frozen=True)
class PolicyRuleDifference:
    rule_identity: str
    field_path: str
    change_type: ChangeType
    baseline_value: Any | None
    proposed_value: Any | None
    material: bool
    reason_code: str
    baseline_provenance: dict[str, Any] | None
    proposed_provenance: dict[str, Any] | None


_PROVENANCE_PATHS = {
    "effective_date": "candidate_rules.effective_date",
    "worker_scope.assigned_work_country": ("candidate_rules.worker_scope.assigned_work_country"),
    "worker_scope.worker_types": "candidate_rules.worker_scope.worker_types",
    "trip_scope.origin_country": "candidate_rules.trip_scope.origin_country",
    "trip_scope.excluded_destination_countries": (
        "candidate_rules.trip_scope.excluded_destination_countries"
    ),
    "manager_approval.booking_before_effective_date_is_exempt": (
        "candidate_rules.manager_approval.booking_before_effective_date_is_exempt"
    ),
    "security_training.course_identifier": "candidate_rules.security_training.course_name",
}


def compare_international_travel_policies(
    baseline: PolicyComparisonSource,
    proposed: PolicyComparisonSource,
) -> tuple[PolicyRuleDifference, ...]:
    differences: list[PolicyRuleDifference] = []
    _append_modified(
        differences,
        baseline,
        proposed,
        field_path="effective_date",
        baseline_value=baseline.effective_date.isoformat(),
        proposed_value=proposed.effective_date.isoformat(),
        reason_code="POLICY_EFFECTIVE_DATE_MODIFIED",
    )
    _append_modified(
        differences,
        baseline,
        proposed,
        field_path="worker_scope.assigned_work_country",
        baseline_value=baseline.rules.worker_scope.assigned_work_country,
        proposed_value=proposed.rules.worker_scope.assigned_work_country,
        reason_code="WORKER_LOCATION_MODIFIED",
    )
    _append_collection_changes(
        differences,
        baseline,
        proposed,
        field_path="worker_scope.worker_types",
        baseline_values=baseline.rules.worker_scope.worker_types,
        proposed_values=proposed.rules.worker_scope.worker_types,
        added_reason_code="WORKER_TYPE_ADDED",
        removed_reason_code="WORKER_TYPE_REMOVED",
    )
    _append_modified(
        differences,
        baseline,
        proposed,
        field_path="trip_scope.origin_country",
        baseline_value=baseline.rules.trip_scope.origin_country,
        proposed_value=proposed.rules.trip_scope.origin_country,
        reason_code="TRIP_ORIGIN_MODIFIED",
    )
    _append_collection_changes(
        differences,
        baseline,
        proposed,
        field_path="trip_scope.excluded_destination_countries",
        baseline_values=baseline.rules.trip_scope.excluded_destination_countries,
        proposed_values=proposed.rules.trip_scope.excluded_destination_countries,
        added_reason_code="EXCLUDED_DESTINATION_ADDED",
        removed_reason_code="EXCLUDED_DESTINATION_REMOVED",
    )
    _append_modified(
        differences,
        baseline,
        proposed,
        field_path="manager_approval.booking_before_effective_date_is_exempt",
        baseline_value=(baseline.rules.manager_approval.booking_before_effective_date_is_exempt),
        proposed_value=(proposed.rules.manager_approval.booking_before_effective_date_is_exempt),
        reason_code="BOOKING_EXEMPTION_MODIFIED",
    )
    _append_modified(
        differences,
        baseline,
        proposed,
        field_path="security_training.course_identifier",
        baseline_value=baseline.rules.security_training.course_identifier,
        proposed_value=proposed.rules.security_training.course_identifier,
        reason_code="TRAINING_REQUIREMENT_MODIFIED",
    )
    return tuple(differences)


def calculate_policy_comparison_fingerprint(
    baseline: PolicyComparisonSource,
    proposed: PolicyComparisonSource,
    differences: tuple[PolicyRuleDifference, ...],
) -> str:
    payload = {
        "contract_version": COMPARISON_CONTRACT_VERSION,
        "baseline": _source_fingerprint_payload(baseline),
        "proposed": _source_fingerprint_payload(proposed),
        "differences": [
            {
                "rule_identity": item.rule_identity,
                "field_path": item.field_path,
                "change_type": item.change_type,
                "baseline_value": item.baseline_value,
                "proposed_value": item.proposed_value,
                "material": item.material,
                "reason_code": item.reason_code,
            }
            for item in differences
        ],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _append_modified(
    differences: list[PolicyRuleDifference],
    baseline: PolicyComparisonSource,
    proposed: PolicyComparisonSource,
    *,
    field_path: str,
    baseline_value: Any,
    proposed_value: Any,
    reason_code: str,
) -> None:
    if baseline_value == proposed_value:
        return
    provenance_path = _PROVENANCE_PATHS[field_path]
    differences.append(
        PolicyRuleDifference(
            rule_identity=field_path,
            field_path=field_path,
            change_type="modified",
            baseline_value=baseline_value,
            proposed_value=proposed_value,
            material=True,
            reason_code=reason_code,
            baseline_provenance=baseline.provenance.get(provenance_path),
            proposed_provenance=proposed.provenance.get(provenance_path),
        )
    )


def _append_collection_changes(
    differences: list[PolicyRuleDifference],
    baseline: PolicyComparisonSource,
    proposed: PolicyComparisonSource,
    *,
    field_path: str,
    baseline_values: tuple[str, ...],
    proposed_values: tuple[str, ...],
    added_reason_code: str,
    removed_reason_code: str,
) -> None:
    provenance_path = _PROVENANCE_PATHS[field_path]
    baseline_set = set(baseline_values)
    proposed_set = set(proposed_values)
    for value in sorted(baseline_set - proposed_set):
        differences.append(
            PolicyRuleDifference(
                rule_identity=f"{field_path}:{value}",
                field_path=field_path,
                change_type="removed",
                baseline_value=value,
                proposed_value=None,
                material=True,
                reason_code=removed_reason_code,
                baseline_provenance=baseline.provenance.get(provenance_path),
                proposed_provenance=None,
            )
        )
    for value in sorted(proposed_set - baseline_set):
        differences.append(
            PolicyRuleDifference(
                rule_identity=f"{field_path}:{value}",
                field_path=field_path,
                change_type="added",
                baseline_value=None,
                proposed_value=value,
                material=True,
                reason_code=added_reason_code,
                baseline_provenance=None,
                proposed_provenance=proposed.provenance.get(provenance_path),
            )
        )


def _source_fingerprint_payload(source: PolicyComparisonSource) -> dict[str, Any]:
    return {
        "policy_change_id": source.policy_change_id,
        "extraction_attempt_id": str(source.extraction_attempt_id),
        "effective_date": source.effective_date.isoformat(),
        "rules": source.rules.model_dump(mode="json"),
    }
