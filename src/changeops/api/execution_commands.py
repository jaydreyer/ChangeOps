import uuid
from typing import Annotated

from fastapi import APIRouter, Body, Header, Response, status
from fastapi.exceptions import HTTPException
from pydantic import ValidationError

from changeops.api.dependencies import SessionDependency
from changeops.schemas.execution_commands import (
    ExecutionCommandPreparationResponse,
    ExecutionCommandResponse,
    ExecutionResultResponse,
)
from changeops.services.action_approval_service import ActionApprovalRunNotFoundError
from changeops.services.execution_command_serializer import (
    serialize_execution_command,
    serialize_execution_command_preparation,
    serialize_execution_result,
)
from changeops.services.execution_command_service import (
    ApprovalRunNotCompletedError,
    ExecutionCommandConflictError,
    ExecutionCommandInconsistentError,
    ExecutionCommandNotFoundError,
    get_execution_command,
    get_execution_command_preparation,
    prepare_execution_commands,
)
from changeops.services.learning_execution_service import (
    ExecutionActorNotAuthorizedError,
    ExecutionCommandIneligibleError,
    execute_command,
)
from changeops.services.learning_execution_service import (
    ExecutionCommandNotFoundError as ExecutableCommandNotFoundError,
)

router = APIRouter(prefix="/api/v1", tags=["execution-commands"])

ActorIdentityHeader = Annotated[str | None, Header(alias="X-ChangeOps-Actor")]
ActorRoleHeader = Annotated[str | None, Header(alias="X-ChangeOps-Role")]


@router.post(
    "/action-approval-runs/{run_id}/execution-commands",
    response_model=ExecutionCommandPreparationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_execution_commands(
    run_id: uuid.UUID,
    response: Response,
    session: SessionDependency,
    request_body: Annotated[None, Body()] = None,
    actor_identity: ActorIdentityHeader = None,
    actor_role: ActorRoleHeader = None,
) -> ExecutionCommandPreparationResponse:
    del request_body
    identity = (actor_identity or "").strip()
    if not identity or actor_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "execution_preparer_not_authorized",
                "message": "An authorized admin execution preparer is required.",
            },
        )
    try:
        result = prepare_execution_commands(
            session,
            run_id,
            actor_identity=identity,
            actor_role=actor_role,
        )
    except ActionApprovalRunNotFoundError as error:
        raise _run_not_found(error) from error
    except ApprovalRunNotCompletedError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "approval_run_not_completed",
                "message": "Execution commands require a completed approval run.",
            },
        ) from error
    except ExecutionCommandConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "execution_command_conflict",
                "message": str(error),
            },
        ) from error
    except (ExecutionCommandInconsistentError, ValidationError) as error:
        raise _inconsistent(error) from error
    if result.created_count == 0:
        response.status_code = status.HTTP_200_OK
    response.headers["Location"] = f"/api/v1/action-approval-runs/{run_id}/execution-commands"
    return serialize_execution_command_preparation(result)


@router.get(
    "/action-approval-runs/{run_id}/execution-commands",
    response_model=ExecutionCommandPreparationResponse,
)
def list_execution_commands(
    run_id: uuid.UUID,
    session: SessionDependency,
) -> ExecutionCommandPreparationResponse:
    try:
        return serialize_execution_command_preparation(
            get_execution_command_preparation(session, run_id)
        )
    except ActionApprovalRunNotFoundError as error:
        raise _run_not_found(error) from error
    except (ExecutionCommandInconsistentError, ValidationError) as error:
        raise _inconsistent(error) from error


@router.get(
    "/execution-commands/{command_id}",
    response_model=ExecutionCommandResponse,
)
def retrieve_execution_command(
    command_id: uuid.UUID,
    session: SessionDependency,
) -> ExecutionCommandResponse:
    try:
        return serialize_execution_command(get_execution_command(session, command_id))
    except ExecutionCommandNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "execution_command_not_found",
                "message": "Execution command was not found.",
            },
        ) from error
    except ExecutionCommandInconsistentError as error:
        raise _inconsistent(error) from error


@router.post(
    "/execution-commands/{command_id}/execute",
    response_model=ExecutionResultResponse,
    status_code=status.HTTP_201_CREATED,
)
def execute_execution_command(
    command_id: uuid.UUID,
    response: Response,
    session: SessionDependency,
    request_body: Annotated[None, Body()] = None,
    actor_identity: ActorIdentityHeader = None,
    actor_role: ActorRoleHeader = None,
) -> ExecutionResultResponse:
    del request_body
    identity = (actor_identity or "").strip()
    if not identity or actor_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "execution_actor_not_authorized",
                "message": "An authorized admin execution actor is required.",
            },
        )
    try:
        outcome = execute_command(
            session,
            command_id,
            actor_identity=identity,
            actor_role=actor_role,
        )
    except ExecutableCommandNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "execution_command_not_found",
                "message": "Execution command was not found.",
            },
        ) from error
    except ExecutionActorNotAuthorizedError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "execution_actor_not_authorized",
                "message": str(error),
            },
        ) from error
    except ExecutionCommandIneligibleError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "execution_command_ineligible",
                "message": str(error),
            },
        ) from error

    serialized = serialize_execution_result(outcome.result)
    if outcome.result.status == "already_applied":
        response.status_code = status.HTTP_200_OK
    elif outcome.result.status in {
        "rejected_unsupported",
        "failed_validation",
        "failed_authentication",
        "failed_unavailable",
    }:
        error_status = (
            status.HTTP_503_SERVICE_UNAVAILABLE
            if outcome.result.status == "failed_unavailable"
            else status.HTTP_401_UNAUTHORIZED
            if outcome.result.status == "failed_authentication"
            else status.HTTP_422_UNPROCESSABLE_CONTENT
        )
        raise HTTPException(
            status_code=error_status,
            detail={
                "code": outcome.result.outcome_code,
                "message": outcome.result.message,
                "execution_result": serialized.model_dump(mode="json"),
            },
        )
    return serialized


def _run_not_found(error: Exception) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "code": "action_approval_run_not_found",
            "message": "Action approval run was not found.",
        },
    )


def _inconsistent(error: Exception) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": "execution_command_inconsistent",
            "message": (
                str(error)
                if isinstance(error, ExecutionCommandInconsistentError)
                else "Persisted execution command data is inconsistent."
            ),
        },
    )
