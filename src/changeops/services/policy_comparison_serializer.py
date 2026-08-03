from sqlalchemy.orm import Session

from changeops.db.models import PolicyChange, PolicyComparison
from changeops.schemas.policy_comparisons import (
    PolicyComparisonDifferenceResponse,
    PolicyComparisonResponse,
    PolicyComparisonSourceResponse,
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
