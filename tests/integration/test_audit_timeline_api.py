import uuid

from sqlalchemy import select

from changeops.adapters.jira import JiraCloudAdapter, JiraIssueReceipt
from changeops.api.policy_extractions import extraction_model_dependency
from changeops.config import get_settings
from changeops.db.models import ActionApprovalRun, ExecutionCommand
from changeops.db.session import SessionLocal
from changeops.services.demo_assessment_seed_service import (
    DEMO_PROPOSED_POLICY_ANALYSIS_RUN_ID,
)
from changeops.services.demo_reset_service import reset_demo_workflows
from changeops.services.seed_service import POLICY_CHANGE_ID
from tests.integration.test_execution_commands_api import ADMIN_HEADERS
from tests.integration.test_jira_execution_api import _prepared_jira_command
from tests.integration.test_policy_extraction_api import (
    configured_fixture_model,
)


def test_completed_journey_returns_stable_ordered_read_projection(client) -> None:
    client.app.dependency_overrides[extraction_model_dependency] = lambda: (
        configured_fixture_model()
    )
    run = client.post(
        "/api/v1/policy-analysis-runs",
        json={"policy_change_id": POLICY_CHANGE_ID},
    ).json()

    first = client.get(f"/api/v1/policy-analysis-runs/{run['id']}/audit-timeline")
    second = client.get(f"/api/v1/policy-analysis-runs/{run['id']}/audit-timeline")

    assert first.status_code == 200
    assert second.json() == first.json()
    body = first.json()
    assert body["subject_type"] == "policy_analysis_run"
    assert body["subject_id"] == run["id"]
    event_types = [entry["event_type"] for entry in body["entries"]]
    assert "extraction_attempted" in event_types
    assert "extraction_accepted" in event_types
    assert "impact_assessment_completed" in event_types
    assert [entry["occurred_at"] for entry in body["entries"]] == sorted(
        entry["occurred_at"] for entry in body["entries"]
    )
    assert all(entry["artifact"]["artifact_id"] for entry in body["entries"])
    extraction_entries = [
        entry
        for entry in body["entries"]
        if entry["artifact"]["artifact_type"] == ("policy_extraction_attempt")
    ]
    assert {entry["actor_category"] for entry in extraction_entries} == {
        "ai_assisted",
        "deterministic_system",
    }


def test_unknown_timeline_uses_standard_not_found_and_has_no_mutation_endpoint(client) -> None:
    run_id = uuid.uuid4()
    url = f"/api/v1/policy-analysis-runs/{run_id}/audit-timeline"

    missing = client.get(url)

    assert missing.status_code == 404
    assert missing.json()["detail"] == {
        "code": "audit_timeline_not_found",
        "message": "Policy analysis audit timeline was not found.",
    }
    assert client.post(url).status_code == 405


def test_demo_reset_produces_complete_repeatable_flagship_timeline(client) -> None:
    with SessionLocal() as session:
        first_summary = reset_demo_workflows(session)
    first = client.get(
        f"/api/v1/policy-analysis-runs/{DEMO_PROPOSED_POLICY_ANALYSIS_RUN_ID}/audit-timeline"
    )
    with SessionLocal() as session:
        second_summary = reset_demo_workflows(session)
    second = client.get(
        f"/api/v1/policy-analysis-runs/{DEMO_PROPOSED_POLICY_ANALYSIS_RUN_ID}/audit-timeline"
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first_summary == second_summary
    required = {
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
    assert required <= {entry["event_type"] for entry in first.json()["entries"]}
    assert required <= {entry["event_type"] for entry in second.json()["entries"]}
    assert all(entry["artifact"]["artifact_id"] for entry in second.json()["entries"])


def test_flagship_jira_execution_and_replay_are_visible(client, monkeypatch) -> None:
    monkeypatch.setenv("JIRA_BASE_URL", "https://acme.atlassian.net")
    monkeypatch.setenv("JIRA_EMAIL", "operator@example.com")
    monkeypatch.setenv("JIRA_API_TOKEN", "test-token")
    monkeypatch.setenv("JIRA_PROJECT_ID_OR_KEY", "ECM")
    monkeypatch.setenv("JIRA_ISSUE_TYPE_ID", "10001")
    get_settings.cache_clear()

    def create_issue(self, parameters):
        return JiraIssueReceipt(
            issue_id="10101",
            issue_key="ECM-42",
            api_url="https://acme.atlassian.net/rest/api/3/issue/10101",
            browse_url="https://acme.atlassian.net/browse/ECM-42",
        )

    monkeypatch.setattr(JiraCloudAdapter, "create_issue", create_issue)
    command = _prepared_jira_command(client)
    url = f"/api/v1/execution-commands/{command['id']}/execute"
    assert client.post(url, headers=ADMIN_HEADERS).status_code == 201
    assert client.post(url, headers=ADMIN_HEADERS).status_code == 200

    with SessionLocal() as session:
        persisted_command = session.get(ExecutionCommand, uuid.UUID(command["id"]))
        run_id = session.scalar(
            select(ActionApprovalRun.policy_analysis_run_id).where(
                ActionApprovalRun.id == persisted_command.approval_run_id
            )
        )
    timeline = client.get(f"/api/v1/policy-analysis-runs/{run_id}/audit-timeline")

    assert timeline.status_code == 200
    entries = timeline.json()["entries"]
    event_types = {entry["event_type"] for entry in entries}
    assert {
        "human_action_decision_recorded",
        "approval_completed",
        "execution_command_prepared",
        "execution_requested",
        "execution_succeeded",
        "jira_issue_created",
        "execution_replay_prevented",
    } <= event_types
    decisions = [
        entry for entry in entries if entry["event_type"] == "human_action_decision_recorded"
    ]
    assert all(entry["actor_identity"] == "reviewer@example.com" for entry in decisions)
    jira = next(entry for entry in entries if entry["event_type"] == "jira_issue_created")
    assert jira["metadata"]["issue_key"] == "ECM-42"
    assert jira["artifact"]["href"] == "https://acme.atlassian.net/browse/ECM-42"
    get_settings.cache_clear()
