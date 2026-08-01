import uuid

from fastapi import APIRouter, Response, status
from fastapi.exceptions import HTTPException

from changeops.api.dependencies import SessionDependency
from changeops.api.policy_extractions import ExtractionModelDependency
from changeops.schemas.policy_analysis import (
    ClarificationAnswerRequest,
    CreatePolicyAnalysisRunRequest,
    PolicyAnalysisRunResponse,
)
from changeops.services.policy_analysis_serializer import serialize_policy_analysis_run
from changeops.services.policy_analysis_service import (
    ClarificationNotFoundError,
    ClarificationStateConflictError,
    PolicyAnalysisPolicyNotFoundError,
    PolicyAnalysisRunNotFoundError,
    answer_clarification,
    create_policy_analysis_run_record,
    get_policy_analysis_run,
)
from changeops.workflows.policy_analysis import execute_policy_analysis

router = APIRouter(prefix="/api/v1/policy-analysis-runs", tags=["policy-analysis"])


@router.post(
    "",
    response_model=PolicyAnalysisRunResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_policy_analysis_run(
    payload: CreatePolicyAnalysisRunRequest,
    response: Response,
    session: SessionDependency,
    configured_model: ExtractionModelDependency,
) -> PolicyAnalysisRunResponse:
    try:
        run = create_policy_analysis_run_record(
            session,
            payload.policy_change_id,
            configured_model,
        )
    except PolicyAnalysisPolicyNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "policy_change_not_found", "message": "Policy change was not found."},
        ) from error
    session.rollback()
    execute_policy_analysis(session, run.id, configured_model)
    result = get_policy_analysis_run(session, run.id)
    response.headers["Location"] = f"/api/v1/policy-analysis-runs/{run.id}"
    return serialize_policy_analysis_run(result)


@router.get("/{run_id}", response_model=PolicyAnalysisRunResponse)
def retrieve_policy_analysis_run(
    run_id: uuid.UUID,
    session: SessionDependency,
) -> PolicyAnalysisRunResponse:
    try:
        return serialize_policy_analysis_run(get_policy_analysis_run(session, run_id))
    except PolicyAnalysisRunNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "policy_analysis_run_not_found",
                "message": "Policy analysis run was not found.",
            },
        ) from error


@router.post(
    "/{run_id}/clarifications/{clarification_id}/answer",
    response_model=PolicyAnalysisRunResponse,
)
def answer_policy_analysis_clarification(
    run_id: uuid.UUID,
    clarification_id: uuid.UUID,
    payload: ClarificationAnswerRequest,
    session: SessionDependency,
    configured_model: ExtractionModelDependency,
) -> PolicyAnalysisRunResponse:
    try:
        answer_clarification(
            session,
            run_id,
            clarification_id,
            value=payload.value,
            responder_identity=payload.responder_identity,
        )
    except (PolicyAnalysisRunNotFoundError, ClarificationNotFoundError) as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "policy_analysis_clarification_not_found",
                "message": "Clarification was not found for this run.",
            },
        ) from error
    except ClarificationStateConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "clarification_state_conflict",
                "message": "Clarification is already answered or the run is terminal.",
            },
        ) from error
    execute_policy_analysis(session, run_id, configured_model)
    return serialize_policy_analysis_run(get_policy_analysis_run(session, run_id))
