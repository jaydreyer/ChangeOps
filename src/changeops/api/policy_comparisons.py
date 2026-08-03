import uuid

from fastapi import APIRouter, Header, Response, status
from fastapi.exceptions import HTTPException

from changeops.api.dependencies import SessionDependency
from changeops.schemas.policy_comparisons import (
    CreatePolicyComparisonRequest,
    PolicyComparisonResponse,
)
from changeops.services.policy_comparison_serializer import serialize_policy_comparison
from changeops.services.policy_comparison_service import (
    PolicyComparisonCreateError,
    PolicyComparisonNotFoundError,
    create_policy_comparison,
    get_policy_comparison,
)

router = APIRouter(prefix="/api/v1/policy-comparisons", tags=["policy-comparisons"])


@router.post(
    "",
    response_model=PolicyComparisonResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_comparison(
    payload: CreatePolicyComparisonRequest,
    response: Response,
    session: SessionDependency,
    changeops_actor: str | None = Header(default=None, alias="X-ChangeOps-Actor"),
) -> PolicyComparisonResponse:
    try:
        comparison, created = create_policy_comparison(
            session,
            baseline_policy_change_id=payload.baseline_policy_change_id,
            proposed_policy_change_id=payload.proposed_policy_change_id,
            created_by=changeops_actor or "",
        )
        result = serialize_policy_comparison(session, comparison)
    except PolicyComparisonCreateError as error:
        raise HTTPException(
            status_code=error.status_code,
            detail={"code": error.code, "message": error.message},
        ) from error
    if not created:
        response.status_code = status.HTTP_200_OK
    response.headers["Location"] = f"/api/v1/policy-comparisons/{comparison.id}"
    return result


@router.get("/{comparison_id}", response_model=PolicyComparisonResponse)
def retrieve_comparison(
    comparison_id: uuid.UUID,
    session: SessionDependency,
) -> PolicyComparisonResponse:
    try:
        return serialize_policy_comparison(
            session,
            get_policy_comparison(session, comparison_id),
        )
    except PolicyComparisonNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "policy_comparison_not_found",
                "message": "Policy comparison was not found.",
            },
        ) from error
    except PolicyComparisonCreateError as error:
        raise HTTPException(
            status_code=error.status_code,
            detail={"code": error.code, "message": error.message},
        ) from error
