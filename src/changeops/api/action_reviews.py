import uuid
from typing import Annotated

from fastapi import APIRouter, Header, Response, status
from fastapi.exceptions import HTTPException

from changeops.api.dependencies import SessionDependency
from changeops.domain.action_review import (
    ReviewActor,
    ReviewDecisionInput,
    ReviewValidationError,
)
from changeops.schemas.action_review import (
    ActionReviewDecisionRequest,
    ActionReviewResponse,
)
from changeops.services.action_review_serializer import serialize_action_review
from changeops.services.action_review_service import (
    ActionReviewLifecycleMismatchError,
    ActionReviewNotFoundError,
    ProposedActionNotFoundError,
    create_or_get_action_review,
    get_action_review,
    get_action_review_for_proposed_action,
    submit_action_review_decision,
)

router = APIRouter(prefix="/api/v1", tags=["action-reviews"])

ActorIdentityHeader = Annotated[str | None, Header(alias="X-ChangeOps-Actor")]
ActorRoleHeader = Annotated[str | None, Header(alias="X-ChangeOps-Role")]


@router.post(
    "/proposed-actions/{proposed_action_id}/review",
    response_model=ActionReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_review(
    proposed_action_id: uuid.UUID,
    response: Response,
    session: SessionDependency,
) -> ActionReviewResponse:
    try:
        review, created = create_or_get_action_review(session, proposed_action_id)
    except ProposedActionNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "proposed_action_not_found",
                "message": "Proposed action was not found.",
            },
        ) from error
    except ActionReviewLifecycleMismatchError as error:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "action_review_lifecycle_mismatch",
                "message": "The proposed action does not belong to a completed assessment.",
            },
        ) from error
    if not created:
        response.status_code = status.HTTP_200_OK
    response.headers["Location"] = f"/api/v1/action-reviews/{review.id}"
    return serialize_action_review(review)


@router.get(
    "/action-reviews/{review_id}",
    response_model=ActionReviewResponse,
)
def retrieve_review(
    review_id: uuid.UUID,
    session: SessionDependency,
) -> ActionReviewResponse:
    try:
        return serialize_action_review(get_action_review(session, review_id))
    except ActionReviewNotFoundError as error:
        raise _review_not_found(error) from error


@router.get(
    "/proposed-actions/{proposed_action_id}/review",
    response_model=ActionReviewResponse,
)
def retrieve_proposed_action_review(
    proposed_action_id: uuid.UUID,
    session: SessionDependency,
) -> ActionReviewResponse:
    try:
        return serialize_action_review(
            get_action_review_for_proposed_action(session, proposed_action_id)
        )
    except ActionReviewNotFoundError as error:
        raise _review_not_found(error) from error


@router.post(
    "/action-reviews/{review_id}/decisions",
    response_model=ActionReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_review_decision(
    review_id: uuid.UUID,
    request: ActionReviewDecisionRequest,
    response: Response,
    session: SessionDependency,
    actor_identity: ActorIdentityHeader = None,
    actor_role: ActorRoleHeader = None,
) -> ActionReviewResponse:
    actor = ReviewActor(identity=actor_identity or "", role=actor_role or "")
    try:
        review = submit_action_review_decision(
            session,
            review_id,
            ReviewDecisionInput(
                decision=request.decision,
                rationale=request.rationale,
                edited_action=request.edited_action,
            ),
            actor,
        )
    except ActionReviewNotFoundError as error:
        raise _review_not_found(error) from error
    except ReviewValidationError as error:
        if error.code == "reviewer_not_authorized":
            http_status = status.HTTP_403_FORBIDDEN
        elif error.code == "action_review_already_decided":
            http_status = status.HTTP_409_CONFLICT
        else:
            http_status = status.HTTP_422_UNPROCESSABLE_CONTENT
        raise HTTPException(
            status_code=http_status,
            detail={"code": error.code, "message": error.message},
        ) from error
    response.headers["Location"] = f"/api/v1/action-reviews/{review.id}"
    return serialize_action_review(review)


def _review_not_found(error: Exception) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={
            "code": "action_review_not_found",
            "message": "Action review was not found.",
        },
    )
