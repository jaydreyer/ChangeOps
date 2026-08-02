# Milestone 4 — Controlled Enterprise Execution

## Status

Slices 1 and 2 are implemented. Slice 1 prepares immutable commands. Slice 2 explicitly executes
only `learning.assign_training` against a durable simulated learning system.

## Product boundary

Milestone 4 converts exact human-approved values into controlled enterprise effects:

```text
completed approval run
  → approved review
  → effective approved action
  → immutable execution command
  → explicit execution request
  → simulated learning adapter
  ├── durable learning assignment
  └── immutable execution result
```

Approval, authorization, execution intent, simulated enterprise state, and attempt history remain
separate artifacts. AI participates in none of these decisions or writes.

## Slice 1 — Execution Command Preparation

An authorized local `admin` may prepare commands for a completed approval run. Preparation uses
immutable membership order, approved reviews only, exact approved edits, canonical SHA-256
idempotency, and at most one command per review.

The only supported mapping is:

```text
training_assignment / worker
  → learning / assign_training
  → course international-travel-security
```

Manager approval, team review, system-workflow review, document, and customer-commitment actions
remain explicit unsupported projections. Approval does not make them executable.

## Slice 2 — First Executable Integration

The existing command contract is sufficient. It contains or references:

- the approved action and effective approved-action snapshot;
- worker and course identifiers;
- target system and operation;
- canonical idempotency key;
- assessment and optional assessment-linked change plan;
- approval run, review, decision, and proposed-action lineage;
- preparer identity, role, and time.

Execution-specific actor, outcome, time, and side-effect identity belong to the immutable execution
result and simulated assignment, so the command was not changed.

`POST /api/v1/execution-commands/{command_id}/execute` requires an explicit demonstration `admin`.
The service does not trust the submitted ID alone: it row-locks the command and reconstructs the
completed approval run, exact membership, approved review decision, effective action, deterministic
mapping, snapshot, and idempotency key from PostgreSQL.

The narrow `SimulatedLearningAdapter` then:

1. verifies `learning.assign_training`;
2. validates the closed payload;
3. verifies the worker and active course;
4. reuses an assignment already owned by the command, if present;
5. otherwise creates one simulated assignment;
6. appends an immutable execution result.

The assignment and successful result commit together. The same command cannot create a duplicate
assignment because execution locks the command and PostgreSQL uniquely owns assignments by
`source_execution_command_id`. Each replay deliberately appends an `already_applied` result
referencing the original assignment. This preserves every explicit attempt without duplicating
enterprise state.

## Persistence

`simulated_learning_assignments` is the authoritative simulated learning-system state for this
slice. It stores the worker, course, assigned state and time, source command, and source approved
action.

`execution_results` is immutable audit history. It distinguishes:

- `succeeded`;
- `already_applied`;
- `rejected_unsupported`;
- `failed_validation`.

Results store stable outcome codes and explanations, command identity, optional assignment, actor,
role, and timestamp. Commands remain immutable `pending_execution` authorization records.
Proposed actions remain immutable `not_executed` assessment records. Neither value is overloaded to
represent mutable connector state.

## Workbench

The existing post-completion panel shows:

- target system and operation;
- affected worker and training identifier;
- approval-decision and proposed-action lineage;
- pending, executed, or failed execution state;
- an explicit execution control only for supported prepared commands;
- durable assignment details and immutable result history;
- unsupported approved actions without active execution controls.

Execution never occurs during page load. Re-execution is labeled as safe and reports that the
original assignment was reused.

## Deliberate architectural limits

This slice adds no MCP, adapter registry, plugin system, connector interface, command bus, queue,
worker, scheduler, polling, retry orchestration, or generic execution engine. One explicit service
call is enough to validate the command boundary and transactional/idempotency behavior.

MCP is deferred because the current consumer runs safely within the modular monolith and has no
external protocol or process-boundary requirement. A later slice should introduce MCP only when a
real external tool boundary proves its value.

## Exit criteria

The slice is complete when a reviewer can trace an approved training action through its immutable
command, explicitly execute it, inspect one durable assignment and immutable result, repeat
execution without a duplicate, and continue to see every unsupported approval. Authorization,
lineage, validation, transactionality, concurrency, immutability, API behavior, UI behavior,
migrations, regressions, and offline evaluations must pass.
