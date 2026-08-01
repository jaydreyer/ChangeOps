import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from fastapi.exceptions import HTTPException

from changeops.ai.model_factory import (
    ExtractionProviderConfigurationError,
    get_configured_extraction_model,
)
from changeops.ai.policy_extractor import ConfiguredExtractionModel
from changeops.api.dependencies import SessionDependency
from changeops.schemas.policy_extractions import PolicyExtractionAttemptResponse
from changeops.services.policy_extraction_serializer import (
    serialize_policy_extraction_attempt,
)
from changeops.services.policy_extraction_service import (
    PolicyChangeNotFoundError,
    PolicyExtractionAttemptNotFoundError,
    create_policy_extraction_attempt,
    get_policy_extraction_attempt,
)

router = APIRouter(prefix="/api/v1", tags=["policy-extractions"])


def extraction_model_dependency() -> ConfiguredExtractionModel:
    try:
        return get_configured_extraction_model()
    except ExtractionProviderConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "extraction_provider_not_configured",
                "message": str(error),
            },
        ) from error


ExtractionModelDependency = Annotated[
    ConfiguredExtractionModel,
    Depends(extraction_model_dependency),
]


@router.post(
    "/policy-changes/{policy_change_id}/extraction-attempts",
    response_model=PolicyExtractionAttemptResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_extraction_attempt(
    policy_change_id: str,
    response: Response,
    session: SessionDependency,
    configured_model: ExtractionModelDependency,
) -> PolicyExtractionAttemptResponse:
    try:
        attempt = create_policy_extraction_attempt(session, policy_change_id, configured_model)
    except PolicyChangeNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "policy_change_not_found",
                "message": "Policy change was not found.",
            },
        ) from error
    response.headers["Location"] = f"/api/v1/policy-extraction-attempts/{attempt.id}"
    return serialize_policy_extraction_attempt(attempt)


@router.get(
    "/policy-extraction-attempts/{attempt_id}",
    response_model=PolicyExtractionAttemptResponse,
)
def retrieve_extraction_attempt(
    attempt_id: uuid.UUID,
    session: SessionDependency,
) -> PolicyExtractionAttemptResponse:
    try:
        attempt = get_policy_extraction_attempt(session, attempt_id)
    except PolicyExtractionAttemptNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "policy_extraction_attempt_not_found",
                "message": "Policy extraction attempt was not found.",
            },
        ) from error
    return serialize_policy_extraction_attempt(attempt)
