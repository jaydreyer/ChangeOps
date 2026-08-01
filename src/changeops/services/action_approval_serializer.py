from changeops.db.models import ActionApprovalRun
from changeops.schemas.action_approval import (
    ActionApprovalRunItemResponse,
    ActionApprovalRunResponse,
    ActionApprovalTransitionResponse,
    ApprovalSummaryResponse,
)


def serialize_action_approval_run(run: ActionApprovalRun) -> ActionApprovalRunResponse:
    return ActionApprovalRunResponse(
        id=run.id,
        assessment_id=run.assessment_id,
        policy_analysis_run_id=run.policy_analysis_run_id,
        status=run.status,
        current_step=run.current_step,
        summary=ApprovalSummaryResponse(
            total=run.total_action_count,
            pending=run.pending_count,
            approved=run.approved_count,
            rejected=run.rejected_count,
            deferred=run.deferred_count,
            revision_requested=run.revision_requested_count,
        ),
        failure_code=run.failure_code,
        failure_message=run.failure_message,
        created_at=run.created_at,
        updated_at=run.updated_at,
        completed_at=run.completed_at,
        items=[
            ActionApprovalRunItemResponse(
                sequence=item.sequence,
                proposed_action_id=item.proposed_action_id,
                review_id=item.action_review_id,
                review_status=item.review.status,
                assessment_url=f"/api/v1/impact-assessments/{run.assessment_id}",
                review_url=f"/api/v1/action-reviews/{item.action_review_id}",
            )
            for item in sorted(run.items, key=lambda item: item.sequence)
        ],
        transitions=[
            ActionApprovalTransitionResponse(
                id=item.id,
                from_status=item.from_status,
                to_status=item.to_status,
                from_step=item.from_step,
                to_step=item.to_step,
                reason_code=item.reason_code,
                trigger_type=item.trigger_type,
                trigger_reference=item.trigger_reference,
                actor_identity=item.actor_identity,
                created_at=item.created_at,
            )
            for item in sorted(run.transitions, key=lambda item: (item.created_at, item.id))
        ],
    )
