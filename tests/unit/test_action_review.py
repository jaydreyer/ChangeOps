import uuid
from datetime import UTC, date, datetime

import pytest

from changeops.domain.action_review import (
    EditedActionSnapshot,
    OriginalActionSnapshot,
    ReviewActor,
    ReviewDecisionInput,
    ReviewValidationError,
    derive_effective_approved_action,
    validate_review_decision,
)

DECISION_TIME = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)


@pytest.fixture
def original_action() -> OriginalActionSnapshot:
    return OriginalActionSnapshot(
        proposed_action_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        assessment_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        finding_id=None,
        enterprise_impact_id=uuid.UUID("00000000-0000-0000-0000-000000000003"),
        worker_id="worker-1",
        action_type="training_assignment",
        target_type="training_course",
        target_identifier="course-1",
        description="Assign the travel course.",
        due_date=date(2026, 8, 20),
        execution_status="not_executed",
    )


@pytest.mark.parametrize(
    ("decision", "edited_action"),
    [
        ("approved", None),
        ("approved", {"description": "Assign the updated travel course."}),
        ("approved", {"due_date": "2026-08-25"}),
        ("rejected", None),
        ("deferred", None),
        ("revision_requested", None),
    ],
)
def test_valid_review_decisions(
    original_action: OriginalActionSnapshot,
    decision: str,
    edited_action: dict[str, object] | None,
) -> None:
    validated = validate_review_decision(
        review_status="pending",
        original_action=original_action,
        request=ReviewDecisionInput(
            decision=decision,
            rationale="  Documented reviewer rationale.  ",
            edited_action=edited_action,
        ),
        actor=ReviewActor(identity=" reviewer@example.com ", role="reviewer"),
        decision_time=DECISION_TIME,
    )

    assert validated.decision == decision
    assert validated.reviewer_identity == "reviewer@example.com"
    assert validated.rationale == "Documented reviewer rationale."


@pytest.mark.parametrize(
    ("decision_request", "actor", "status", "code"),
    [
        (
            ReviewDecisionInput(decision="approved", rationale=" "),
            ReviewActor(identity="reviewer@example.com", role="reviewer"),
            "pending",
            "invalid_review_decision",
        ),
        (
            ReviewDecisionInput(decision="approved", rationale="Okay"),
            ReviewActor(identity="reviewer@example.com", role="viewer"),
            "pending",
            "reviewer_not_authorized",
        ),
        (
            ReviewDecisionInput(
                decision="rejected",
                rationale="No",
                edited_action={"description": "Changed"},
            ),
            ReviewActor(identity="reviewer@example.com", role="reviewer"),
            "pending",
            "invalid_action_edit",
        ),
        (
            ReviewDecisionInput(
                decision="approved",
                rationale="Okay",
                edited_action={"action_type": "update_document"},
            ),
            ReviewActor(identity="reviewer@example.com", role="reviewer"),
            "pending",
            "invalid_action_edit",
        ),
        (
            ReviewDecisionInput(
                decision="approved",
                rationale="Okay",
                edited_action={"target_identifier": "other-target"},
            ),
            ReviewActor(identity="reviewer@example.com", role="reviewer"),
            "pending",
            "invalid_action_edit",
        ),
        (
            ReviewDecisionInput(
                decision="approved",
                rationale="Okay",
                edited_action={"description": " "},
            ),
            ReviewActor(identity="reviewer@example.com", role="reviewer"),
            "pending",
            "invalid_action_edit",
        ),
        (
            ReviewDecisionInput(
                decision="approved",
                rationale="Okay",
                edited_action={"due_date": "not-a-date"},
            ),
            ReviewActor(identity="reviewer@example.com", role="reviewer"),
            "pending",
            "invalid_action_edit",
        ),
        (
            ReviewDecisionInput(
                decision="approved",
                rationale="Okay",
                edited_action={"due_date": "2026-07-31"},
            ),
            ReviewActor(identity="reviewer@example.com", role="reviewer"),
            "pending",
            "invalid_action_edit",
        ),
        (
            ReviewDecisionInput(
                decision="approved",
                rationale="Okay",
                edited_action={"description": "Assign the travel course."},
            ),
            ReviewActor(identity="reviewer@example.com", role="reviewer"),
            "pending",
            "invalid_action_edit",
        ),
        (
            ReviewDecisionInput(decision="approved", rationale="Again"),
            ReviewActor(identity="reviewer@example.com", role="reviewer"),
            "approved",
            "action_review_already_decided",
        ),
    ],
)
def test_invalid_review_decisions(
    original_action: OriginalActionSnapshot,
    decision_request: ReviewDecisionInput,
    actor: ReviewActor,
    status: str,
    code: str,
) -> None:
    with pytest.raises(ReviewValidationError) as captured:
        validate_review_decision(
            review_status=status,
            original_action=original_action,
            request=decision_request,
            actor=actor,
            decision_time=DECISION_TIME,
        )
    assert captured.value.code == code


def test_effective_approved_action_is_derived_without_mutating_original(
    original_action: OriginalActionSnapshot,
) -> None:
    effective = derive_effective_approved_action(
        original_action,
        EditedActionSnapshot(
            description="Assign the updated travel course.",
            due_date=date(2026, 8, 25),
        ),
    )

    assert effective.description == "Assign the updated travel course."
    assert effective.due_date == date(2026, 8, 25)
    assert effective.action_type == original_action.action_type
    assert effective.target_identifier == original_action.target_identifier
    assert original_action.description == "Assign the travel course."
    assert (
        OriginalActionSnapshot.model_validate_json(original_action.model_dump_json())
        == original_action
    )
