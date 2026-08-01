# Milestone 3 — Human Review and Approval

## Status

In progress. PR 1 implements the action-review and decision foundation. Durable workflow
interruption/resume and the reviewer interface remain later slices.

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

## Planned later slices

- PR 2: connect durable workflow interruption and resume to persisted action decisions;
- PR 3: add the focused reviewer interface at the roadmap-approved frontend boundary.

The later slices must consume this review aggregate without mutating historical assessments,
proposed actions, or decision events.
