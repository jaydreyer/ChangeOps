from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

ApprovalRunStatus = Literal["initializing", "awaiting_decisions", "completed", "failed"]
ApprovalRunStep = Literal["create_reviews", "evaluate_reviews", "await_decisions", "finalize"]
ApprovalRoute = Literal["await_decisions", "complete"]
ApprovalFailureCode = Literal[
    "approval_assessment_not_found",
    "approval_assessment_not_completed",
    "approval_run_initialization_failed",
    "approval_review_membership_mismatch",
    "approval_run_state_invalid",
    "approval_resume_failed",
    "approval_persistence_error",
]

TERMINAL_REVIEW_STATUSES = {
    "approved",
    "rejected",
    "deferred",
    "revision_requested",
}


@dataclass(frozen=True)
class ApprovalProgress:
    total: int
    pending: int
    approved: int
    rejected: int
    deferred: int
    revision_requested: int

    def __post_init__(self) -> None:
        values = (
            self.total,
            self.pending,
            self.approved,
            self.rejected,
            self.deferred,
            self.revision_requested,
        )
        if any(value < 0 for value in values):
            raise ValueError("approval counts must be nonnegative")
        if self.total != sum(values[1:]):
            raise ValueError("approval total must equal the sum of review states")

    @property
    def route(self) -> ApprovalRoute:
        return "await_decisions" if self.pending else "complete"


def calculate_approval_progress(statuses: Iterable[str]) -> ApprovalProgress:
    counts = {
        "pending": 0,
        "approved": 0,
        "rejected": 0,
        "deferred": 0,
        "revision_requested": 0,
    }
    for status in statuses:
        if status not in counts:
            raise ValueError(f"unsupported action review status: {status}")
        counts[status] += 1
    return ApprovalProgress(total=sum(counts.values()), **counts)


def map_approval_failure(error: Exception, *, phase: str) -> ApprovalFailureCode:
    if isinstance(error, ValueError):
        return "approval_review_membership_mismatch"
    if phase == "initialize":
        return "approval_run_initialization_failed"
    if phase == "resume":
        return "approval_resume_failed"
    return "approval_persistence_error"
