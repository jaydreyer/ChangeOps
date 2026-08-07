"""Idempotent setup and validation of the fictional demo fixture."""

import json
import sys
from dataclasses import asdict, dataclass

from changeops.db.session import SessionLocal
from changeops.services.audit_timeline_projection_service import get_audit_timeline
from changeops.services.demo_assessment_seed_service import (
    DEMO_PROPOSED_POLICY_ANALYSIS_RUN_ID,
)
from changeops.services.demo_audit_timeline_seed_service import seed_demo_audit_timeline
from changeops.services.seed_service import seed_database

REQUIRED_FIXTURE_EVENTS = {
    "extraction_attempted",
    "extraction_accepted",
    "impact_assessment_completed",
    "comparison_created",
    "impact_delta_created",
    "human_action_decision_recorded",
    "approval_completed",
    "execution_command_prepared",
    "execution_requested",
    "execution_succeeded",
    "jira_issue_created",
    "execution_replay_prevented",
}


@dataclass(frozen=True)
class DeploymentBootstrapSummary:
    status: str
    policy_analysis_run_id: str
    approval_run_id: str
    event_count: int
    jira_mode: str


def bootstrap_demo_fixture() -> DeploymentBootstrapSummary:
    with SessionLocal.begin() as session:
        seed_database(session)
    with SessionLocal() as session:
        approval_run_id = seed_demo_audit_timeline(session)
        timeline = get_audit_timeline(session, DEMO_PROPOSED_POLICY_ANALYSIS_RUN_ID)

    event_types = {entry.event_type.value for entry in timeline.entries}
    missing = REQUIRED_FIXTURE_EVENTS - event_types
    if missing:
        raise RuntimeError(f"demo_fixture_incomplete:{','.join(sorted(missing))}")
    if not any(
        entry.event_type.value == "human_action_decision_recorded"
        and entry.actor_category.value == "human"
        for entry in timeline.entries
    ):
        raise RuntimeError("demo_fixture_human_decision_missing")
    if not all(entry.artifact.artifact_id for entry in timeline.entries):
        raise RuntimeError("demo_fixture_audit_provenance_incomplete")

    return DeploymentBootstrapSummary(
        status="initialized",
        policy_analysis_run_id=str(DEMO_PROPOSED_POLICY_ANALYSIS_RUN_ID),
        approval_run_id=str(approval_run_id),
        event_count=len(timeline.entries),
        jira_mode="deterministic_simulation",
    )


def main() -> int:
    try:
        summary = bootstrap_demo_fixture()
    except Exception as error:
        code = str(error)
        if not code.startswith("demo_fixture_"):
            code = "demo_fixture_bootstrap_failed"
        print(json.dumps({"status": "failed", "failure_code": code}, sort_keys=True))
        return 1
    print(json.dumps(asdict(summary), sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
