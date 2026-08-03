import uuid

from fastapi import APIRouter
from fastapi.exceptions import HTTPException

from changeops.api.dependencies import SessionDependency
from changeops.schemas.policy_analysis_journey import (
    PolicyAnalysisEntryResponse,
    PolicyAnalysisJourneyResponse,
)
from changeops.services.policy_analysis_journey_service import (
    PolicyAnalysisJourneyIntegrityError,
    PolicyAnalysisJourneyNotFoundError,
    get_policy_analysis_entry,
    get_policy_analysis_journey,
)

router = APIRouter(prefix="/api/v1", tags=["policy-analysis-journey"])


@router.get("/policy-analysis-entry", response_model=PolicyAnalysisEntryResponse)
def retrieve_policy_analysis_entry(
    session: SessionDependency,
) -> PolicyAnalysisEntryResponse:
    return get_policy_analysis_entry(session)


@router.get(
    "/policy-analysis-runs/{run_id}/journey",
    response_model=PolicyAnalysisJourneyResponse,
)
def retrieve_policy_analysis_journey(
    run_id: uuid.UUID,
    session: SessionDependency,
) -> PolicyAnalysisJourneyResponse:
    try:
        return get_policy_analysis_journey(session, run_id)
    except PolicyAnalysisJourneyNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "policy_analysis_journey_not_found",
                "message": "Policy analysis journey was not found.",
            },
        ) from error
    except PolicyAnalysisJourneyIntegrityError as error:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "policy_analysis_journey_lineage_inconsistent",
                "message": str(error),
            },
        ) from error
