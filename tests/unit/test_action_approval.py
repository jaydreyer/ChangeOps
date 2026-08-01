import pytest

from changeops.domain.action_approval import (
    ApprovalProgress,
    calculate_approval_progress,
    map_approval_failure,
)


def test_mixed_terminal_decisions_complete_with_deterministic_summary() -> None:
    progress = calculate_approval_progress(
        [
            "approved",
            "approved",
            "rejected",
            "deferred",
            "revision_requested",
        ]
    )

    assert progress == ApprovalProgress(
        total=5,
        pending=0,
        approved=2,
        rejected=1,
        deferred=1,
        revision_requested=1,
    )
    assert progress.route == "complete"


def test_pending_decisions_route_to_durable_wait() -> None:
    progress = calculate_approval_progress(["pending", "approved"])

    assert progress.pending == 1
    assert progress.route == "await_decisions"


def test_count_total_and_review_state_are_validated() -> None:
    with pytest.raises(ValueError, match="sum"):
        ApprovalProgress(
            total=2,
            pending=1,
            approved=0,
            rejected=0,
            deferred=0,
            revision_requested=0,
        )
    with pytest.raises(ValueError, match="unsupported"):
        calculate_approval_progress(["running"])


def test_failure_codes_are_stable_and_phase_specific() -> None:
    assert (
        map_approval_failure(ValueError("mismatch"), phase="resume")
        == "approval_review_membership_mismatch"
    )
    assert (
        map_approval_failure(RuntimeError("technical"), phase="initialize")
        == "approval_run_initialization_failed"
    )
    assert (
        map_approval_failure(RuntimeError("technical"), phase="resume") == "approval_resume_failed"
    )
