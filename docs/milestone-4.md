# Milestone 4 — Controlled Enterprise Execution

## Status

Slice 1, Execution Command Preparation, is implemented. No command executes.

## Product boundary

Milestone 4 converts exact human-approved values into controlled enterprise effects. The first
slice establishes a durable boundary before any adapter or MCP tool exists:

```text
completed approval run
  → approved review
  → effective approved action
  → deterministic supported-action mapping
  → immutable execution command
  → pending execution
```

Approval decisions and execution commands are separate audit artifacts. The former proves what a
human decided; the latter proves what deterministic code authorized a future connector to do.

## Slice 1 capability

An authorized local `admin` may prepare commands for a completed approval run. Preparation:

- uses immutable run membership order;
- considers approved reviews only;
- reuses approved description and due-date overlay rules;
- reports unsupported approved actions explicitly;
- stores at most one command per review;
- uses a canonical semantic SHA-256 idempotency key;
- snapshots effective approved values and command parameters;
- keeps every command `pending_execution`;
- keeps every proposed action `not_executed`.

The only supported golden-scenario mapping is:

```text
training_assignment / worker
  → learning / assign_training
  → course international-travel-security
```

The other 11 golden actions are intentionally informational, human-owned, or not yet supported:
manager approval requests, team travel review, system-workflow review, document update/review, and
customer-commitment review. Approval does not make an action mechanically executable.

## Persistence and API

`execution_commands` contains relational provenance to the approval run, review, approval decision,
proposed action, and assessment. It stores versioned effective-action and command-parameter
snapshots, target and operation columns, a unique idempotency key, preparer identity and role, and
creation time.

PostgreSQL enforces lifecycle ownership, one command per review, approved-decision eligibility,
completed-run eligibility, immutable rows, and the only current status:
`pending_execution`.

```text
POST /api/v1/action-approval-runs/{run_id}/execution-commands
GET  /api/v1/action-approval-runs/{run_id}/execution-commands
GET  /api/v1/execution-commands/{command_id}
```

The POST accepts no action overrides. It returns `201` when any command is new and `200` when fully
idempotent. List responses derive unsupported results from immutable approvals instead of creating
a preparation-run aggregate.

## Workbench

The existing focused approval page adds one post-completion panel. It shows approved, preparable,
unsupported, and prepared counts; one explicit preparation control; immutable command details; and
unsupported reasons. Every command is labeled “Pending execution — no enterprise system called.”
There are no execution controls.

## Explicitly deferred

- MCP and tool invocation;
- simulated enterprise APIs;
- execution attempts, responses, retries, and compensation;
- queues, workers, schedulers, and generic command buses;
- current-system precondition checks;
- production authentication or generalized RBAC;
- generic adapter registries;
- earlier policy workflow screens;
- cloud infrastructure and observability.

## Exit criteria

Slice 1 is complete when supported approved reviews produce one immutable, idempotent command;
non-approved reviews never produce commands; unsupported approvals remain visible; approved edits
are snapshotted exactly; concurrent preparation cannot duplicate rows; commands remain pending;
proposed actions remain unexecuted; the workbench exposes the boundary; and backend, frontend,
migration, and offline quality checks pass.
