import uuid
from unittest.mock import Mock

from pydantic import ValidationError

from changeops.db.models import ExecutionCommand
from changeops.domain.learning_execution import AssignTrainingParameters
from changeops.services.learning_execution_service import SimulatedLearningAdapter


def _command(**overrides) -> ExecutionCommand:
    values = {
        "id": uuid.uuid4(),
        "proposed_action_id": uuid.uuid4(),
        "system": "learning",
        "operation": "assign_training",
        "target_type": "worker",
        "target_identifier": "worker-1",
        "parameters_snapshot": {
            "worker_identifier": "worker-1",
            "course_identifier": "international-travel-security",
            "description": "Assign training.",
            "due_date": None,
        },
        "idempotency_key": "a" * 64,
    }
    values.update(overrides)
    return ExecutionCommand(**values)


def test_assign_training_parameters_reject_unknown_or_missing_values() -> None:
    try:
        AssignTrainingParameters.model_validate(
            {
                "worker_identifier": "worker-1",
                "course_identifier": "",
                "description": "Assign training.",
                "due_date": None,
                "invented": True,
            }
        )
    except ValidationError as error:
        assert {item["loc"] for item in error.errors()} == {
            ("course_identifier",),
            ("invented",),
        }
    else:
        raise AssertionError("Malformed assign-training parameters were accepted.")


def test_adapter_rejects_unsupported_command_without_side_effect() -> None:
    session = Mock()
    outcome = SimulatedLearningAdapter().assign_training(
        command=_command(system="knowledge", operation="publish"),
        session=session,
        actor_identity="operator@example.com",
        actor_role="admin",
    )

    assert outcome.result.status == "rejected_unsupported"
    assert outcome.result.outcome_code == "unsupported_execution_command"
    assert outcome.assignment is None
    session.get.assert_not_called()
    assert session.add.call_args.args[0] is outcome.result


def test_adapter_records_malformed_payload_without_side_effect() -> None:
    session = Mock()
    outcome = SimulatedLearningAdapter().assign_training(
        command=_command(parameters_snapshot={"worker_identifier": "worker-1"}),
        session=session,
        actor_identity="operator@example.com",
        actor_role="admin",
    )

    assert outcome.result.status == "failed_validation"
    assert outcome.result.outcome_code == "invalid_execution_command_payload"
    assert outcome.assignment is None
    session.get.assert_not_called()


def test_adapter_validates_target_before_looking_up_enterprise_records() -> None:
    session = Mock()
    outcome = SimulatedLearningAdapter().assign_training(
        command=_command(target_identifier="worker-2"),
        session=session,
        actor_identity="operator@example.com",
        actor_role="admin",
    )

    assert outcome.result.status == "failed_validation"
    assert outcome.result.outcome_code == "invalid_execution_command_target"
    assert outcome.assignment is None
    session.get.assert_not_called()
