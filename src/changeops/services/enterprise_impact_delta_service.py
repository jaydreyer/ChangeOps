import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from changeops.db.models import (
    AssessmentEnterpriseImpact,
    AssessmentWorkerResult,
    Evidence,
    Finding,
    ImpactAssessment,
    PolicyComparison,
    PolicyComparisonImpactDelta,
    PolicyComparisonImpactDeltaItem,
)
from changeops.domain.enterprise_impact_delta import (
    IMPACT_DELTA_CONTRACT_VERSION,
    AssessmentDeltaSource,
    EnterpriseImpactDeltaSource,
    FindingDeltaSource,
    WorkerDeltaSource,
    calculate_enterprise_impact_delta,
    calculate_enterprise_impact_delta_fingerprint,
)


class EnterpriseImpactDeltaIntegrityError(RuntimeError):
    pass


def create_policy_comparison_impact_delta(
    session: Session,
    *,
    comparison: PolicyComparison,
    baseline_assessment: ImpactAssessment,
    proposed_assessment: ImpactAssessment,
    created_by: str,
) -> PolicyComparisonImpactDelta:
    existing = session.scalar(
        select(PolicyComparisonImpactDelta).where(
            PolicyComparisonImpactDelta.policy_comparison_id == comparison.id
        )
    )
    if existing is not None:
        return existing
    _validate_assessment_pair(comparison, baseline_assessment, proposed_assessment)
    baseline = _assessment_source(baseline_assessment)
    proposed = _assessment_source(proposed_assessment)
    items = calculate_enterprise_impact_delta(baseline, proposed)
    fingerprint = calculate_enterprise_impact_delta_fingerprint(
        baseline.policy_change_id,
        proposed.policy_change_id,
        items,
    )
    delta = PolicyComparisonImpactDelta(
        policy_comparison_id=comparison.id,
        organization_id=comparison.organization_id,
        baseline_assessment_id=baseline_assessment.id,
        proposed_assessment_id=proposed_assessment.id,
        impact_delta_contract_version=IMPACT_DELTA_CONTRACT_VERSION,
        impact_delta_fingerprint=fingerprint,
        created_by=created_by,
        created_at=datetime.now(UTC),
    )
    session.add(delta)
    session.flush()
    for sequence, item in enumerate(items, start=1):
        session.add(
            PolicyComparisonImpactDeltaItem(
                impact_delta_id=delta.id,
                sequence=sequence,
                item_kind=item.item_kind,
                change_type=item.change_type,
                stable_identity=item.stable_identity,
                delta_reason_code=item.delta_reason_code,
                baseline_record_id=item.baseline_record_id,
                proposed_record_id=item.proposed_record_id,
                baseline_snapshot=item.baseline_snapshot,
                proposed_snapshot=item.proposed_snapshot,
            )
        )
    session.flush()
    return delta


def get_policy_comparison_impact_delta(
    session: Session,
    comparison_id: uuid.UUID,
) -> PolicyComparisonImpactDelta | None:
    return session.scalar(
        select(PolicyComparisonImpactDelta)
        .where(PolicyComparisonImpactDelta.policy_comparison_id == comparison_id)
        .options(selectinload(PolicyComparisonImpactDelta.items))
    )


def _validate_assessment_pair(
    comparison: PolicyComparison,
    baseline: ImpactAssessment,
    proposed: ImpactAssessment,
) -> None:
    if (
        baseline.id == proposed.id
        or baseline.status != "completed"
        or proposed.status != "completed"
        or baseline.policy_change_id != comparison.baseline_policy_change_id
        or proposed.policy_change_id != comparison.proposed_policy_change_id
        or baseline.policy_analysis_run_id is None
        or proposed.policy_analysis_run_id is None
    ):
        raise EnterpriseImpactDeltaIntegrityError(
            "The comparison assessments do not satisfy the authoritative lineage contract."
        )


def _assessment_source(assessment: ImpactAssessment) -> AssessmentDeltaSource:
    evidence_by_key = {item.evidence_key: item for item in assessment.evidence}
    return AssessmentDeltaSource(
        policy_change_id=assessment.policy_change_id,
        workers=tuple(
            _worker_source(item, evidence_by_key)
            for item in sorted(
                assessment.worker_results,
                key=lambda result: (result.worker_id, result.trip_id),
            )
        ),
        findings=tuple(
            _finding_source(item)
            for item in sorted(
                assessment.findings,
                key=lambda finding: (
                    finding.worker_result.worker_id,
                    finding.worker_result.trip_id,
                    finding.finding_type,
                    finding.severity,
                    finding.rule_code,
                ),
            )
        ),
        enterprise_impacts=tuple(
            _impact_source(item)
            for item in sorted(
                assessment.enterprise_impacts,
                key=lambda impact: (
                    impact.domain,
                    impact.object_type,
                    impact.source_key,
                    impact.classification,
                    impact.reason_code,
                ),
            )
        ),
    )


def _worker_source(
    result: AssessmentWorkerResult,
    evidence_by_key: dict[str, Evidence],
) -> WorkerDeltaSource:
    evidence_keys = {
        f"worker:{result.worker_id}",
        f"trip:{result.trip_id}",
    }
    for reason_code in result.reason_codes:
        suffix = _WORKER_REASON_EVIDENCE_SUFFIXES.get(reason_code)
        if suffix is not None:
            matching = next(
                (
                    key
                    for key in evidence_by_key
                    if key.startswith("policy:") and key.endswith(f":{suffix}")
                ),
                None,
            )
            if matching is not None:
                evidence_keys.add(matching)
    worker_evidence = evidence_by_key.get(f"worker:{result.worker_id}")
    display_name = (
        worker_evidence.snapshot.get("full_name")
        if worker_evidence is not None
        else result.worker_id
    )
    snapshot = {
        "worker_id": result.worker_id,
        "display_name": display_name,
        "trip_id": result.trip_id,
        "classification": result.classification,
        "explanation": result.explanation,
        "reason_codes": list(result.reason_codes),
        "evidence": [
            _evidence_snapshot(evidence_by_key[key])
            for key in sorted(evidence_keys)
            if key in evidence_by_key
        ],
    }
    return WorkerDeltaSource(
        record_id=result.id,
        worker_id=result.worker_id,
        trip_id=result.trip_id,
        classification=result.classification,
        reason_codes=tuple(result.reason_codes),
        snapshot=snapshot,
    )


def _finding_source(finding: Finding) -> FindingDeltaSource:
    worker_result = finding.worker_result
    snapshot = {
        "worker_id": worker_result.worker_id,
        "trip_id": worker_result.trip_id,
        "finding_type": finding.finding_type,
        "severity": finding.severity,
        "rule_code": finding.rule_code,
        "explanation": finding.explanation,
        "evidence": [
            _evidence_snapshot(item)
            for item in sorted(finding.evidence, key=lambda item: item.evidence_key)
        ],
    }
    return FindingDeltaSource(
        record_id=finding.id,
        worker_id=worker_result.worker_id,
        trip_id=worker_result.trip_id,
        finding_type=finding.finding_type,
        severity=finding.severity,
        rule_code=finding.rule_code,
        snapshot=snapshot,
    )


def _impact_source(impact: AssessmentEnterpriseImpact) -> EnterpriseImpactDeltaSource:
    snapshot = {
        "domain": impact.domain,
        "object_type": impact.object_type,
        "source_key": impact.source_key,
        "display_name": impact.display_name,
        "classification": impact.classification,
        "explanation": impact.explanation,
        "reason_code": impact.reason_code,
        "evidence": [
            _evidence_snapshot(item)
            for item in sorted(impact.evidence, key=lambda item: item.evidence_key)
        ],
        "relationship_path": [
            {
                "sequence": item.sequence,
                "object_type": item.object_type,
                "stable_key": item.stable_key,
                "display_label": item.display_label,
                "relationship_to_next": item.relationship_to_next,
            }
            for item in sorted(impact.path_elements, key=lambda item: item.sequence)
        ],
    }
    return EnterpriseImpactDeltaSource(
        record_id=impact.id,
        domain=impact.domain,
        object_type=impact.object_type,
        source_key=impact.source_key,
        classification=impact.classification,
        reason_code=impact.reason_code,
        snapshot=snapshot,
    )


def _evidence_snapshot(evidence: Evidence) -> dict[str, Any]:
    return {
        "record_id": str(evidence.id),
        "evidence_key": evidence.evidence_key,
        "evidence_type": evidence.evidence_type,
        "source_type": evidence.source_type,
        "source_id": evidence.source_id,
        "label": evidence.label,
        "snapshot": evidence.snapshot,
    }


_WORKER_REASON_EVIDENCE_SUFFIXES = {
    "WORK_COUNTRY_OUT_OF_SCOPE": "worker_scope",
    "WORKER_TYPE_OUT_OF_SCOPE": "worker_scope",
    "ORIGIN_OUT_OF_SCOPE": "destination_scope",
    "DESTINATION_EXCLUDED": "destination_scope",
    "DEPARTURE_BEFORE_EFFECTIVE_DATE": "effective_date",
    "WORKER_IN_SCOPE": "worker_scope",
    "DESTINATION_IN_SCOPE": "destination_scope",
    "DEPARTURE_ON_OR_AFTER_EFFECTIVE_DATE": "effective_date",
    "MANAGER_APPROVAL_REQUIRED": "manager_approval",
    "BOOKING_DATE_EXCEPTION": "booking_exception",
    "TRAINING_ALREADY_COMPLETED": "security_training",
    "TRAINING_REQUIRED": "security_training",
}
