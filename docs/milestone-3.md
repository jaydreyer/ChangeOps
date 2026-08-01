# Milestone 3 — Human Review and Approval

## Status

Complete. PR 1 implements the action-review and decision foundation. PR 2 adds the separate
durable action-approval run, deterministic interruption/resume, ordered review membership, and
workflow audit history. PR 3 adds the focused local approval workbench.

## Product goal

Place an explicit, explainable human decision boundary around each immutable proposed action before
any consequential execution can be introduced.

A reviewer can inspect one persisted action and its evidence references, then approve it as
proposed, approve an allowed edited snapshot, reject it, defer it, or request revision. Every
decision records the trusted request actor, role, rationale, and timestamp.

## PR 1 — Action review and decision foundation

### Item-level aggregate

Each `proposed_actions` row may have at most one `action_reviews` row. Creating a review snapshots
the action and relevant evidence context in the same transaction. The review is self-contained for
audit, while the source action remains the authoritative immutable assessment artifact.

The original snapshot schema is `action-review-v1` and includes the action, assessment, finding,
enterprise-impact, worker, type, target, description, due date, and execution-status fields.
Review context records the applicable finding or impact, reason code, and stable evidence keys.

### State transitions

```text
pending ──→ approved
        ├─→ rejected
        ├─→ deferred
        └─→ revision_requested
```

Only the first terminal decision is accepted. Reopening, superseding, sequential rounds, quorum,
and multi-stage approval are not part of this slice.

### Edited snapshots

Approval may store a separate typed snapshot containing a changed `description`, `due_date`, or
both. Action type, target identity, worker, finding, and enterprise-impact references cannot be
changed during approval. A changed due date must be on or after the decision date.

The API derives the effective approved action by overlaying approved edits on the original
snapshot. It does not create an executable action and never changes
`proposed_actions.execution_status = not_executed`.

### Authorization boundary

Decision writes use the narrow demonstration request contract:

- `X-ChangeOps-Actor`: nonempty actor identity;
- `X-ChangeOps-Role`: `reviewer` or `admin`.

The persisted reviewer identity comes only from these trusted request headers; it cannot be
supplied independently in the request body. This boundary demonstrates role-aware authorization
but is not production authentication. It does not add users, sessions, passwords, JWT issuance,
OAuth, or organization administration.

### Audit and database guarantees

PostgreSQL enforces:

- one review per proposed action;
- assessment/action lifecycle consistency through a composite foreign key;
- zero or one decision per review;
- a terminal status matching its decision;
- no decision on a pending review and no terminal review without a decision;
- append-only decision rows;
- immutable review identity and snapshots;
- immutable terminal reviews;
- row-locked, single-winner decision submission.

Review creation locks the proposed action and decision submission locks the review. Database
uniqueness constraints remain the final protection against duplicate concurrent writes.

### API

```text
POST /api/v1/proposed-actions/{proposed_action_id}/review
GET  /api/v1/proposed-actions/{proposed_action_id}/review
GET  /api/v1/action-reviews/{review_id}
POST /api/v1/action-reviews/{review_id}/decisions
```

Review creation returns `201` for a new review and `200` for the existing review. A concurrent or
repeated terminal decision returns `409 action_review_already_decided`.

## Explicit separation from execution

This milestone slice does not execute an action, update an execution status, call enterprise
systems, introduce MCP, or allow AI to make or recommend approval decisions. Approval is a durable
human record only.

## PR 2 — Durable action-approval workflow

### Separate lifecycle

Approval is a separate aggregate and graph:

```text
PolicyAnalysisRun(completed)
  → ImpactAssessment(completed, immutable)
  → ActionApprovalRun(initializing)
  → ActionApprovalRun(awaiting_decisions)
  → ActionApprovalRun(completed)
```

The completed policy-analysis run never moves backward. Approval can happen hours or days later,
has its own technical failures and audit history, and will be the boundary consumed by future
execution work.

### Initialization and membership

One database-enforced run exists per assessment. Creation locks the completed assessment, requires
that it belongs to a completed policy-analysis run, and returns the existing run under repeated or
concurrent requests. Initialization loads all proposed actions in stable worker/type/target order,
uses the PR 1 transaction-owned review helper to create or reuse each review, and atomically inserts
one immutable membership item per action and review. Existing pending and terminal decisions are
preserved and counted.

### Pause and resume

PostgreSQL is authoritative. LangGraph state contains only the run ID and small routing values. The
graph ends after persisting `awaiting_decisions / await_decisions`; it never holds an HTTP request,
sleeps, polls, or relies on an in-memory thread while waiting for people.

After an authorized decision commits, the API finds the run through immutable membership and
invokes the graph. Evaluation locks the run row, reloads every persisted review, validates
membership, and recalculates all six counts. It pauses again when any review is pending and
completes when none are pending. An authorized `reviewer` or `admin` can call the explicit resume
endpoint for recovery. No-op awaiting resumes and completed resumes are idempotent.

### Completion, failure isolation, and audit

Approved, rejected, deferred, and revision-requested reviews are all terminal for this slice. A
mixed decision set completes the workflow; the summary makes no business-success judgment.
Deferred and revision-requested actions are closed for this workflow but are not executable.

Human decisions commit before automatic resume. An unexpected resume failure cannot erase or roll
back the decision, and explicit resume can reconcile later. Initialization membership is atomic.
Stable failure codes and sanitized messages are stored without unrestricted exception details.

Append-only transitions expose run creation, initialization, meaningful reevaluation, completion,
and failure. Database constraints enforce assessment/analysis ownership, action/review/run
ownership, unique ordered membership, count totals, terminal timestamps, immutable completed runs,
and append-only items and transitions.

### API and evaluation

```text
POST /api/v1/impact-assessments/{assessment_id}/approval-run
GET  /api/v1/impact-assessments/{assessment_id}/approval-run
GET  /api/v1/action-approval-runs/{run_id}
POST /api/v1/action-approval-runs/{run_id}/resume
```

Explicit resume uses the same demonstration actor and role headers as decisions. These headers are
not production authentication.

The offline fixture evaluation uses deterministic review-state fixtures and no provider:

```bash
python -m changeops.evaluation.approval_workflow \
  tests/golden/approval_workflow/v1/dataset.json
```

## PR 3 — Focused approval workbench

The minimal local Next.js application begins at a completed assessment. It creates or retrieves
one approval run, renders immutable membership order, resolves persisted evidence and deterministic
context, and submits terminal decisions through the existing item write API. A same-origin Next.js
proxy uses the configurable API base URL; browser state is limited to form inputs.

`GET /api/v1/action-approval-runs/{run_id}/workbench` is a deterministic read projection, not a
domain aggregate or generic backend-for-frontend framework. It performs no writes and stores no
snapshot. Missing membership, finding, impact, evidence, reason-code, or relationship-path context
fails with a stable sanitized error.

The workbench uses explicit provenance labels for AI proposals, deterministic conclusions, human
decisions, workflow state, and execution state. After every decision or manual reconciliation it
reloads authoritative API state. Approval can edit description and due date only. No decision
executes an action; completed review explicitly states that approved actions remain unexecuted.

The Compose seed supplies a stable provider-free completed demonstration assessment. Policy
submission, extraction monitoring, clarification, and interpretation screens remain intentionally
deferred.
