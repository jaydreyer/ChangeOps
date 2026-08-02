import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from changeops.db.models import (
    ActionApprovalRun,
    ActionApprovalRunItem,
    ActionReview,
    ExecutionCommand,
    ExecutionResult,
    ProposedAction,
    SimulatedLearningAssignment,
    TrainingCourse,
    Worker,
)
from changeops.domain.action_review import (
    EditedActionSnapshot,
    OriginalActionSnapshot,
    derive_effective_approved_action,
)
from changeops.domain.execution_command import (
    command_idempotency_key,
    map_effective_action,
    snapshot_effective_action,
)
from changeops.domain.learning_execution import AssignTrainingParameters


class ExecutionCommandNotFoundError(Exception):
    pass


class ExecutionCommandIneligibleError(Exception):
    pass


class ExecutionActorNotAuthorizedError(Exception):
    pass


@dataclass(frozen=True)
class ExecutionOutcome:
    result: ExecutionResult
    assignment: SimulatedLearningAssignment | None


class SimulatedLearningAdapter:
    def assign_training(
        self,
        *,
        command: ExecutionCommand,
        session: Session,
        actor_identity: str,
        actor_role: str,
    ) -> ExecutionOutcome:
        attempted_at = datetime.now(UTC)
        if command.system != "learning" or command.operation != "assign_training":
            return self._record_result(
                session=session,
                command=command,
                status="rejected_unsupported",
                outcome_code="unsupported_execution_command",
                message=(
                    f"Execution target '{command.system}.{command.operation}' is not supported."
                ),
                actor_identity=actor_identity,
                actor_role=actor_role,
                attempted_at=attempted_at,
            )

        try:
            parameters = AssignTrainingParameters.model_validate(command.parameters_snapshot)
        except ValidationError:
            return self._record_result(
                session=session,
                command=command,
                status="failed_validation",
                outcome_code="invalid_execution_command_payload",
                message="The assign-training command payload is malformed.",
                actor_identity=actor_identity,
                actor_role=actor_role,
                attempted_at=attempted_at,
            )

        if (
            command.target_type != "worker"
            or command.target_identifier != parameters.worker_identifier
        ):
            return self._record_result(
                session=session,
                command=command,
                status="failed_validation",
                outcome_code="invalid_execution_command_target",
                message="The assign-training worker target is inconsistent.",
                actor_identity=actor_identity,
                actor_role=actor_role,
                attempted_at=attempted_at,
            )

        worker = session.get(Worker, parameters.worker_identifier)
        course = session.get(TrainingCourse, parameters.course_identifier)
        if worker is None or course is None or not course.active:
            return self._record_result(
                session=session,
                command=command,
                status="failed_validation",
                outcome_code="execution_reference_not_found",
                message="The command worker and active training course must exist.",
                actor_identity=actor_identity,
                actor_role=actor_role,
                attempted_at=attempted_at,
            )

        assignment = session.scalar(
            select(SimulatedLearningAssignment).where(
                SimulatedLearningAssignment.source_execution_command_id == command.id
            )
        )
        if assignment is not None:
            return self._record_result(
                session=session,
                command=command,
                assignment=assignment,
                status="already_applied",
                outcome_code="training_assignment_already_applied",
                message="This command already created the simulated training assignment.",
                actor_identity=actor_identity,
                actor_role=actor_role,
                attempted_at=attempted_at,
            )

        assignment = SimulatedLearningAssignment(
            worker_id=parameters.worker_identifier,
            training_course_id=parameters.course_identifier,
            source_execution_command_id=command.id,
            source_approved_action_id=command.proposed_action_id,
            assignment_status="assigned",
            assigned_at=attempted_at,
            created_at=attempted_at,
        )
        session.add(assignment)
        session.flush()
        return self._record_result(
            session=session,
            command=command,
            assignment=assignment,
            status="succeeded",
            outcome_code="training_assignment_created",
            message="The simulated learning system assigned the training item.",
            actor_identity=actor_identity,
            actor_role=actor_role,
            attempted_at=attempted_at,
        )

    @staticmethod
    def _record_result(
        *,
        session: Session,
        command: ExecutionCommand,
        status: str,
        outcome_code: str,
        message: str,
        actor_identity: str,
        actor_role: str,
        attempted_at: datetime,
        assignment: SimulatedLearningAssignment | None = None,
    ) -> ExecutionOutcome:
        result = ExecutionResult(
            execution_command_id=command.id,
            simulated_learning_assignment_id=assignment.id if assignment is not None else None,
            learning_assignment=assignment,
            status=status,
            outcome_code=outcome_code,
            message=message,
            command_idempotency_key=command.idempotency_key,
            attempted_by=actor_identity,
            attempted_role=actor_role,
            created_at=attempted_at,
        )
        session.add(result)
        session.flush()
        return ExecutionOutcome(result=result, assignment=assignment)


def execute_command(
    session: Session,
    command_id: uuid.UUID,
    *,
    actor_identity: str,
    actor_role: str,
) -> ExecutionOutcome:
    identity = actor_identity.strip()
    if not identity or actor_role != "admin":
        raise ExecutionActorNotAuthorizedError("An authorized admin execution actor is required.")
    with session.begin():
        command = session.scalar(
            select(ExecutionCommand).where(ExecutionCommand.id == command_id).with_for_update()
        )
        if command is None:
            raise ExecutionCommandNotFoundError(str(command_id))
        _validate_authoritative_eligibility(session, command)
        outcome = SimulatedLearningAdapter().assign_training(
            command=command,
            session=session,
            actor_identity=identity,
            actor_role=actor_role,
        )
    return outcome


def _validate_authoritative_eligibility(
    session: Session,
    command: ExecutionCommand,
) -> None:
    run = session.get(ActionApprovalRun, command.approval_run_id)
    review = session.scalar(
        select(ActionReview)
        .where(ActionReview.id == command.action_review_id)
        .options(selectinload(ActionReview.decisions))
    )
    membership = session.scalar(
        select(ActionApprovalRunItem).where(
            ActionApprovalRunItem.approval_run_id == command.approval_run_id,
            ActionApprovalRunItem.action_review_id == command.action_review_id,
            ActionApprovalRunItem.proposed_action_id == command.proposed_action_id,
            ActionApprovalRunItem.assessment_id == command.assessment_id,
        )
    )
    action = session.get(ProposedAction, command.proposed_action_id)
    if (
        run is None
        or run.status != "completed"
        or review is None
        or review.status != "approved"
        or membership is None
        or action is None
        or action.execution_status != "not_executed"
        or len(review.decisions) != 1
    ):
        raise ExecutionCommandIneligibleError(
            "The command is not backed by a completed, approved immutable lineage."
        )

    decision = review.decisions[0]
    if decision.id != command.action_review_decision_id or decision.decision != "approved":
        raise ExecutionCommandIneligibleError("The command approval decision is not authoritative.")

    try:
        original = OriginalActionSnapshot.model_validate(review.original_action_snapshot)
        edited = (
            EditedActionSnapshot.model_validate(decision.edited_action_snapshot)
            if decision.edited_action_snapshot is not None
            else None
        )
        effective = derive_effective_approved_action(original, edited)
        mapping = map_effective_action(effective)
    except ValidationError as error:
        raise ExecutionCommandIneligibleError(
            "The approved action lineage is malformed."
        ) from error

    candidate = mapping.command
    expected_snapshot = snapshot_effective_action(effective).model_dump(mode="json")
    if candidate is None:
        raise ExecutionCommandIneligibleError(
            "The approved action no longer has a supported deterministic mapping."
        )
    expected_key = command_idempotency_key(
        approval_decision_id=str(decision.id),
        command=candidate,
    )
    if (
        command.schema_version != candidate.schema_version
        or command.system != candidate.system
        or command.operation != candidate.operation
        or command.target_type != candidate.target_type
        or command.target_identifier != candidate.target_identifier
        or command.parameters_snapshot != candidate.parameters
        or command.effective_action_snapshot != expected_snapshot
        or command.idempotency_key != expected_key
        or command.status != "pending_execution"
    ):
        raise ExecutionCommandIneligibleError(
            "The command does not match its effective approved-action snapshot."
        )
