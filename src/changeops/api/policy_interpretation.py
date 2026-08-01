import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from fastapi.exceptions import HTTPException

from changeops.ai.model_factory import (
    InterpretationProviderConfigurationError,
    get_configured_interpretation_model,
)
from changeops.ai.policy_interpreter import ConfiguredInterpretationModel
from changeops.api.dependencies import SessionDependency
from changeops.schemas.policy_interpretation import (
    ChangePlanResponse,
    PolicyInterpretationAttemptResponse,
)
from changeops.services.assessment_service import ImpactAssessmentNotFoundError
from changeops.services.policy_interpretation_service import (
    AssessmentNotInterpretableError,
    ChangePlanNotFoundError,
    InterpretationFailedError,
    PolicyInterpretationAttemptNotFoundError,
    create_or_get_change_plan,
    get_change_plan,
    get_change_plan_for_assessment,
    get_interpretation_attempt,
)

router = APIRouter(prefix="/api/v1", tags=["policy-interpretation"])


def interpretation_model_dependency() -> ConfiguredInterpretationModel:
    try:
        return get_configured_interpretation_model()
    except InterpretationProviderConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "interpretation_provider_not_configured", "message": str(error)},
        ) from error


InterpretationModelDependency = Annotated[
    ConfiguredInterpretationModel, Depends(interpretation_model_dependency)
]


def _serialize_plan(plan) -> ChangePlanResponse:
    return ChangePlanResponse(
        id=plan.id,
        policy_analysis_run_id=plan.policy_analysis_run_id,
        impact_assessment_id=plan.impact_assessment_id,
        interpretation_attempt_id=plan.interpretation_attempt_id,
        schema_version=plan.schema_version,
        created_at=plan.created_at,
        change_plan=plan.validated_plan,
    )


@router.post(
    "/impact-assessments/{assessment_id}/change-plans",
    response_model=ChangePlanResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_change_plan(
    assessment_id: uuid.UUID,
    response: Response,
    session: SessionDependency,
    configured_model: InterpretationModelDependency,
) -> ChangePlanResponse:
    try:
        plan, created = create_or_get_change_plan(session, assessment_id, configured_model)
    except ImpactAssessmentNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "impact_assessment_not_found",
                "message": "Impact assessment was not found.",
            },
        ) from error
    except AssessmentNotInterpretableError as error:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "assessment_not_interpretable",
                "message": "Only a completed policy-analysis assessment can be interpreted.",
            },
        ) from error
    except InterpretationFailedError as error:
        raise HTTPException(
            status_code=502 if error.failure_code == "interpretation_provider_error" else 422,
            detail={
                "code": error.failure_code,
                "message": "Interpretation failed; the deterministic assessment remains completed.",
                "attempt_id": str(error.attempt_id),
            },
        ) from error
    if not created:
        response.status_code = status.HTTP_200_OK
    response.headers["Location"] = f"/api/v1/change-plans/{plan.id}"
    return _serialize_plan(plan)


@router.get("/change-plans/{plan_id}", response_model=ChangePlanResponse)
def retrieve_change_plan(plan_id: uuid.UUID, session: SessionDependency) -> ChangePlanResponse:
    try:
        return _serialize_plan(get_change_plan(session, plan_id))
    except ChangePlanNotFoundError as error:
        raise HTTPException(status_code=404, detail={"code": "change_plan_not_found"}) from error


@router.get(
    "/impact-assessments/{assessment_id}/change-plan",
    response_model=ChangePlanResponse,
)
def retrieve_assessment_change_plan(
    assessment_id: uuid.UUID, session: SessionDependency
) -> ChangePlanResponse:
    try:
        return _serialize_plan(get_change_plan_for_assessment(session, assessment_id))
    except ChangePlanNotFoundError as error:
        raise HTTPException(status_code=404, detail={"code": "change_plan_not_found"}) from error


@router.get(
    "/policy-interpretation-attempts/{attempt_id}",
    response_model=PolicyInterpretationAttemptResponse,
)
def retrieve_interpretation_attempt(
    attempt_id: uuid.UUID, session: SessionDependency
) -> PolicyInterpretationAttemptResponse:
    try:
        return PolicyInterpretationAttemptResponse.model_validate(
            get_interpretation_attempt(session, attempt_id), from_attributes=True
        )
    except PolicyInterpretationAttemptNotFoundError as error:
        raise HTTPException(
            status_code=404, detail={"code": "policy_interpretation_attempt_not_found"}
        ) from error
