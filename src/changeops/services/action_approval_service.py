import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from changeops.db.models import (
    ActionApprovalRun,
    ActionApprovalRunItem,
    ActionApprovalRunTransition,
    ImpactAssessment,
    PolicyAnalysisRun,
    ProposedAction,
)
from changeops.domain.action_approval import (
    ApprovalProgress,
    calculate_approval_progress,
    map_approval_failure,
)
from changeops.services.action_review_service import (
    create_or_get_action_review_in_transaction,
)


class ActionApprovalRunNotFoundError(Exception):
    pass


class ApprovalAssessmentNotFoundError(Exception):
    pass


class ApprovalAssessmentNotCompletedError(Exception):
    pass


class ActionApprovalStateError(Exception):
    pass


def create_action_approval_run_record(
    session: Session,
    assessment_id: uuid.UUID,
) -> tuple[ActionApprovalRun, bool]:
    now = datetime.now(UTC)
    with session.begin():
        assessment = session.get(ImpactAssessment, assessment_id, with_for_update=True)
        if assessment is None:
            raise ApprovalAssessmentNotFoundError(str(assessment_id))
        existing = session.scalar(
            select(ActionApprovalRun).where(ActionApprovalRun.assessment_id == assessment_id)
        )
        if existing is not None:
            run_id = existing.id
            created = False
        else:
            analysis = (
                session.get(PolicyAnalysisRun, assessment.policy_analysis_run_id)
                if assessment.policy_analysis_run_id is not None
                else None
            )
            if (
                assessment.status != "completed"
                or analysis is None
                or analysis.status != "completed"
                or analysis.assessment_id != assessment.id
            ):
                raise ApprovalAssessmentNotCompletedError(str(assessment_id))
            run = ActionApprovalRun(
                assessment_id=assessment.id,
                policy_analysis_run_id=analysis.id,
                status="initializing",
                current_step="create_reviews",
                total_action_count=0,
                pending_count=0,
                approved_count=0,
                rejected_count=0,
                deferred_count=0,
                revision_requested_count=0,
                failure_code=None,
                failure_message=None,
                created_at=now,
                updated_at=now,
                completed_at=None,
            )
            session.add(run)
            session.flush()
            _add_transition(
                session,
                run,
                from_status=None,
                from_step=None,
                reason_code="approval_run_created",
                trigger_type="run_created",
            )
            run_id = run.id
            created = True
    return get_action_approval_run(session, run_id), created


def initialize_action_approval_run(session: Session, run_id: uuid.UUID) -> ApprovalProgress:
    now = datetime.now(UTC)
    with session.begin():
        run = session.get(ActionApprovalRun, run_id, with_for_update=True)
        if run is None:
            raise ActionApprovalRunNotFoundError(str(run_id))
        if run.status == "completed":
            return _progress_from_run(run)
        if run.status != "initializing" or run.current_step != "create_reviews":
            raise ActionApprovalStateError(
                f"run {run.id} cannot initialize from {run.status}/{run.current_step}"
            )
        existing_items = list(
            session.scalars(
                select(ActionApprovalRunItem).where(ActionApprovalRunItem.approval_run_id == run.id)
            )
        )
        if existing_items:
            raise ActionApprovalStateError("approval initialization found partial membership")

        actions = list(
            session.scalars(
                select(ProposedAction)
                .where(ProposedAction.assessment_id == run.assessment_id)
                .order_by(
                    ProposedAction.worker_id.nullsfirst(),
                    ProposedAction.action_type,
                    ProposedAction.target_identifier,
                    ProposedAction.id,
                )
            )
        )
        reviews = []
        for sequence, action in enumerate(actions):
            review, _ = create_or_get_action_review_in_transaction(session, action.id)
            reviews.append(review)
            session.add(
                ActionApprovalRunItem(
                    approval_run_id=run.id,
                    assessment_id=run.assessment_id,
                    proposed_action_id=action.id,
                    action_review_id=review.id,
                    sequence=sequence,
                    created_at=now,
                )
            )
        session.flush()
        progress = calculate_approval_progress(review.status for review in reviews)
        _set_counts(run, progress)
        previous_step = run.current_step
        run.current_step = "evaluate_reviews"
        run.updated_at = now
        session.flush()
        _add_transition(
            session,
            run,
            from_status="initializing",
            from_step=previous_step,
            reason_code="approval_reviews_initialized",
            trigger_type="initialized",
        )
    return progress


def evaluate_action_approval_run(
    session: Session,
    run_id: uuid.UUID,
    *,
    trigger_type: str,
    trigger_reference: str | None = None,
    actor_identity: str | None = None,
) -> ApprovalProgress:
    now = datetime.now(UTC)
    with session.begin():
        run = session.get(ActionApprovalRun, run_id, with_for_update=True)
        if run is None:
            raise ActionApprovalRunNotFoundError(str(run_id))
        if run.status == "completed":
            return _progress_from_run(run)
        if run.status not in {"initializing", "awaiting_decisions"}:
            raise ActionApprovalStateError(f"run status {run.status!r} cannot be evaluated")

        items = list(
            session.scalars(
                select(ActionApprovalRunItem)
                .where(ActionApprovalRunItem.approval_run_id == run.id)
                .options(selectinload(ActionApprovalRunItem.review))
                .order_by(ActionApprovalRunItem.sequence)
            )
        )
        if len(items) != run.total_action_count:
            raise ValueError("approval membership does not match the initialized action count")
        if any(
            item.assessment_id != run.assessment_id
            or item.review.assessment_id != run.assessment_id
            or item.review.proposed_action_id != item.proposed_action_id
            for item in items
        ):
            raise ValueError("approval membership lifecycle mismatch")

        progress = calculate_approval_progress(item.review.status for item in items)
        old_counts = _progress_from_run(run)
        old_status = run.status
        old_step = run.current_step
        if (
            run.status == "awaiting_decisions"
            and run.current_step == "await_decisions"
            and old_counts == progress
            and run.failure_code is None
        ):
            return progress
        _set_counts(run, progress)
        run.failure_code = None
        run.failure_message = None
        if progress.pending:
            run.status = "awaiting_decisions"
            run.current_step = "await_decisions"
            run.completed_at = None
        else:
            run.status = "completed"
            run.current_step = "finalize"
            run.completed_at = now
        run.updated_at = now
        session.flush()

        changed = old_status != run.status or old_step != run.current_step or old_counts != progress
        if changed:
            _add_transition(
                session,
                run,
                from_status=old_status,
                from_step=old_step,
                reason_code=(
                    "approval_all_decisions_recorded"
                    if run.status == "completed"
                    else "approval_decisions_pending"
                ),
                trigger_type="completed" if run.status == "completed" else trigger_type,
                trigger_reference=trigger_reference,
                actor_identity=actor_identity,
            )
    return progress


def get_action_approval_run(session: Session, run_id: uuid.UUID) -> ActionApprovalRun:
    run = session.scalar(
        select(ActionApprovalRun)
        .where(ActionApprovalRun.id == run_id)
        .options(
            selectinload(ActionApprovalRun.items).selectinload(ActionApprovalRunItem.review),
            selectinload(ActionApprovalRun.transitions),
        )
    )
    if run is None:
        raise ActionApprovalRunNotFoundError(str(run_id))
    return run


def get_action_approval_run_for_assessment(
    session: Session,
    assessment_id: uuid.UUID,
) -> ActionApprovalRun:
    run = session.scalar(
        select(ActionApprovalRun).where(ActionApprovalRun.assessment_id == assessment_id)
    )
    if run is None:
        raise ActionApprovalRunNotFoundError(str(assessment_id))
    return get_action_approval_run(session, run.id)


def find_action_approval_run_id_for_review(
    session: Session,
    review_id: uuid.UUID,
) -> uuid.UUID | None:
    return session.scalar(
        select(ActionApprovalRunItem.approval_run_id).where(
            ActionApprovalRunItem.action_review_id == review_id
        )
    )


def record_action_approval_failure(
    session: Session,
    run_id: uuid.UUID,
    error: Exception,
    *,
    phase: str,
) -> None:
    session.rollback()
    now = datetime.now(UTC)
    with session.begin():
        run = session.get(ActionApprovalRun, run_id, with_for_update=True)
        if run is None or run.status == "completed":
            return
        old_status = run.status
        old_step = run.current_step
        run.failure_code = map_approval_failure(error, phase=phase)
        run.failure_message = "The approval workflow could not advance safely."
        if run.status == "initializing":
            run.status = "failed"
        run.updated_at = now
        session.flush()
        _add_transition(
            session,
            run,
            from_status=old_status,
            from_step=old_step,
            reason_code=run.failure_code,
            trigger_type="failed",
        )


def _set_counts(run: ActionApprovalRun, progress: ApprovalProgress) -> None:
    run.total_action_count = progress.total
    run.pending_count = progress.pending
    run.approved_count = progress.approved
    run.rejected_count = progress.rejected
    run.deferred_count = progress.deferred
    run.revision_requested_count = progress.revision_requested


def _progress_from_run(run: ActionApprovalRun) -> ApprovalProgress:
    return ApprovalProgress(
        total=run.total_action_count,
        pending=run.pending_count,
        approved=run.approved_count,
        rejected=run.rejected_count,
        deferred=run.deferred_count,
        revision_requested=run.revision_requested_count,
    )


def _add_transition(
    session: Session,
    run: ActionApprovalRun,
    *,
    from_status: str | None,
    from_step: str | None,
    reason_code: str,
    trigger_type: str,
    trigger_reference: str | None = None,
    actor_identity: str | None = None,
) -> None:
    session.add(
        ActionApprovalRunTransition(
            approval_run_id=run.id,
            from_status=from_status,
            to_status=run.status,
            from_step=from_step,
            to_step=run.current_step,
            reason_code=reason_code,
            trigger_type=trigger_type,
            trigger_reference=trigger_reference,
            actor_identity=actor_identity,
            created_at=datetime.now(UTC),
        )
    )
