import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from changeops.db.models import ActionApprovalRun, ExecutionCommand
from changeops.db.session import SessionLocal
from changeops.deployment_bootstrap import bootstrap_demo_fixture
from changeops.evaluation.deployed_evidence import (
    DeployedEvidenceError,
    verify_deployed_journey,
)
from changeops.services.demo_assessment_seed_service import (
    DEMO_PROPOSED_POLICY_ANALYSIS_RUN_ID,
)
from tests.integration.test_execution_commands_api import ADMIN_HEADERS
from tests.integration.test_learning_execution_api import _prepared_command


def test_verifies_nonseeded_human_journey_and_fixture_jira(client) -> None:
    bootstrap_demo_fixture()
    _, command = _prepared_command(client)
    executed = client.post(
        f"/api/v1/execution-commands/{command['id']}/execute",
        headers=ADMIN_HEADERS,
    )
    assert executed.status_code == 201

    with SessionLocal() as session:
        command_row = session.get(ExecutionCommand, uuid.UUID(command["id"]))
        run_id = session.scalar(
            select(ActionApprovalRun.policy_analysis_run_id).where(
                ActionApprovalRun.id == command_row.approval_run_id
            )
        )

    summary = verify_deployed_journey(
        run_id,
        release_not_before=datetime.now(UTC) - timedelta(minutes=5),
    )

    assert summary.status == "verified"
    assert summary.policy_analysis_run_id == str(run_id)
    assert summary.jira_fixture_mode == "deterministic_simulation"


def test_rejects_seeded_fixture_as_live_evidence() -> None:
    bootstrap_demo_fixture()

    with pytest.raises(
        DeployedEvidenceError,
        match="live_run_must_not_be_seeded_fixture",
    ):
        verify_deployed_journey(
            DEMO_PROPOSED_POLICY_ANALYSIS_RUN_ID,
            release_not_before=datetime.now(UTC) - timedelta(minutes=5),
        )


def test_rejects_journey_that_predates_deployed_task(client) -> None:
    bootstrap_demo_fixture()
    _, command = _prepared_command(client)
    executed = client.post(
        f"/api/v1/execution-commands/{command['id']}/execute",
        headers=ADMIN_HEADERS,
    )
    assert executed.status_code == 201

    with SessionLocal() as session:
        command_row = session.get(ExecutionCommand, uuid.UUID(command["id"]))
        run_id = session.scalar(
            select(ActionApprovalRun.policy_analysis_run_id).where(
                ActionApprovalRun.id == command_row.approval_run_id
            )
        )

    with pytest.raises(DeployedEvidenceError, match="live_run_predates_deployed_task"):
        verify_deployed_journey(
            run_id,
            release_not_before=datetime.now(UTC) + timedelta(minutes=1),
        )
