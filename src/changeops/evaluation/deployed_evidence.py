"""Read-only evidence check for a human-performed deployed journey."""

import argparse
import json
import sys
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

from changeops.db.session import SessionLocal
from changeops.schemas.audit_timeline import AuditActorCategory, AuditEventType
from changeops.services.audit_timeline_projection_service import get_audit_timeline
from changeops.services.demo_assessment_seed_service import (
    DEMO_PROPOSED_POLICY_ANALYSIS_RUN_ID,
)

REQUIRED_LIVE_EVENTS = {
    AuditEventType.EXTRACTION_ATTEMPTED,
    AuditEventType.EXTRACTION_ACCEPTED,
    AuditEventType.IMPACT_ASSESSMENT_COMPLETED,
    AuditEventType.HUMAN_ACTION_DECISION_RECORDED,
    AuditEventType.APPROVAL_COMPLETED,
    AuditEventType.EXECUTION_COMMAND_PREPARED,
    AuditEventType.EXECUTION_REQUESTED,
    AuditEventType.EXECUTION_SUCCEEDED,
    AuditEventType.SIMULATED_SIDE_EFFECT_CREATED,
}


class DeployedEvidenceError(Exception):
    """A stable, non-sensitive deployed-evidence failure."""


@dataclass(frozen=True)
class DeployedEvidenceSummary:
    status: str
    policy_analysis_run_id: str
    approval_run_id: str
    event_count: int
    human_decision_count: int
    execution_request_count: int
    release_bound: bool
    jira_fixture_mode: str


def verify_deployed_journey(
    run_id: uuid.UUID,
    *,
    release_not_before: datetime,
) -> DeployedEvidenceSummary:
    if run_id == DEMO_PROPOSED_POLICY_ANALYSIS_RUN_ID:
        raise DeployedEvidenceError("live_run_must_not_be_seeded_fixture")
    if release_not_before.tzinfo is None:
        raise DeployedEvidenceError("release_timestamp_must_include_timezone")
    release_boundary = release_not_before.astimezone(UTC)

    with SessionLocal() as session:
        live_timeline = get_audit_timeline(session, run_id)
        fixture_timeline = get_audit_timeline(session, DEMO_PROPOSED_POLICY_ANALYSIS_RUN_ID)

    analysis_requested = next(
        entry
        for entry in live_timeline.entries
        if entry.event_type == AuditEventType.ANALYSIS_REQUESTED
    )
    if analysis_requested.occurred_at.astimezone(UTC) < release_boundary:
        raise DeployedEvidenceError("live_run_predates_deployed_task")

    event_types = {entry.event_type for entry in live_timeline.entries}
    missing = REQUIRED_LIVE_EVENTS - event_types
    if missing:
        names = ",".join(sorted(event.value for event in missing))
        raise DeployedEvidenceError(f"live_journey_incomplete:{names}")

    decisions = [
        entry
        for entry in live_timeline.entries
        if entry.event_type == AuditEventType.HUMAN_ACTION_DECISION_RECORDED
    ]
    decision_identities = {entry.actor_identity for entry in decisions}
    if (
        not decisions
        or any(
            entry.actor_category != AuditActorCategory.HUMAN
            or not entry.actor_identity
            or entry.metadata.get("reviewer_role") != "reviewer"
            for entry in decisions
        )
        or len(decision_identities) != 1
    ):
        raise DeployedEvidenceError("reviewer_evidence_invalid")

    prepared = [
        entry
        for entry in live_timeline.entries
        if entry.event_type == AuditEventType.EXECUTION_COMMAND_PREPARED
    ]
    requested = [
        entry
        for entry in live_timeline.entries
        if entry.event_type == AuditEventType.EXECUTION_REQUESTED
    ]
    prepared_identities = {entry.actor_identity for entry in prepared}
    requested_identities = {entry.actor_identity for entry in requested}
    if not prepared or None in prepared_identities or len(prepared_identities) != 1:
        raise DeployedEvidenceError("command_preparer_evidence_invalid")
    if (
        not requested
        or any(
            entry.actor_category != AuditActorCategory.HUMAN
            or not entry.actor_identity
            or entry.metadata.get("attempted_role") != "admin"
            for entry in requested
        )
        or requested_identities != prepared_identities
    ):
        raise DeployedEvidenceError("execution_actor_evidence_invalid")
    if not all(entry.artifact.artifact_id for entry in live_timeline.entries):
        raise DeployedEvidenceError("live_audit_provenance_incomplete")

    fixture_events = {entry.event_type for entry in fixture_timeline.entries}
    if AuditEventType.JIRA_ISSUE_CREATED not in fixture_events:
        raise DeployedEvidenceError("deterministic_jira_fixture_missing")

    approval = next(
        entry
        for entry in live_timeline.entries
        if entry.event_type == AuditEventType.APPROVAL_COMPLETED
    )
    return DeployedEvidenceSummary(
        status="verified",
        policy_analysis_run_id=str(run_id),
        approval_run_id=approval.artifact.artifact_id,
        event_count=len(live_timeline.entries),
        human_decision_count=len(decisions),
        execution_request_count=len(requested),
        release_bound=True,
        jira_fixture_mode="deterministic_simulation",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True, type=uuid.UUID)
    parser.add_argument(
        "--release-not-before",
        required=True,
        type=lambda value: datetime.fromisoformat(value.replace("Z", "+00:00")),
    )
    args = parser.parse_args()
    try:
        summary = verify_deployed_journey(
            args.run_id,
            release_not_before=args.release_not_before,
        )
    except Exception as error:
        code = str(error)
        if not isinstance(error, DeployedEvidenceError):
            code = "deployed_evidence_check_failed"
        print(json.dumps({"status": "failed", "failure_code": code}, sort_keys=True))
        return 1
    print(json.dumps(asdict(summary), sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
