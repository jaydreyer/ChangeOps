from changeops.db.models import ActionReview, ActionReviewDecision
from changeops.domain.action_review import (
    EditedActionSnapshot,
    OriginalActionSnapshot,
    derive_effective_approved_action,
)
from changeops.schemas.action_review import (
    ActionReviewDecisionResponse,
    ActionReviewResponse,
)


def serialize_action_review(review: ActionReview) -> ActionReviewResponse:
    original = OriginalActionSnapshot.model_validate(review.original_action_snapshot)
    decisions = [_serialize_decision(item) for item in review.decisions]
    current_decision = decisions[0] if decisions else None
    effective_action = None
    if review.status == "approved" and review.decisions:
        edited = (
            EditedActionSnapshot.model_validate(review.decisions[0].edited_action_snapshot)
            if review.decisions[0].edited_action_snapshot is not None
            else None
        )
        effective_action = derive_effective_approved_action(original, edited)
    return ActionReviewResponse(
        id=review.id,
        assessment_id=review.assessment_id,
        proposed_action_id=review.proposed_action_id,
        status=review.status,
        original_action=original.model_dump(mode="json"),
        review_context=review.review_context_snapshot,
        decision_history=decisions,
        current_decision=current_decision,
        effective_approved_action=(
            effective_action.model_dump(mode="json") if effective_action is not None else None
        ),
        created_at=review.created_at,
        completed_at=review.completed_at,
    )


def _serialize_decision(
    decision: ActionReviewDecision,
) -> ActionReviewDecisionResponse:
    return ActionReviewDecisionResponse(
        id=decision.id,
        action_review_id=decision.action_review_id,
        decision=decision.decision,
        reviewer_identity=decision.reviewer_identity,
        reviewer_role=decision.reviewer_role,
        rationale=decision.rationale,
        edited_action=decision.edited_action_snapshot,
        created_at=decision.created_at,
    )
