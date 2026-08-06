import uuid

from fastapi import APIRouter
from fastapi.exceptions import HTTPException

from changeops.api.dependencies import SessionDependency
from changeops.schemas.audit_timeline import AuditTimelineResponse
from changeops.services.audit_timeline_projection_service import (
    AuditTimelineNotFoundError,
    get_audit_timeline,
)

router = APIRouter(prefix="/api/v1", tags=["audit-timeline"])


@router.get(
    "/policy-analysis-runs/{run_id}/audit-timeline",
    response_model=AuditTimelineResponse,
)
def retrieve_audit_timeline(
    run_id: uuid.UUID,
    session: SessionDependency,
) -> AuditTimelineResponse:
    try:
        return get_audit_timeline(session, run_id)
    except AuditTimelineNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "audit_timeline_not_found",
                "message": "Policy analysis audit timeline was not found.",
            },
        ) from error
