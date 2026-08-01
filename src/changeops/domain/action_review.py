import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

ACTION_REVIEW_SCHEMA_VERSION = "action-review-v1"

ReviewStatus = Literal[
    "pending",
    "approved",
    "rejected",
    "deferred",
    "revision_requested",
]
ReviewDecision = Literal["approved", "rejected", "deferred", "revision_requested"]


class OriginalActionSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: Literal["action-review-v1"] = ACTION_REVIEW_SCHEMA_VERSION
    proposed_action_id: uuid.UUID
    assessment_id: uuid.UUID
    finding_id: uuid.UUID | None
    enterprise_impact_id: uuid.UUID | None
    worker_id: str | None
    action_type: str
    target_type: str
    target_identifier: str
    description: str
    due_date: date | None
    execution_status: Literal["not_executed"]


class ReviewContextSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    finding_id: uuid.UUID | None
    enterprise_impact_id: uuid.UUID | None
    reason_code: str | None
    evidence_keys: tuple[str, ...]


class EditedActionSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    description: str | None = None
    due_date: date | None = None


class ReviewActor(BaseModel):
    model_config = ConfigDict(frozen=True)

    identity: str
    role: str


class ReviewDecisionInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    decision: str
    rationale: str
    edited_action: dict[str, object] | None = None


class ValidatedReviewDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    decision: ReviewDecision
    reviewer_identity: str
    reviewer_role: Literal["reviewer", "admin"]
    rationale: str
    edited_action: EditedActionSnapshot | None


class ReviewValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def validate_review_decision(
    *,
    review_status: str,
    original_action: OriginalActionSnapshot,
    request: ReviewDecisionInput,
    actor: ReviewActor,
    decision_time: datetime,
) -> ValidatedReviewDecision:
    if not actor.identity.strip() or actor.role not in {"reviewer", "admin"}:
        raise ReviewValidationError(
            "reviewer_not_authorized",
            "A reviewer identity and authorized role are required.",
        )
    if review_status != "pending":
        raise ReviewValidationError(
            "action_review_already_decided",
            "The action review already has a final decision.",
        )
    if request.decision not in {
        "approved",
        "rejected",
        "deferred",
        "revision_requested",
    }:
        raise ReviewValidationError(
            "invalid_review_decision",
            "The review decision is not supported.",
        )
    rationale = request.rationale.strip()
    if not rationale:
        raise ReviewValidationError(
            "invalid_review_decision",
            "A nonempty rationale is required.",
        )

    edited_action = _validate_action_edit(
        decision=request.decision,
        raw_edit=request.edited_action,
        original_action=original_action,
        decision_date=decision_time.date(),
    )
    return ValidatedReviewDecision(
        decision=request.decision,
        reviewer_identity=actor.identity.strip(),
        reviewer_role=actor.role,
        rationale=rationale,
        edited_action=edited_action,
    )


def _validate_action_edit(
    *,
    decision: str,
    raw_edit: dict[str, object] | None,
    original_action: OriginalActionSnapshot,
    decision_date: date,
) -> EditedActionSnapshot | None:
    if raw_edit is None:
        return None
    if decision != "approved":
        raise ReviewValidationError(
            "invalid_action_edit",
            "Edited action values are allowed only for approval.",
        )
    forbidden_fields = set(raw_edit) - {"description", "due_date"}
    if forbidden_fields:
        raise ReviewValidationError(
            "invalid_action_edit",
            "Only description and due_date may be edited.",
        )
    if not raw_edit:
        raise ReviewValidationError(
            "invalid_action_edit",
            "An edited action must contain at least one actual change.",
        )

    description: str | None = None
    if "description" in raw_edit:
        value = raw_edit["description"]
        if not isinstance(value, str) or not value.strip():
            raise ReviewValidationError(
                "invalid_action_edit",
                "An edited description must be nonempty.",
            )
        description = value.strip()

    due_date: date | None = None
    if "due_date" in raw_edit:
        value = raw_edit["due_date"]
        if isinstance(value, date):
            due_date = value
        elif isinstance(value, str):
            try:
                due_date = date.fromisoformat(value)
            except ValueError as error:
                raise ReviewValidationError(
                    "invalid_action_edit",
                    "An edited due date must be an ISO 8601 date.",
                ) from error
        else:
            raise ReviewValidationError(
                "invalid_action_edit",
                "An edited due date must be an ISO 8601 date.",
            )
        if due_date is not None and due_date < decision_date:
            raise ReviewValidationError(
                "invalid_action_edit",
                "An edited due date cannot be before the decision date.",
            )

    if description is not None and description == original_action.description:
        description = None
    due_date_changed = "due_date" in raw_edit and due_date != original_action.due_date
    if description is None and not due_date_changed:
        raise ReviewValidationError(
            "invalid_action_edit",
            "An edited action must contain at least one actual change.",
        )
    return EditedActionSnapshot(
        description=description,
        due_date=due_date if due_date_changed else None,
    )


def derive_effective_approved_action(
    original_action: OriginalActionSnapshot,
    edited_action: EditedActionSnapshot | None,
) -> OriginalActionSnapshot:
    if edited_action is None:
        return original_action
    values = original_action.model_dump()
    if edited_action.description is not None:
        values["description"] = edited_action.description
    if edited_action.due_date is not None:
        values["due_date"] = edited_action.due_date
    return OriginalActionSnapshot.model_validate(values)
