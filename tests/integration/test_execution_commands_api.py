import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError

from changeops.db.models import ExecutionCommand, ProposedAction
from changeops.db.session import SessionLocal
from changeops.services.execution_command_service import prepare_execution_commands
from tests.integration.test_action_approval_api import REVIEWER_HEADERS, _create_run

ADMIN_HEADERS = {
    "X-ChangeOps-Actor": "operator@example.com",
    "X-ChangeOps-Role": "admin",
}


def _complete_run(client, *, approve_training_only: bool = False) -> tuple[dict, dict]:
    assessment, run = _create_run(client)
    workbench = client.get(f"/api/v1/action-approval-runs/{run['id']}/workbench").json()
    for item in workbench["items"]:
        action = item["review"]["original_action"]
        decision = (
            "approved"
            if not approve_training_only or action["action_type"] == "training_assignment"
            else "deferred"
        )
        payload = {
            "decision": decision,
            "rationale": f"Fixture decision for {action['action_type']}.",
        }
        if decision == "approved" and action["action_type"] == "training_assignment":
            payload["edited_action"] = {
                "description": f"Approved: {action['description']}",
            }
        response = client.post(
            f"/api/v1/action-reviews/{item['review']['id']}/decisions",
            headers=REVIEWER_HEADERS,
            json=payload,
        )
        assert response.status_code == 201, response.text
    completed = client.get(f"/api/v1/action-approval-runs/{run['id']}").json()
    assert completed["status"] == "completed"
    return assessment, completed


def test_preparation_requires_admin_and_completed_run(client) -> None:
    _, run = _create_run(client)
    url = f"/api/v1/action-approval-runs/{run['id']}/execution-commands"

    assert client.post(url).status_code == 403
    not_completed = client.post(url, headers=ADMIN_HEADERS)
    assert not_completed.status_code == 422
    assert not_completed.json()["detail"]["code"] == "approval_run_not_completed"


def test_prepare_commands_is_ordered_visible_and_idempotent(client) -> None:
    assessment, run = _complete_run(client)
    url = f"/api/v1/action-approval-runs/{run['id']}/execution-commands"

    before = client.get(url)
    assert before.status_code == 200
    assert before.json()["approved_action_count"] == 13
    assert before.json()["eligible_action_count"] == 2
    assert before.json()["prepared_command_count"] == 0
    assert before.json()["unsupported_approved_action_count"] == 11

    created = client.post(url, headers=ADMIN_HEADERS)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["execution_performed"] is False
    assert body["approved_action_count"] == 13
    assert body["eligible_action_count"] == 2
    assert body["prepared_command_count"] == 2
    assert body["unsupported_approved_action_count"] == 11
    assert [item["sequence"] for item in body["commands"]] == sorted(
        item["sequence"] for item in body["commands"]
    )
    assert [item["sequence"] for item in body["unsupported_items"]] == sorted(
        item["sequence"] for item in body["unsupported_items"]
    )
    assert all(item["status"] == "pending_execution" for item in body["commands"])
    assert all(item["execution_performed"] is False for item in body["commands"])
    assert all(item["system"] == "learning" for item in body["commands"])
    assert all(item["operation"] == "assign_training" for item in body["commands"])
    assert all(
        item["effective_action"]["description"].startswith("Approved:") for item in body["commands"]
    )
    assert all(
        item["effective_action"]["execution_status"] == "not_executed" for item in body["commands"]
    )

    repeated = client.post(url, headers=ADMIN_HEADERS)
    assert repeated.status_code == 200
    assert repeated.json() == body
    assert client.get(url).json() == body
    detail = client.get(f"/api/v1/execution-commands/{body['commands'][0]['id']}")
    assert detail.status_code == 200
    assert detail.json() == body["commands"][0]

    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(ExecutionCommand)) == 2
        actions = list(
            session.scalars(
                select(ProposedAction).where(
                    ProposedAction.assessment_id == uuid.UUID(assessment["id"])
                )
            )
        )
        assert all(action.execution_status == "not_executed" for action in actions)


def test_nonapproved_actions_never_prepare_and_request_cannot_override(client) -> None:
    _, run = _complete_run(client, approve_training_only=True)
    url = f"/api/v1/action-approval-runs/{run['id']}/execution-commands"

    override = client.post(
        url,
        headers=ADMIN_HEADERS,
        json={"description": "Caller-controlled override"},
    )
    assert override.status_code == 422

    result = client.post(url, headers=ADMIN_HEADERS)
    assert result.status_code == 201
    assert result.json()["approved_action_count"] == 2
    assert result.json()["prepared_command_count"] == 2
    assert result.json()["unsupported_approved_action_count"] == 0


def test_concurrent_preparation_has_one_database_winner(client) -> None:
    _, run = _complete_run(client, approve_training_only=True)
    run_id = uuid.UUID(run["id"])
    barrier = Barrier(2)

    def prepare(index: int) -> int:
        barrier.wait()
        with SessionLocal() as session:
            result = prepare_execution_commands(
                session,
                run_id,
                actor_identity=f"operator-{index}@example.com",
                actor_role="admin",
            )
            return result.created_count

    with ThreadPoolExecutor(max_workers=2) as executor:
        created_counts = list(executor.map(prepare, range(2)))

    assert sorted(created_counts) == [0, 2]
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(ExecutionCommand)) == 2


def test_execution_command_rows_are_database_immutable(client) -> None:
    _, run = _complete_run(client, approve_training_only=True)
    body = client.post(
        f"/api/v1/action-approval-runs/{run['id']}/execution-commands",
        headers=ADMIN_HEADERS,
    ).json()
    command_id = body["commands"][0]["id"]

    with pytest.raises(DBAPIError), SessionLocal.begin() as session:
        session.execute(
            text("UPDATE execution_commands SET parameters_snapshot = '{}'::jsonb WHERE id = :id"),
            {"id": command_id},
        )
    with pytest.raises(DBAPIError), SessionLocal.begin() as session:
        session.execute(
            text("DELETE FROM execution_commands WHERE id = :id"),
            {"id": command_id},
        )
