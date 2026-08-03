import hashlib
import json
import uuid
from dataclasses import dataclass
from typing import Any, Literal

IMPACT_DELTA_CONTRACT_VERSION = "enterprise-impact-delta-v1"

DeltaItemKind = Literal["worker", "finding", "enterprise_impact"]
DeltaChangeType = Literal[
    "became_affected",
    "no_longer_affected",
    "remained_affected",
    "introduced",
    "disappeared",
    "removed",
]


@dataclass(frozen=True)
class WorkerDeltaSource:
    record_id: uuid.UUID
    worker_id: str
    trip_id: str
    classification: Literal["affected", "unaffected"]
    reason_codes: tuple[str, ...]
    snapshot: dict[str, Any]

    @property
    def stable_identity(self) -> str:
        return f"worker:{self.worker_id}:trip:{self.trip_id}"

    def semantic_payload(self) -> dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "trip_id": self.trip_id,
            "classification": self.classification,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class FindingDeltaSource:
    record_id: uuid.UUID
    worker_id: str
    trip_id: str
    finding_type: str
    severity: str
    rule_code: str
    snapshot: dict[str, Any]

    @property
    def stable_identity(self) -> str:
        return ":".join(
            (
                "finding",
                self.worker_id,
                self.trip_id,
                self.finding_type,
                self.severity,
                self.rule_code,
            )
        )

    def semantic_payload(self) -> dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "trip_id": self.trip_id,
            "finding_type": self.finding_type,
            "severity": self.severity,
            "rule_code": self.rule_code,
        }


@dataclass(frozen=True)
class EnterpriseImpactDeltaSource:
    record_id: uuid.UUID
    domain: str
    object_type: str
    source_key: str
    classification: str
    reason_code: str
    snapshot: dict[str, Any]

    @property
    def stable_identity(self) -> str:
        return ":".join(
            (
                "enterprise_impact",
                self.domain,
                self.object_type,
                self.source_key,
                self.classification,
                self.reason_code,
            )
        )

    def semantic_payload(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "object_type": self.object_type,
            "source_key": self.source_key,
            "classification": self.classification,
            "reason_code": self.reason_code,
        }


@dataclass(frozen=True)
class AssessmentDeltaSource:
    policy_change_id: str
    workers: tuple[WorkerDeltaSource, ...]
    findings: tuple[FindingDeltaSource, ...]
    enterprise_impacts: tuple[EnterpriseImpactDeltaSource, ...]


@dataclass(frozen=True)
class ImpactDeltaItem:
    item_kind: DeltaItemKind
    change_type: DeltaChangeType
    stable_identity: str
    delta_reason_code: str
    baseline_record_id: uuid.UUID | None
    proposed_record_id: uuid.UUID | None
    baseline_snapshot: dict[str, Any] | None
    proposed_snapshot: dict[str, Any] | None
    baseline_semantics: dict[str, Any] | None
    proposed_semantics: dict[str, Any] | None


def calculate_enterprise_impact_delta(
    baseline: AssessmentDeltaSource,
    proposed: AssessmentDeltaSource,
) -> tuple[ImpactDeltaItem, ...]:
    items = [
        *_worker_deltas(baseline.workers, proposed.workers),
        *_set_deltas(
            item_kind="finding",
            baseline=baseline.findings,
            proposed=proposed.findings,
            introduced_reason="FINDING_INTRODUCED",
            removed_change_type="disappeared",
            removed_reason="FINDING_DISAPPEARED",
        ),
        *_set_deltas(
            item_kind="enterprise_impact",
            baseline=baseline.enterprise_impacts,
            proposed=proposed.enterprise_impacts,
            introduced_reason="ENTERPRISE_IMPACT_INTRODUCED",
            removed_change_type="removed",
            removed_reason="ENTERPRISE_IMPACT_REMOVED",
        ),
    ]
    return tuple(items)


def calculate_enterprise_impact_delta_fingerprint(
    baseline_policy_change_id: str,
    proposed_policy_change_id: str,
    items: tuple[ImpactDeltaItem, ...],
) -> str:
    payload = {
        "contract_version": IMPACT_DELTA_CONTRACT_VERSION,
        "baseline_policy_change_id": baseline_policy_change_id,
        "proposed_policy_change_id": proposed_policy_change_id,
        "items": [
            {
                "item_kind": item.item_kind,
                "change_type": item.change_type,
                "stable_identity": item.stable_identity,
                "delta_reason_code": item.delta_reason_code,
                "baseline": item.baseline_semantics,
                "proposed": item.proposed_semantics,
            }
            for item in items
        ],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _worker_deltas(
    baseline: tuple[WorkerDeltaSource, ...],
    proposed: tuple[WorkerDeltaSource, ...],
) -> list[ImpactDeltaItem]:
    baseline_by_identity = _by_identity(baseline)
    proposed_by_identity = _by_identity(proposed)
    items: list[ImpactDeltaItem] = []
    for identity in sorted(baseline_by_identity.keys() | proposed_by_identity.keys()):
        before = baseline_by_identity.get(identity)
        after = proposed_by_identity.get(identity)
        was_affected = before is not None and before.classification == "affected"
        is_affected = after is not None and after.classification == "affected"
        if not was_affected and not is_affected:
            continue
        if not was_affected and is_affected:
            change_type: DeltaChangeType = "became_affected"
            reason_code = "WORKER_BECAME_AFFECTED"
        elif was_affected and not is_affected:
            change_type = "no_longer_affected"
            reason_code = "WORKER_NO_LONGER_AFFECTED"
        else:
            change_type = "remained_affected"
            reason_code = "WORKER_REMAINED_AFFECTED"
        items.append(
            _item(
                item_kind="worker",
                change_type=change_type,
                stable_identity=identity,
                delta_reason_code=reason_code,
                baseline=before,
                proposed=after,
            )
        )
    return items


def _set_deltas(
    *,
    item_kind: Literal["finding", "enterprise_impact"],
    baseline: tuple[FindingDeltaSource, ...] | tuple[EnterpriseImpactDeltaSource, ...],
    proposed: tuple[FindingDeltaSource, ...] | tuple[EnterpriseImpactDeltaSource, ...],
    introduced_reason: str,
    removed_change_type: Literal["disappeared", "removed"],
    removed_reason: str,
) -> list[ImpactDeltaItem]:
    baseline_by_identity = _by_identity(baseline)
    proposed_by_identity = _by_identity(proposed)
    items: list[ImpactDeltaItem] = []
    for identity in sorted(proposed_by_identity.keys() - baseline_by_identity.keys()):
        items.append(
            _item(
                item_kind=item_kind,
                change_type="introduced",
                stable_identity=identity,
                delta_reason_code=introduced_reason,
                baseline=None,
                proposed=proposed_by_identity[identity],
            )
        )
    for identity in sorted(baseline_by_identity.keys() - proposed_by_identity.keys()):
        items.append(
            _item(
                item_kind=item_kind,
                change_type=removed_change_type,
                stable_identity=identity,
                delta_reason_code=removed_reason,
                baseline=baseline_by_identity[identity],
                proposed=None,
            )
        )
    return items


def _by_identity(items: tuple[Any, ...]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for item in items:
        if item.stable_identity in result:
            raise ValueError(f"Duplicate stable business identity: {item.stable_identity}")
        result[item.stable_identity] = item
    return result


def _item(
    *,
    item_kind: DeltaItemKind,
    change_type: DeltaChangeType,
    stable_identity: str,
    delta_reason_code: str,
    baseline: Any | None,
    proposed: Any | None,
) -> ImpactDeltaItem:
    return ImpactDeltaItem(
        item_kind=item_kind,
        change_type=change_type,
        stable_identity=stable_identity,
        delta_reason_code=delta_reason_code,
        baseline_record_id=baseline.record_id if baseline is not None else None,
        proposed_record_id=proposed.record_id if proposed is not None else None,
        baseline_snapshot=baseline.snapshot if baseline is not None else None,
        proposed_snapshot=proposed.snapshot if proposed is not None else None,
        baseline_semantics=baseline.semantic_payload() if baseline is not None else None,
        proposed_semantics=proposed.semantic_payload() if proposed is not None else None,
    )
