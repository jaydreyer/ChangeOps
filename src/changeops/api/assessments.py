import uuid

from fastapi import APIRouter, Response, status
from fastapi.exceptions import HTTPException

from changeops.api.dependencies import SessionDependency
from changeops.schemas.assessments import ImpactAssessmentResponse
from changeops.services.assessment_serializer import serialize_assessment
from changeops.services.assessment_service import (
    ImpactAssessmentNotFoundError,
    PolicyChangeNotFoundError,
    PolicyNotAnalyzableError,
    create_impact_assessment,
    get_impact_assessment,
)

router = APIRouter(prefix="/api/v1", tags=["impact-assessments"])


@router.post(
    "/policy-changes/{policy_change_id}/impact-assessments",
    response_model=ImpactAssessmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_assessment(
    policy_change_id: str,
    response: Response,
    session: SessionDependency,
) -> ImpactAssessmentResponse:
    try:
        assessment = create_impact_assessment(session, policy_change_id)
    except PolicyChangeNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "policy_change_not_found",
                "message": "Policy change was not found.",
            },
        ) from error
    except PolicyNotAnalyzableError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "policy_not_analyzable",
                "message": ("The policy change does not contain valid international-travel rules."),
            },
        ) from error

    response.headers["Location"] = f"/api/v1/impact-assessments/{assessment.id}"
    return serialize_assessment(assessment)


@router.get(
    "/impact-assessments/{assessment_id}",
    response_model=ImpactAssessmentResponse,
)
def retrieve_assessment(
    assessment_id: uuid.UUID,
    session: SessionDependency,
) -> ImpactAssessmentResponse:
    try:
        assessment = get_impact_assessment(session, assessment_id)
    except ImpactAssessmentNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "impact_assessment_not_found",
                "message": "Impact assessment was not found.",
            },
        ) from error
    return serialize_assessment(assessment)
