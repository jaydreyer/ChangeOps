import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError

from changeops.db.models import (
    ActionReview,
    ExecutionCommand,
    ExecutionResult,
    ProposedAction,
    SimulatedLearningAssignment,
)
from changeops.db.session import SessionLocal
from changeops.services.learning_execution_service import (
    ExecutionActorNotAuthorizedError,
    ExecutionCommandIneligibleError,
    ExecutionOutcome,
    execute_command,
)
from tests.integration.test_execution_commands_api import (
    ADMIN_HEADERS,
    _complete_run,
)


def _prepared_command(client) -> tuple[dict, dict]:
    assessment, run = _complete_run(client, approve_training_only=True)
    prepared = client.post(
        f"/api/v1/action-approval-runs/{run['id']}/execution-commands",
        headers=ADMIN_HEADERS,
    )
    assert prepared.status_code == 201, prepared.text
    return assessment, prepared.json()["commands"][0]


def test_supported_command_executes_and_preserves_lineage(client) -> None:
    assessment, command_before = _prepared_command(client)
    execute_url = f"/api/v1/execution-commands/{command_before['id']}/execute"

    with SessionLocal() as session:
        command_row = session.get(ExecutionCommand, uuid.UUID(command_before["id"]))
        review_row = session.get(ActionReview, command_row.action_review_id)
        action_row = session.get(ProposedAction, command_row.proposed_action_id)
        immutable_before = (
            command_row.parameters_snapshot,
            command_row.effective_action_snapshot,
            command_row.status,
            review_row.status,
            tuple(
                (decision.id, decision.decision, decision.rationale)
                for decision in review_row.decisions
            ),
            action_row.execution_status,
        )

    response = client.post(execute_url, headers=ADMIN_HEADERS)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "succeeded"
    assert body["outcome_code"] == "training_assignment_created"
    assignment = body["learning_assignment"]
    assert assignment["worker_id"] == command_before["target_identifier"]
    assert assignment["training_course_id"] == "international-travel-security"
    assert assignment["source_execution_command_id"] == command_before["id"]
    assert assignment["source_approved_action_id"] == command_before["proposed_action_id"]
    assert assignment["assignment_status"] == "assigned"

    detail = client.get(f"/api/v1/execution-commands/{command_before['id']}")
    assert detail.status_code == 200
    assert detail.json()["execution_state"] == "executed"
    assert detail.json()["execution_results"] == [body]

    with SessionLocal() as session:
        command_row = session.get(ExecutionCommand, uuid.UUID(command_before["id"]))
        review_row = session.get(ActionReview, command_row.action_review_id)
        action_row = session.get(ProposedAction, command_row.proposed_action_id)
        immutable_after = (
            command_row.parameters_snapshot,
            command_row.effective_action_snapshot,
            command_row.status,
            review_row.status,
            tuple(
                (decision.id, decision.decision, decision.rationale)
                for decision in review_row.decisions
            ),
            action_row.execution_status,
        )
        result = session.get(ExecutionResult, uuid.UUID(body["id"]))
        persisted_assignment = session.get(
            SimulatedLearningAssignment,
            uuid.UUID(assignment["id"]),
        )
        assert result.execution_command_id == command_row.id
        assert result.simulated_learning_assignment_id == persisted_assignment.id
        assert command_row.assessment_id == uuid.UUID(assessment["id"])
    assert immutable_after == immutable_before


def test_repeated_execution_records_replay_and_creates_one_assignment(client) -> None:
    _, command = _prepared_command(client)
    url = f"/api/v1/execution-commands/{command['id']}/execute"

    first = client.post(url, headers=ADMIN_HEADERS)
    repeated = client.post(url, headers=ADMIN_HEADERS)

    assert first.status_code == 201
    assert repeated.status_code == 200
    assert repeated.json()["status"] == "already_applied"
    assert repeated.json()["learning_assignment"]["id"] == first.json()["learning_assignment"]["id"]
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(SimulatedLearningAssignment)) == 1
        assert session.scalar(select(func.count()).select_from(ExecutionResult)) == 2


def test_concurrent_execution_has_one_side_effect_and_deterministic_replay(client) -> None:
    _, command = _prepared_command(client)
    command_id = uuid.UUID(command["id"])
    barrier = Barrier(2)

    def execute(index: int) -> str:
        barrier.wait()
        with SessionLocal() as session:
            return execute_command(
                session,
                command_id,
                actor_identity=f"operator-{index}@example.com",
                actor_role="admin",
            ).result.status

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(execute, range(2)))

    assert sorted(statuses) == ["already_applied", "succeeded"]
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(SimulatedLearningAssignment)) == 1
        assert session.scalar(select(func.count()).select_from(ExecutionResult)) == 2


def test_database_uniqueness_and_immutability_protect_execution_history(client) -> None:
    _, command = _prepared_command(client)
    created = client.post(
        f"/api/v1/execution-commands/{command['id']}/execute",
        headers=ADMIN_HEADERS,
    ).json()
    assignment = created["learning_assignment"]

    with pytest.raises(DBAPIError), SessionLocal.begin() as session:
        session.execute(
            text(
                """
                INSERT INTO simulated_learning_assignments (
                    id, worker_id, training_course_id, source_execution_command_id,
                    source_approved_action_id, assignment_status, assigned_at, created_at
                )
                VALUES (
                    :id, :worker_id, :course_id, :command_id,
                    :action_id, 'assigned', NOW(), NOW()
                )
                """
            ),
            {
                "id": uuid.uuid4(),
                "worker_id": assignment["worker_id"],
                "course_id": assignment["training_course_id"],
                "command_id": assignment["source_execution_command_id"],
                "action_id": assignment["source_approved_action_id"],
            },
        )
    with pytest.raises(DBAPIError), SessionLocal.begin() as session:
        session.execute(
            text("UPDATE execution_results SET message = 'changed' WHERE id = :id"),
            {"id": created["id"]},
        )
    with pytest.raises(DBAPIError), SessionLocal.begin() as session:
        session.execute(
            text("DELETE FROM simulated_learning_assignments WHERE id = :id"),
            {"id": assignment["id"]},
        )


def test_execution_api_rejects_missing_or_unauthorized_command(client) -> None:
    missing = client.post(
        f"/api/v1/execution-commands/{uuid.uuid4()}/execute",
        headers=ADMIN_HEADERS,
    )
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "execution_command_not_found"

    _, command = _prepared_command(client)
    unauthorized = client.post(f"/api/v1/execution-commands/{command['id']}/execute")
    assert unauthorized.status_code == 403
    assert unauthorized.json()["detail"]["code"] == "execution_actor_not_authorized"

    with pytest.raises(ExecutionActorNotAuthorizedError), SessionLocal() as session:
        execute_command(
            session,
            uuid.UUID(command["id"]),
            actor_identity="viewer@example.com",
            actor_role="viewer",
        )
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(ExecutionResult)) == 0
        assert session.scalar(select(func.count()).select_from(SimulatedLearningAssignment)) == 0


def test_execution_api_returns_explicit_ineligible_error(client, monkeypatch) -> None:
    def reject(*args, **kwargs):
        raise ExecutionCommandIneligibleError("Approval lineage is not eligible.")

    monkeypatch.setattr(
        "changeops.api.execution_commands.execute_command",
        reject,
    )
    response = client.post(
        f"/api/v1/execution-commands/{uuid.uuid4()}/execute",
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == {
        "code": "execution_command_ineligible",
        "message": "Approval lineage is not eligible.",
    }


@pytest.mark.parametrize(
    ("result_status", "outcome_code"),
    [
        ("rejected_unsupported", "unsupported_execution_command"),
        ("failed_validation", "invalid_execution_command_payload"),
    ],
)
def test_execution_api_returns_persisted_adapter_error(
    client,
    monkeypatch,
    result_status: str,
    outcome_code: str,
) -> None:
    command_id = uuid.uuid4()
    result = ExecutionResult(
        id=uuid.uuid4(),
        execution_command_id=command_id,
        status=result_status,
        outcome_code=outcome_code,
        message="The command cannot be executed.",
        command_idempotency_key="a" * 64,
        attempted_by="operator@example.com",
        attempted_role="admin",
        created_at="2026-08-02T12:00:00+00:00",
        learning_assignment=None,
    )
    monkeypatch.setattr(
        "changeops.api.execution_commands.execute_command",
        lambda *args, **kwargs: ExecutionOutcome(result=result, assignment=None),
    )

    response = client.post(
        f"/api/v1/execution-commands/{command_id}/execute",
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == outcome_code
    assert response.json()["detail"]["execution_result"]["status"] == result_status
