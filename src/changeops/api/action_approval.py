import uuid
from typing import Annotated

from fastapi import APIRouter, Header, Response, status
from fastapi.exceptions import HTTPException

from changeops.api.dependencies import SessionDependency
from changeops.schemas.action_approval import ActionApprovalRunResponse
from changeops.services.action_approval_serializer import serialize_action_approval_run
from changeops.services.action_approval_service import (
    ActionApprovalRunNotFoundError,
    ApprovalAssessmentNotCompletedError,
    ApprovalAssessmentNotFoundError,
    create_action_approval_run_record,
    get_action_approval_run,
    get_action_approval_run_for_assessment,
)
from changeops.workflows.action_approval import execute_action_approval

router = APIRouter(prefix="/api/v1", tags=["action-approval"])

ActorIdentityHeader = Annotated[str | None, Header(alias="X-ChangeOps-Actor")]
ActorRoleHeader = Annotated[str | None, Header(alias="X-ChangeOps-Role")]


@router.post(
    "/impact-assessments/{assessment_id}/approval-run",
    response_model=ActionApprovalRunResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_action_approval_run(
    assessment_id: uuid.UUID,
    response: Response,
    session: SessionDependency,
) -> ActionApprovalRunResponse:
    try:
        run, created = create_action_approval_run_record(session, assessment_id)
    except ApprovalAssessmentNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "approval_assessment_not_found",
                "message": "Impact assessment was not found.",
            },
        ) from error
    except ApprovalAssessmentNotCompletedError as error:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "approval_assessment_not_completed",
                "message": (
                    "Approval requires an assessment produced by a completed policy-analysis run."
                ),
            },
        ) from error
    if created:
        session.rollback()
        execute_action_approval(session, run.id, trigger_type="run_created")
    else:
        response.status_code = status.HTTP_200_OK
    result = get_action_approval_run(session, run.id)
    response.headers["Location"] = f"/api/v1/action-approval-runs/{run.id}"
    return serialize_action_approval_run(result)


@router.get(
    "/action-approval-runs/{run_id}",
    response_model=ActionApprovalRunResponse,
)
def retrieve_action_approval_run(
    run_id: uuid.UUID,
    session: SessionDependency,
) -> ActionApprovalRunResponse:
    try:
        return serialize_action_approval_run(get_action_approval_run(session, run_id))
    except ActionApprovalRunNotFoundError as error:
        raise _run_not_found(error) from error


@router.get(
    "/impact-assessments/{assessment_id}/approval-run",
    response_model=ActionApprovalRunResponse,
)
def retrieve_assessment_action_approval_run(
    assessment_id: uuid.UUID,
    session: SessionDependency,
) -> ActionApprovalRunResponse:
    try:
        return serialize_action_approval_run(
            get_action_approval_run_for_assessment(session, assessment_id)
        )
    except ActionApprovalRunNotFoundError as error:
        raise _run_not_found(error) from error


@router.post(
    "/action-approval-runs/{run_id}/resume",
    response_model=ActionApprovalRunResponse,
)
def resume_action_approval_run(
    run_id: uuid.UUID,
    session: SessionDependency,
    actor_identity: ActorIdentityHeader = None,
    actor_role: ActorRoleHeader = None,
) -> ActionApprovalRunResponse:
    identity = (actor_identity or "").strip()
    if not identity or actor_role not in {"reviewer", "admin"}:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "reviewer_not_authorized",
                "message": "An authorized reviewer or admin is required.",
            },
        )
    try:
        run = get_action_approval_run(session, run_id)
    except ActionApprovalRunNotFoundError as error:
        raise _run_not_found(error) from error
    if run.status in {"awaiting_decisions", "initializing"}:
        session.rollback()
        execute_action_approval(
            session,
            run.id,
            trigger_type="manual_resume",
            actor_identity=identity,
        )
    return serialize_action_approval_run(get_action_approval_run(session, run.id))


def _run_not_found(error: Exception) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={
            "code": "action_approval_run_not_found",
            "message": "Action approval run was not found.",
        },
    )
