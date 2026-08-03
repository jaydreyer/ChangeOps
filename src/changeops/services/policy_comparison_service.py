import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from changeops.db.models import (
    PolicyAnalysisClarification,
    PolicyAnalysisRun,
    PolicyChange,
    PolicyComparison,
    PolicyComparisonDifference,
    PolicyExtractionAttempt,
)
from changeops.domain.policy_comparison import (
    COMPARISON_CONTRACT_VERSION,
    PolicyComparisonSource,
    calculate_policy_comparison_fingerprint,
    compare_international_travel_policies,
)
from changeops.domain.policy_extraction import MATERIAL_FIELD_PATHS
from changeops.domain.types import InternationalTravelPolicyRules

ComparisonSide = Literal["baseline", "proposed"]


class PolicyComparisonNotFoundError(Exception):
    pass


class PolicyComparisonCreateError(Exception):
    def __init__(self, code: str, message: str, *, status_code: int = 409) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class PolicyComparisonReadiness:
    ready: bool
    status: str
    accepted_extraction_attempt_id: uuid.UUID | None


@dataclass(frozen=True)
class _ResolvedSource:
    run: PolicyAnalysisRun
    attempt: PolicyExtractionAttempt
    provenance: dict[str, dict[str, Any]]


def create_policy_comparison(
    session: Session,
    *,
    baseline_policy_change_id: str,
    proposed_policy_change_id: str,
    created_by: str,
) -> tuple[PolicyComparison, bool]:
    creator = created_by.strip()
    if not creator or len(creator) > 200:
        raise PolicyComparisonCreateError(
            "policy_comparison_creator_required",
            "A comparison creator identity between 1 and 200 characters is required.",
            status_code=422,
        )
    if baseline_policy_change_id == proposed_policy_change_id:
        raise PolicyComparisonCreateError(
            "policy_comparison_same_policy",
            "Baseline and proposed policies must be distinct.",
            status_code=422,
        )

    fingerprint: str | None = None
    try:
        with session.begin():
            baseline_policy = _get_policy(
                session,
                baseline_policy_change_id,
                side="baseline",
            )
            proposed_policy = _get_policy(
                session,
                proposed_policy_change_id,
                side="proposed",
            )
            if baseline_policy.organization_id != proposed_policy.organization_id:
                raise PolicyComparisonCreateError(
                    "policy_comparison_organization_mismatch",
                    "Baseline and proposed policies must belong to the same organization.",
                    status_code=422,
                )

            baseline = _resolve_source(session, baseline_policy, side="baseline")
            proposed = _resolve_source(session, proposed_policy, side="proposed")
            _validate_compatibility(baseline.attempt, proposed.attempt)
            baseline_source = _typed_source(baseline, baseline_policy)
            proposed_source = _typed_source(proposed, proposed_policy)
            differences = compare_international_travel_policies(
                baseline_source,
                proposed_source,
            )
            _validate_difference_provenance(differences)
            fingerprint = calculate_policy_comparison_fingerprint(
                baseline_source,
                proposed_source,
                differences,
            )
            existing_id = session.scalar(
                select(PolicyComparison.id).where(
                    PolicyComparison.comparison_fingerprint == fingerprint
                )
            )
            if existing_id is not None:
                comparison_id = existing_id
                created = False
            else:
                comparison = PolicyComparison(
                    organization_id=baseline_policy.organization_id,
                    baseline_policy_change_id=baseline_policy.id,
                    proposed_policy_change_id=proposed_policy.id,
                    baseline_extraction_attempt_id=baseline.attempt.id,
                    proposed_extraction_attempt_id=proposed.attempt.id,
                    baseline_policy_snapshot=_policy_snapshot(baseline_policy),
                    proposed_policy_snapshot=_policy_snapshot(proposed_policy),
                    comparison_contract_version=COMPARISON_CONTRACT_VERSION,
                    comparison_fingerprint=fingerprint,
                    created_by=creator,
                    created_at=datetime.now(UTC),
                )
                session.add(comparison)
                session.flush()
                for sequence, difference in enumerate(differences, start=1):
                    session.add(
                        PolicyComparisonDifference(
                            policy_comparison_id=comparison.id,
                            sequence=sequence,
                            rule_identity=difference.rule_identity,
                            field_path=difference.field_path,
                            change_type=difference.change_type,
                            baseline_value=difference.baseline_value,
                            proposed_value=difference.proposed_value,
                            material=difference.material,
                            reason_code=difference.reason_code,
                            baseline_provenance=difference.baseline_provenance,
                            proposed_provenance=difference.proposed_provenance,
                        )
                    )
                session.flush()
                comparison_id = comparison.id
                created = True
    except IntegrityError:
        session.rollback()
        if fingerprint is None:
            raise
        existing_id = session.scalar(
            select(PolicyComparison.id).where(
                PolicyComparison.comparison_fingerprint == fingerprint
            )
        )
        if existing_id is None:
            raise
        comparison_id = existing_id
        created = False
    return get_policy_comparison(session, comparison_id), created


def get_policy_comparison(
    session: Session,
    comparison_id: uuid.UUID,
) -> PolicyComparison:
    comparison = session.scalar(
        select(PolicyComparison)
        .where(PolicyComparison.id == comparison_id)
        .options(selectinload(PolicyComparison.differences))
    )
    if comparison is None:
        raise PolicyComparisonNotFoundError(str(comparison_id))
    return comparison


def get_policy_comparison_readiness(
    session: Session,
    policy: PolicyChange,
) -> PolicyComparisonReadiness:
    try:
        resolved = _resolve_source(session, policy, side="baseline")
        _typed_source(resolved, policy)
    except PolicyComparisonCreateError as error:
        return PolicyComparisonReadiness(
            ready=False,
            status=error.code.removeprefix("baseline_"),
            accepted_extraction_attempt_id=None,
        )
    return PolicyComparisonReadiness(
        ready=True,
        status="ready",
        accepted_extraction_attempt_id=resolved.attempt.id,
    )


def _get_policy(
    session: Session,
    policy_change_id: str,
    *,
    side: ComparisonSide,
) -> PolicyChange:
    policy = session.get(PolicyChange, policy_change_id)
    if policy is None:
        raise PolicyComparisonCreateError(
            f"{side}_policy_not_found",
            f"The {side} policy was not found.",
            status_code=404,
        )
    return policy


def _resolve_source(
    session: Session,
    policy: PolicyChange,
    *,
    side: ComparisonSide,
) -> _ResolvedSource:
    run = session.scalar(
        select(PolicyAnalysisRun)
        .where(
            PolicyAnalysisRun.policy_change_id == policy.id,
            PolicyAnalysisRun.status == "completed",
        )
        .order_by(
            PolicyAnalysisRun.completed_at.desc(),
            PolicyAnalysisRun.created_at.desc(),
            PolicyAnalysisRun.id.desc(),
        )
        .limit(1)
    )
    if run is None or run.latest_extraction_attempt_id is None:
        raise _not_ready(side, "No completed accepted policy analysis is available.")
    attempt = session.get(PolicyExtractionAttempt, run.latest_extraction_attempt_id)
    pending = session.scalar(
        select(PolicyAnalysisClarification.id).where(
            PolicyAnalysisClarification.policy_analysis_run_id == run.id,
            PolicyAnalysisClarification.status == "pending",
        )
    )
    if pending is not None:
        raise _not_ready(
            side,
            f"The {side} policy has a pending clarification.",
        )
    if (
        run.organization_id != policy.organization_id
        or run.policy_change_id != policy.id
        or run.policy_text_snapshot != policy.policy_text
        or attempt is None
        or attempt.id != run.latest_extraction_attempt_id
        or attempt.policy_analysis_run_id != run.id
        or attempt.policy_change_id != policy.id
        or attempt.policy_text_snapshot != run.policy_text_snapshot
        or attempt.validation_outcome != "accepted"
        or attempt.accepted_rules is None
        or attempt.candidate_rules is None
    ):
        raise PolicyComparisonCreateError(
            "policy_comparison_lineage_inconsistent",
            "The policy analysis and accepted extraction lineage are inconsistent.",
        )
    candidate_effective_date = attempt.candidate_rules.get("effective_date")
    if candidate_effective_date != policy.effective_date.isoformat():
        raise PolicyComparisonCreateError(
            "policy_comparison_lineage_inconsistent",
            "The accepted extraction effective date does not match its policy source.",
        )
    provenance = _validated_provenance(run, attempt)
    return _ResolvedSource(run=run, attempt=attempt, provenance=provenance)


def _typed_source(
    resolved: _ResolvedSource,
    policy: PolicyChange,
) -> PolicyComparisonSource:
    try:
        rules = InternationalTravelPolicyRules.model_validate(resolved.attempt.accepted_rules)
    except ValidationError as error:
        raise PolicyComparisonCreateError(
            "policy_comparison_lineage_inconsistent",
            "Accepted rules do not satisfy the supported typed policy contract.",
        ) from error
    return PolicyComparisonSource(
        policy_change_id=policy.id,
        extraction_attempt_id=resolved.attempt.id,
        effective_date=policy.effective_date,
        rules=rules,
        provenance=resolved.provenance,
    )


def _validate_compatibility(
    baseline: PolicyExtractionAttempt,
    proposed: PolicyExtractionAttempt,
) -> None:
    baseline_rules = baseline.accepted_rules or {}
    proposed_rules = proposed.accepted_rules or {}
    if baseline_rules.get("kind") != proposed_rules.get("kind"):
        raise PolicyComparisonCreateError(
            "policy_comparison_family_mismatch",
            "Baseline and proposed policy families do not match.",
            status_code=422,
        )
    if baseline_rules.get("schema_version") != proposed_rules.get("schema_version"):
        raise PolicyComparisonCreateError(
            "policy_comparison_schema_mismatch",
            "Baseline and proposed policy rule schema versions do not match.",
            status_code=422,
        )
    if (
        baseline_rules.get("kind") != "international_travel"
        or baseline_rules.get("schema_version") != 1
    ):
        raise PolicyComparisonCreateError(
            "policy_comparison_schema_unsupported",
            "Only international-travel schema version 1 can be compared.",
            status_code=422,
        )


def _validated_provenance(
    run: PolicyAnalysisRun,
    attempt: PolicyExtractionAttempt,
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for entry in run.accepted_rule_provenance:
        source = entry.get("source")
        if source == "policy_text":
            field_path = entry.get("field_path")
            start = entry.get("start")
            end = entry.get("end")
            quote = entry.get("quote")
            if (
                not isinstance(field_path, str)
                or not isinstance(start, int)
                or not isinstance(end, int)
                or not isinstance(quote, str)
                or start < 0
                or end <= start
                or attempt.policy_text_snapshot[start:end] != quote
            ):
                raise PolicyComparisonCreateError(
                    "policy_comparison_lineage_inconsistent",
                    "Accepted policy-text provenance does not resolve against its source.",
                )
            result[field_path] = dict(entry)
        elif source == "human":
            affected_fields = entry.get("affected_fields")
            clarification_id = entry.get("clarification_id")
            if not isinstance(affected_fields, list) or not clarification_id:
                raise PolicyComparisonCreateError(
                    "policy_comparison_lineage_inconsistent",
                    "Accepted human provenance is incomplete.",
                )
            clarification = next(
                (
                    item
                    for item in run.clarifications
                    if str(item.id) == str(clarification_id) and item.status == "answered"
                ),
                None,
            )
            if clarification is None:
                raise PolicyComparisonCreateError(
                    "policy_comparison_lineage_inconsistent",
                    "Accepted human provenance does not resolve to an answered clarification.",
                )
            for field_path in affected_fields:
                result[str(field_path)] = dict(entry)
        else:
            raise PolicyComparisonCreateError(
                "policy_comparison_lineage_inconsistent",
                "Accepted provenance has an unsupported source.",
            )
    missing = MATERIAL_FIELD_PATHS - result.keys()
    if missing:
        raise PolicyComparisonCreateError(
            "policy_comparison_lineage_inconsistent",
            "Accepted provenance is missing a required material field.",
        )
    return result


def _validate_difference_provenance(differences: tuple[Any, ...]) -> None:
    for difference in differences:
        if difference.baseline_value is not None and difference.baseline_provenance is None:
            raise PolicyComparisonCreateError(
                "policy_comparison_lineage_inconsistent",
                "A baseline semantic value is missing accepted provenance.",
            )
        if difference.proposed_value is not None and difference.proposed_provenance is None:
            raise PolicyComparisonCreateError(
                "policy_comparison_lineage_inconsistent",
                "A proposed semantic value is missing accepted provenance.",
            )


def _not_ready(side: ComparisonSide, message: str) -> PolicyComparisonCreateError:
    return PolicyComparisonCreateError(
        f"{side}_policy_not_ready",
        message,
    )


def _policy_snapshot(policy: PolicyChange) -> dict[str, Any]:
    return {
        "policy_change_id": policy.id,
        "title": policy.title,
        "version": policy.version,
        "effective_date": policy.effective_date.isoformat(),
    }
