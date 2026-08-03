from sqlalchemy.orm import Session

from changeops.db.models import PolicyChange, PolicyComparison, PolicyComparisonImpactDelta
from changeops.schemas.policy_comparisons import (
    EnterpriseImpactDeltaResponse,
    EnterpriseImpactDeltaSideResponse,
    FindingDeltaResponse,
    FindingDeltaSideResponse,
    ImpactDeltaSummaryResponse,
    PolicyComparisonDifferenceResponse,
    PolicyComparisonImpactDeltaResponse,
    PolicyComparisonResponse,
    PolicyComparisonSourceResponse,
    WorkerDeltaResponse,
    WorkerDeltaSideResponse,
)
from changeops.services.policy_comparison_service import PolicyComparisonCreateError


def serialize_policy_comparison(
    session: Session,
    comparison: PolicyComparison,
) -> PolicyComparisonResponse:
    baseline = session.get(PolicyChange, comparison.baseline_policy_change_id)
    proposed = session.get(PolicyChange, comparison.proposed_policy_change_id)
    if (
        baseline is None
        or proposed is None
        or baseline.organization_id != comparison.organization_id
        or proposed.organization_id != comparison.organization_id
    ):
        raise PolicyComparisonCreateError(
            "policy_comparison_lineage_inconsistent",
            "The persisted comparison policy lineage is inconsistent.",
        )
    baseline_snapshot = _validated_policy_snapshot(
        comparison.baseline_policy_snapshot,
        baseline,
    )
    proposed_snapshot = _validated_policy_snapshot(
        comparison.proposed_policy_snapshot,
        proposed,
    )
    differences = sorted(comparison.differences, key=lambda item: item.sequence)
    return PolicyComparisonResponse(
        id=comparison.id,
        organization_id=comparison.organization_id,
        baseline=PolicyComparisonSourceResponse(
            policy_change_id=baseline.id,
            title=baseline_snapshot["title"],
            version=baseline_snapshot["version"],
            effective_date=baseline_snapshot["effective_date"],
            accepted_extraction_attempt_id=comparison.baseline_extraction_attempt_id,
        ),
        proposed=PolicyComparisonSourceResponse(
            policy_change_id=proposed.id,
            title=proposed_snapshot["title"],
            version=proposed_snapshot["version"],
            effective_date=proposed_snapshot["effective_date"],
            accepted_extraction_attempt_id=comparison.proposed_extraction_attempt_id,
        ),
        comparison_contract_version=comparison.comparison_contract_version,
        comparison_fingerprint=comparison.comparison_fingerprint,
        difference_count=len(differences),
        differences=[
            PolicyComparisonDifferenceResponse(
                id=item.id,
                sequence=item.sequence,
                rule_identity=item.rule_identity,
                field_path=item.field_path,
                change_type=item.change_type,
                baseline_value=item.baseline_value,
                proposed_value=item.proposed_value,
                material=True,
                reason_code=item.reason_code,
                baseline_provenance=item.baseline_provenance,
                proposed_provenance=item.proposed_provenance,
            )
            for item in differences
        ],
        impact_delta=(
            _serialize_impact_delta(comparison.impact_delta)
            if comparison.impact_delta is not None
            else None
        ),
        created_by=comparison.created_by,
        created_at=comparison.created_at,
    )


def _validated_policy_snapshot(snapshot: dict, policy: PolicyChange) -> dict:
    if (
        snapshot.get("policy_change_id") != policy.id
        or not isinstance(snapshot.get("title"), str)
        or not isinstance(snapshot.get("version"), str)
        or not isinstance(snapshot.get("effective_date"), str)
    ):
        raise PolicyComparisonCreateError(
            "policy_comparison_lineage_inconsistent",
            "The persisted comparison policy snapshot is inconsistent.",
        )
    return snapshot


def _serialize_impact_delta(
    delta: PolicyComparisonImpactDelta,
) -> PolicyComparisonImpactDeltaResponse:
    items = sorted(delta.items, key=lambda item: item.sequence)
    worker_items = [item for item in items if item.item_kind == "worker"]
    finding_items = [item for item in items if item.item_kind == "finding"]
    impact_items = [item for item in items if item.item_kind == "enterprise_impact"]
    return PolicyComparisonImpactDeltaResponse(
        id=delta.id,
        baseline_assessment_id=delta.baseline_assessment_id,
        proposed_assessment_id=delta.proposed_assessment_id,
        impact_delta_contract_version=delta.impact_delta_contract_version,
        impact_delta_fingerprint=delta.impact_delta_fingerprint,
        summary=ImpactDeltaSummaryResponse(
            workers_became_affected=sum(
                item.change_type == "became_affected" for item in worker_items
            ),
            workers_no_longer_affected=sum(
                item.change_type == "no_longer_affected" for item in worker_items
            ),
            workers_remained_affected=sum(
                item.change_type == "remained_affected" for item in worker_items
            ),
            findings_introduced=sum(item.change_type == "introduced" for item in finding_items),
            findings_disappeared=sum(item.change_type == "disappeared" for item in finding_items),
            enterprise_impacts_introduced=sum(
                item.change_type == "introduced" for item in impact_items
            ),
            enterprise_impacts_removed=sum(item.change_type == "removed" for item in impact_items),
        ),
        worker_deltas=[
            WorkerDeltaResponse(
                id=item.id,
                sequence=item.sequence,
                stable_identity=item.stable_identity,
                change_type=item.change_type,
                delta_reason_code=item.delta_reason_code,
                baseline_record_id=item.baseline_record_id,
                proposed_record_id=item.proposed_record_id,
                baseline=(
                    WorkerDeltaSideResponse.model_validate(item.baseline_snapshot)
                    if item.baseline_snapshot is not None
                    else None
                ),
                proposed=(
                    WorkerDeltaSideResponse.model_validate(item.proposed_snapshot)
                    if item.proposed_snapshot is not None
                    else None
                ),
            )
            for item in worker_items
        ],
        finding_deltas=[
            FindingDeltaResponse(
                id=item.id,
                sequence=item.sequence,
                stable_identity=item.stable_identity,
                change_type=item.change_type,
                delta_reason_code=item.delta_reason_code,
                baseline_record_id=item.baseline_record_id,
                proposed_record_id=item.proposed_record_id,
                baseline=(
                    FindingDeltaSideResponse.model_validate(item.baseline_snapshot)
                    if item.baseline_snapshot is not None
                    else None
                ),
                proposed=(
                    FindingDeltaSideResponse.model_validate(item.proposed_snapshot)
                    if item.proposed_snapshot is not None
                    else None
                ),
            )
            for item in finding_items
        ],
        enterprise_impact_deltas=[
            EnterpriseImpactDeltaResponse(
                id=item.id,
                sequence=item.sequence,
                stable_identity=item.stable_identity,
                change_type=item.change_type,
                delta_reason_code=item.delta_reason_code,
                baseline_record_id=item.baseline_record_id,
                proposed_record_id=item.proposed_record_id,
                baseline=(
                    EnterpriseImpactDeltaSideResponse.model_validate(item.baseline_snapshot)
                    if item.baseline_snapshot is not None
                    else None
                ),
                proposed=(
                    EnterpriseImpactDeltaSideResponse.model_validate(item.proposed_snapshot)
                    if item.proposed_snapshot is not None
                    else None
                ),
            )
            for item in impact_items
        ],
        created_by=delta.created_by,
        created_at=delta.created_at,
    )
