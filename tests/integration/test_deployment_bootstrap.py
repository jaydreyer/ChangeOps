from changeops.db.session import SessionLocal
from changeops.deployment_bootstrap import (
    REQUIRED_FIXTURE_EVENTS,
    bootstrap_demo_fixture,
)
from changeops.services.audit_timeline_projection_service import get_audit_timeline
from changeops.services.demo_assessment_seed_service import (
    DEMO_PROPOSED_POLICY_ANALYSIS_RUN_ID,
)


def test_deployment_bootstrap_is_idempotent_fixture_setup() -> None:
    first = bootstrap_demo_fixture()
    second = bootstrap_demo_fixture()

    assert first == second
    assert first.status == "initialized"
    assert first.jira_mode == "deterministic_simulation"
    with SessionLocal() as session:
        timeline = get_audit_timeline(session, DEMO_PROPOSED_POLICY_ANALYSIS_RUN_ID)
    assert {entry.event_type.value for entry in timeline.entries} >= REQUIRED_FIXTURE_EVENTS
