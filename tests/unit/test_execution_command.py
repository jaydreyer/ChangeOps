import uuid
from datetime import date

from changeops.domain.action_review import OriginalActionSnapshot
from changeops.domain.execution_command import (
    command_idempotency_key,
    map_effective_action,
    snapshot_effective_action,
)


def _action(**overrides) -> OriginalActionSnapshot:
    values = {
        "proposed_action_id": uuid.UUID("11111111-1111-1111-1111-111111111111"),
        "assessment_id": uuid.UUID("22222222-2222-2222-2222-222222222222"),
        "finding_id": uuid.UUID("33333333-3333-3333-3333-333333333333"),
        "enterprise_impact_id": None,
        "worker_id": "worker-sarah-johnson",
        "action_type": "training_assignment",
        "target_type": "worker",
        "target_identifier": "worker-sarah-johnson",
        "description": "Assign the approved course.",
        "due_date": date(2026, 9, 15),
        "execution_status": "not_executed",
    }
    values.update(overrides)
    return OriginalActionSnapshot.model_validate(values)


def test_training_assignment_maps_to_learning_command() -> None:
    result = map_effective_action(_action())

    assert result.unsupported is None
    assert result.command is not None
    assert result.command.model_dump(mode="json") == {
        "schema_version": "execution-command-v1",
        "system": "learning",
        "operation": "assign_training",
        "target_type": "worker",
        "target_identifier": "worker-sarah-johnson",
        "parameters": {
            "course_identifier": "international-travel-security",
            "description": "Assign the approved course.",
            "due_date": "2026-09-15",
            "worker_identifier": "worker-sarah-johnson",
        },
    }


def test_approved_edits_are_command_values() -> None:
    result = map_effective_action(
        _action(description="Assign with approved wording.", due_date=date(2026, 9, 20))
    )

    assert result.command is not None
    assert result.command.parameters["description"] == "Assign with approved wording."
    assert result.command.parameters["due_date"] == "2026-09-20"


def test_unsupported_action_and_target_are_explicit() -> None:
    unsupported_action = map_effective_action(_action(action_type="review_team_travel"))
    unsupported_target = map_effective_action(_action(target_type="team"))

    assert unsupported_action.unsupported is not None
    assert unsupported_action.unsupported.code == "unsupported_action_type"
    assert unsupported_target.unsupported is not None
    assert unsupported_target.unsupported.code == "unsupported_target_type"


def test_effective_snapshot_has_its_own_stable_schema() -> None:
    snapshot = snapshot_effective_action(_action())

    assert snapshot.schema_version == "effective-approved-action-v1"
    assert snapshot.due_date == "2026-09-15"
    assert snapshot.execution_status == "not_executed"


def test_fingerprint_is_canonical_and_changes_with_semantics() -> None:
    first = map_effective_action(_action()).command
    equivalent = map_effective_action(_action()).command
    changed = map_effective_action(_action(description="Changed approved wording.")).command
    assert first is not None and equivalent is not None and changed is not None

    key = command_idempotency_key(approval_decision_id="decision-1", command=first)
    assert key == command_idempotency_key(
        approval_decision_id="decision-1",
        command=equivalent,
    )
    assert key != command_idempotency_key(
        approval_decision_id="decision-1",
        command=changed,
    )
    assert key != command_idempotency_key(
        approval_decision_id="decision-2",
        command=first,
    )
