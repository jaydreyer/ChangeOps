# Milestone 6 — Real Jira Execution Integration

## Status

Implemented.

## Product capability

Exactly one new action is executable:

```text
operational_remediation / enterprise_document
  → jira / create_issue
```

The golden proposed assessment creates one remediation recommendation for the primary policy
document. After the immutable baseline/proposed comparison exists, a reviewer may approve that
recommendation, an admin may prepare its immutable command, and an admin may explicitly create one
Jira Cloud Task.

## Boundaries

ChangeOps owns approval, immutable commands, deterministic comparison-aware routing, persistence,
delivery control, replay protection, and history. Jira owns the created work item. AI owns nothing
during preparation or execution.

The adapter supports create Task only. It performs no update, delete, transition, comment,
attachment, search, synchronization, webhook, polling, background work, queue operation, or MCP
call. The configured Task workflow must begin in To Do.

## Issue product contract

The frozen ADF description contains readable Business summary, Policy comparison, Operational
impact, Deterministic reason, Evidence reviewed, and ChangeOps audit lineage sections. It includes
the command and comparison IDs, baseline/proposed assessments, accepted extraction lineage, and a
statement that ChangeOps generated the issue after explicit human approval.

## Idempotency

One durable delivery gate is reserved before the external call. Success stores one immutable Jira
receipt and replay is local. Definitive no-side-effect failures are safely retryable; ambiguous
failures are not resent. This at-most-once policy is required because Jira Create Issue has no
unique client idempotency key and this milestone excludes reconciliation search.

## Configuration and testing

Base URL, email, API token, project identifier, Task issue-type identifier, and timeout come from
environment variables. CI uses injected/mock adapters and never requires a live Jira account.
Coverage includes pure template/mapping tests, adapter request/error tests, PostgreSQL migration and
idempotency tests, execution API tests, and workbench rendering checks.
