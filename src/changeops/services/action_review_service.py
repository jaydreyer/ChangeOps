import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from changeops.db.models import (
    ActionReview,
    ActionReviewDecision,
    AssessmentEnterpriseImpact,
    Finding,
    ImpactAssessment,
    ProposedAction,
)
from changeops.domain.action_review import (
    OriginalActionSnapshot,
    ReviewActor,
    ReviewContextSnapshot,
    ReviewDecisionInput,
    validate_review_decision,
)


class ProposedActionNotFoundError(Exception):
    pass


class ActionReviewNotFoundError(Exception):
    pass


class ActionReviewLifecycleMismatchError(Exception):
    pass


def create_or_get_action_review(
    session: Session,
    proposed_action_id: uuid.UUID,
) -> tuple[ActionReview, bool]:
    with session.begin():
        review, created = create_or_get_action_review_in_transaction(
            session,
            proposed_action_id,
        )
        review_id = review.id
    return get_action_review(session, review_id), created


def create_or_get_action_review_in_transaction(
    session: Session,
    proposed_action_id: uuid.UUID,
) -> tuple[ActionReview, bool]:
    """Create or reuse a review inside a caller-owned transaction."""
    action = session.get(ProposedAction, proposed_action_id, with_for_update=True)
    if action is None:
        raise ProposedActionNotFoundError(str(proposed_action_id))
    assessment = session.get(ImpactAssessment, action.assessment_id)
    if assessment is None or assessment.status != "completed":
        raise ActionReviewLifecycleMismatchError(str(proposed_action_id))

    existing = session.scalar(
        select(ActionReview).where(ActionReview.proposed_action_id == proposed_action_id)
    )
    if existing is not None:
        return existing, False

    action = session.scalar(
        select(ProposedAction)
        .where(ProposedAction.id == proposed_action_id)
        .options(
            selectinload(ProposedAction.finding).selectinload(Finding.evidence),
            selectinload(ProposedAction.enterprise_impact).selectinload(
                AssessmentEnterpriseImpact.evidence
            ),
        )
    )
    if action is None:
        raise ProposedActionNotFoundError(str(proposed_action_id))
    review = ActionReview(
        assessment_id=action.assessment_id,
        proposed_action_id=action.id,
        status="pending",
        original_action_snapshot=_original_snapshot(action).model_dump(mode="json"),
        review_context_snapshot=_review_context(action).model_dump(mode="json"),
        created_at=datetime.now(UTC),
        completed_at=None,
    )
    session.add(review)
    session.flush()
    return review, True


def submit_action_review_decision(
    session: Session,
    review_id: uuid.UUID,
    request: ReviewDecisionInput,
    actor: ReviewActor,
    *,
    now: datetime | None = None,
) -> ActionReview:
    decision_time = now or datetime.now(UTC)
    with session.begin():
        review = session.get(ActionReview, review_id, with_for_update=True)
        if review is None:
            raise ActionReviewNotFoundError(str(review_id))
        validated = validate_review_decision(
            review_status=review.status,
            original_action=OriginalActionSnapshot.model_validate(review.original_action_snapshot),
            request=request,
            actor=actor,
            decision_time=decision_time,
        )
        decision = ActionReviewDecision(
            action_review_id=review.id,
            decision=validated.decision,
            reviewer_identity=validated.reviewer_identity,
            reviewer_role=validated.reviewer_role,
            rationale=validated.rationale,
            edited_action_snapshot=(
                validated.edited_action.model_dump(mode="json", exclude_none=True)
                if validated.edited_action is not None
                else None
            ),
            created_at=decision_time,
        )
        session.add(decision)
        session.flush()
        review.status = validated.decision
        review.completed_at = decision_time
        session.flush()
    return get_action_review(session, review_id)


def get_action_review(session: Session, review_id: uuid.UUID) -> ActionReview:
    review = session.scalar(
        select(ActionReview)
        .where(ActionReview.id == review_id)
        .options(selectinload(ActionReview.decisions))
    )
    if review is None:
        raise ActionReviewNotFoundError(str(review_id))
    return review


def get_action_review_for_proposed_action(
    session: Session,
    proposed_action_id: uuid.UUID,
) -> ActionReview:
    review = session.scalar(
        select(ActionReview)
        .where(ActionReview.proposed_action_id == proposed_action_id)
        .options(selectinload(ActionReview.decisions))
    )
    if review is None:
        raise ActionReviewNotFoundError(str(proposed_action_id))
    return review


def _original_snapshot(action: ProposedAction) -> OriginalActionSnapshot:
    return OriginalActionSnapshot(
        proposed_action_id=action.id,
        assessment_id=action.assessment_id,
        finding_id=action.finding_id,
        enterprise_impact_id=action.enterprise_impact_id,
        worker_id=action.worker_id,
        action_type=action.action_type,
        target_type=action.target_type,
        target_identifier=action.target_identifier,
        description=action.description,
        due_date=action.due_date,
        execution_status=action.execution_status,
    )


def _review_context(action: ProposedAction) -> ReviewContextSnapshot:
    if action.enterprise_impact is not None:
        reason_code = action.enterprise_impact.reason_code
        evidence_keys = tuple(
            sorted(item.evidence_key for item in action.enterprise_impact.evidence)
        )
    elif action.finding is not None:
        reason_code = action.finding.rule_code
        evidence_keys = tuple(sorted(item.evidence_key for item in action.finding.evidence))
    else:
        reason_code = None
        evidence_keys = ()
    return ReviewContextSnapshot(
        finding_id=action.finding_id,
        enterprise_impact_id=action.enterprise_impact_id,
        reason_code=reason_code,
        evidence_keys=evidence_keys,
    )
