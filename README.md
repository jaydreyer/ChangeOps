# ChangeOps

ChangeOps analyzes operational and policy changes, identifies affected people and systems, recommends evidence-backed actions, and preserves an auditable decision trail.

## Current milestone

Milestone 3, PR 2: Durable Action-Approval Workflow.

The complete Milestone 2 backend remains protected by automated merge-quality checks. Milestone 3
now adds item-level review creation and decisions plus a separate durable assessment-level approval
run that pauses and resumes around those human decisions. The reviewer UI remains a later slice;
Milestone 3 is not complete.

Milestone 0 is complete and preserved by the `v0.0.1-milestone-0` tag.

See:

- `docs/product-brief.md`
- `docs/milestone-0.md`
- `docs/milestone-1.md`
- `docs/milestone-2.md`
- `docs/milestone-3.md`
- `docs/demo-scenario.md`
- `docs/decisions.md`
- [Contributing and engineering standards](CONTRIBUTING.md)

## Project direction

See `docs/roadmap.md` for the milestone sequence and planned introduction of LangChain, LangGraph, MCP, the frontend, and AWS.

## Milestone 1 behavior

The current backend preserves the Milestone 0 worker-and-trip result and additionally:

- seeds the six-worker international-travel scenario;
- validates the policy's structured rules into a typed travel-policy model;
- applies deterministic worker, destination, effective-date, booking, and training rules;
- traces affected workers to managers, teams, systems, documents, training, and customer
  commitments through explicit PostgreSQL relationships;
- returns 18 categorized enterprise impacts with stable reason codes, evidence, and ordered
  relationship paths;
- persists the complete immutable assessment aggregate in one transaction;
- returns three affected workers, three unaffected workers, six original findings, 13 unexecuted
  proposed actions, and eight scenario-defined unresolved questions.

The Milestone 1 assessment behavior remains unchanged.

## Structured policy extraction

The first Milestone 2 slice converts stored policy text into proposed typed rules using LangChain
structured output, then validates source spans, supported constructs, business rules, and
enterprise course references deterministically. The model extracts the human course name;
deterministic code resolves its enterprise identifier.

Each invocation creates an append-only extraction attempt with raw output, candidate and accepted
rules, validation errors, and model/provider/prompt/schema metadata. Unsupported and invalid output
fails closed and never reaches the impact engine.

## Durable policy-analysis workflow

The second Milestone 2 slice wraps extraction in a narrow LangGraph state machine backed by
authoritative PostgreSQL application records. A run either completes with one deterministic
assessment, pauses on one bounded typed clarification, terminates as unsupported, or fails with a
stable code. Technical extraction failures receive at most one fresh append-only attempt.

Clarification is deterministic and deliberately narrow. Because the existing schema-v1 assessment
rule is `Literal[True]`, the workflow asks for an explicit `true` acknowledgement only when
conflicting pre-effective-date booking behavior could change the rule and assessment.
Malformed JSON is retried, not sent to a human; unsupported families and unresolved enterprise
course references terminate without blind retries.

Only a persisted extraction attempt with `validation_outcome = accepted`, resolved typed rules,
and no pending clarification can cross the assessment adapter. Human answers retain their own
clarification ID, responder, timestamp, and affected field; no source span is fabricated.
`policy_changes.structured_rules` is never changed.

## Grounded coverage-gap interpretation

The third Milestone 2 slice interprets only the persisted artifacts of a completed policy-analysis
assessment. A structured model may propose review concerns about unsupported concepts, missing
evidence, or incomplete mapping coverage. Its output cites only exact policy quotes, existing impact
IDs, and existing evidence keys. Application code deterministically adds policy and assessment IDs,
character offsets, and evidence owners before pure validation resolves every reference and accepts
a separate immutable change plan.

Interpretation is non-authoritative: it cannot add, remove, reclassify, or edit deterministic
impacts, evidence, reason codes, paths, actions, or counts. Provider and grounding failures create
append-only failed attempts and never change the completed run or assessment. Creation is
idempotent; PostgreSQL permits at most one accepted change plan per assessment while failed
attempts remain available for audit and retry. Returning an existing plan does not construct or
require a configured interpretation provider.

## Action review and decision foundation

Each persisted proposed action can have one idempotently created review. The review snapshots the
original unexecuted action and relevant evidence keys without updating the assessment or proposed
action. An authorized `reviewer` or `admin` can submit exactly one approval, rejection, deferral, or
revision request with rationale.

Approval may store a separate edited description and/or due date. The API deterministically
derives the effective approved action while preserving the original snapshot. PostgreSQL triggers
make decisions append-only and terminal reviews immutable; row locks and uniqueness constraints
provide a single winner under concurrent creation or decision attempts. No reviewed action is
executed, and every proposed action remains `not_executed`.

## Durable action-approval workflow

A completed policy-analysis assessment can now create one idempotent `ActionApprovalRun`. The run
creates or reuses one review for each proposed action, stores explicit ordered membership, derives
counts from persisted review states, and records append-only workflow transitions. It is separate
from the already-completed `PolicyAnalysisRun`; approval never reopens analysis or mutates its
immutable assessment.

The narrow deterministic LangGraph invocation ends as soon as the run persists
`awaiting_decisions / await_decisions`. Each authorized decision commits first, then synchronously
resumes the same run. The graph recalculates all counts under a run row lock and either pauses again
or completes when every item is terminal. Approval, rejection, deferral, and revision request all
close an item; the decision mix is summarized without treating non-approval as a technical failure.

Unexpected automatic-resume failure cannot roll back a committed human decision. Authorized
reviewers and admins can use the idempotent explicit resume endpoint to reconcile persisted state.
Completed runs and no-op waiting resumes remain unchanged. Nothing executes, including approved
actions.

## Requirements

- Docker Desktop or another Docker Engine with Docker Compose
- `curl` for the manual smoke test

No host Python or PostgreSQL installation is required.

## Run

Start PostgreSQL, apply migrations, load the idempotent seed data, and start the API:

```bash
docker compose up --build
```

The API is available at `http://localhost:8000`. Verify it in another terminal:

```bash
curl --fail http://localhost:8000/healthz
```

Expected response:

```json
{"status":"ok"}
```

To exercise live extraction, copy `.env.example` to `.env` and set `OPENAI_API_KEY`. The default
provider/model are `openai` and `gpt-5.6-luna`; override them with
`EXTRACTION_MODEL_PROVIDER` and `EXTRACTION_MODEL`. Interpretation defaults to the same provider
and model family and can be configured independently with `INTERPRETATION_MODEL_PROVIDER` and
`INTERPRETATION_MODEL`. Provider calls default to a 120-second timeout with provider-library
retries disabled; configure these bounds with `*_MODEL_TIMEOUT_SECONDS` and
`*_MODEL_MAX_RETRIES`. The policy-analysis workflow still owns its one bounded fresh-attempt retry.

Stop the stack while preserving database data:

```bash
docker compose down
```

## Test

Run all unit and PostgreSQL integration tests:

```bash
docker compose run --rm api pytest
```

Run only the pure deterministic analyzer tests:

```bash
docker compose run --rm api pytest tests/unit
```

Run the code-quality checks:

```bash
docker compose run --rm api ruff check src migrations tests
docker compose run --rm api ruff format --check src migrations tests
```

Run the versioned fixture-based extraction evaluation without a live provider:

```bash
docker compose run --rm api python -m changeops.evaluation.extraction \
  tests/golden/extraction/v1/dataset.json
```

Run the scoped deterministic workflow scenario evaluation:

```bash
docker compose run --rm api python -m changeops.evaluation.workflow \
  tests/golden/workflow/v1/dataset.json
```

Run the fixture-based interpretation grounding evaluation without a live provider:

```bash
docker compose run --rm api python -m changeops.evaluation.interpretation \
  tests/golden/interpretation/v1/dataset.json
```

Run the deterministic approval-workflow evaluation:

```bash
docker compose run --rm api python -m changeops.evaluation.approval_workflow \
  tests/golden/approval_workflow/v1/dataset.json
```

The integration suite creates and removes a dedicated `changeops_test` database. It does not use the development database for test assessments.

Pull requests and pushes to `main` run the same Compose-based lint, format, pytest, and four
offline evaluation commands in GitHub Actions. CI explicitly clears `OPENAI_API_KEY`, so ordinary
quality checks use fixture models and cannot inherit repository or runner provider credentials.

The separate `migration` check creates an empty PostgreSQL database, upgrades to the discovered
Alembic head, downgrades that head by one revision, and upgrades back to head. Repository owners
should configure branch protection to require the stable `quality` and `migration` checks before
merge.

## Live AI smoke verification

The `Live AI Smoke` GitHub Actions workflow is available only through manual `workflow_dispatch`.
It requires the `OPENAI_API_KEY` repository secret and starts a fresh isolated Compose stack. The
smoke runs real extraction and interpretation for the canonical policy, verifies the deterministic
3/3 worker split, 6 findings, 18 enterprise impacts, 13 unexecuted actions, and 8 unresolved
questions, then checks accepted grounding, plan retrieval, idempotency, and assessment immutability.

Workflow output contains only provider/model names, elapsed time, lifecycle identifiers, terminal
outcome, and a stable failure code. It does not emit provider envelopes, raw model output,
authorization data, or unrestricted exception text. A successful live call is deliberately not
required for ordinary offline development or pull-request CI.

## Database operations

Apply all pending schema migrations:

```bash
docker compose run --rm migrate
```

Reload the idempotent scenario seed:

```bash
docker compose run --rm seed
```

Reset all local ChangeOps database data:

```bash
docker compose down -v
```

The `-v` form permanently deletes the local ChangeOps PostgreSQL volume. The next `docker compose up --build` recreates, migrates, and seeds it.

## API

Create an assessment for the seeded policy:

```http
POST /api/v1/policy-changes/policy-international-travel-2026-09/impact-assessments
```

Retrieve a persisted assessment:

```http
GET /api/v1/impact-assessments/{assessment_id}
```

Create a new append-only extraction attempt:

```http
POST /api/v1/policy-changes/{policy_change_id}/extraction-attempts
```

Retrieve an extraction attempt, including failures:

```http
GET /api/v1/policy-extraction-attempts/{attempt_id}
```

Create and execute a policy-analysis run:

```http
POST /api/v1/policy-analysis-runs
Content-Type: application/json

{"policy_change_id":"policy-international-travel-2026-09"}
```

Policy analysis is synchronous while the configured model is running. During that call, retrieving
the run reports `status = running` and `current_step = extract`, and API logs record model-call
start, completion, elapsed time, and a sanitized error category. Use `curl --show-error --verbose`
when exercising a live provider so the open request is visible.

Retrieve durable state after completion or a process restart:

```http
GET /api/v1/policy-analysis-runs/{run_id}
```

Answer the pending typed clarification and resume:

```http
POST /api/v1/policy-analysis-runs/{run_id}/clarifications/{clarification_id}/answer
Content-Type: application/json

{"value":true,"responder_identity":"reviewer@example.com"}
```

The persisted answer contract is
`{"type":"literal","allowed_values":[true]}`; `false` is rejected without answering or advancing
the clarification.

Create or idempotently retrieve the accepted plan for a completed workflow assessment:

```http
POST /api/v1/impact-assessments/{assessment_id}/change-plans
GET /api/v1/impact-assessments/{assessment_id}/change-plan
GET /api/v1/change-plans/{change_plan_id}
```

Retrieve any interpretation attempt, including invalid and provider-failed attempts:

```http
GET /api/v1/policy-interpretation-attempts/{attempt_id}
```

Interpretation is explicitly requested after the policy-analysis run completes. A successful new
plan returns `201`; an existing plan returns `200`. Failed attempts do not block a later retry.

Create or idempotently retrieve a review, then retrieve it by either stable identifier:

```http
POST /api/v1/proposed-actions/{proposed_action_id}/review
GET /api/v1/proposed-actions/{proposed_action_id}/review
GET /api/v1/action-reviews/{review_id}
```

Submit the one terminal decision using the demonstration authorization headers:

```http
POST /api/v1/action-reviews/{review_id}/decisions
X-ChangeOps-Actor: reviewer@example.com
X-ChangeOps-Role: reviewer
Content-Type: application/json

{
  "decision": "approved",
  "rationale": "Approved with a clearer assignment description.",
  "edited_action": {
    "description": "Assign the updated international travel course.",
    "due_date": "2026-08-20"
  }
}
```

The headers are a replaceable demonstration boundary, not production authentication. Retrieval
remains unauthenticated.

Create or idempotently retrieve the approval run for a completed policy-analysis assessment:

```http
POST /api/v1/impact-assessments/{assessment_id}/approval-run
GET  /api/v1/impact-assessments/{assessment_id}/approval-run
GET  /api/v1/action-approval-runs/{run_id}
GET  /api/v1/action-approval-runs/{run_id}/workbench
```

Explicitly reconcile or resume the same run:

```http
POST /api/v1/action-approval-runs/{run_id}/resume
X-ChangeOps-Actor: reviewer@example.com
X-ChangeOps-Role: reviewer
```

Creation returns `awaiting_decisions` while any item is pending and may return `completed`
immediately when every reused review was already terminal. Resume returns `200` and is idempotent,
including for waiting runs with no new decision and completed runs. The demonstration headers are
not safe production authentication.

The workbench endpoint is a read-only, screen-oriented projection. It resolves immutable run
membership, complete review snapshots, findings, enterprise impacts, persisted evidence, and
ordered relationship paths without creating a durable workbench record. A missing reference
returns the stable `approval_workbench_inconsistent` error instead of silently dropping context.

## Local approval workbench

Start PostgreSQL, migrations, provider-free demonstration seed data, the API, and Next.js:

```bash
docker compose up --build
```

Open:

- API and OpenAPI docs: <http://localhost:8000/docs>
- approval workbench entry: <http://localhost:3000>

The Compose seed creates completed demonstration assessment
`8f4f647d-7f2d-4da8-8e02-77d5301f2002`. Enter that ID on the workbench home page. The page
idempotently creates or retrieves its approval run and displays every action in immutable
membership order.

The reviewer email field populates `X-ChangeOps-Actor`; decision and retry requests send
`X-ChangeOps-Role: reviewer`. These are trusted local demonstration headers, not login or
production authentication.

The interface labels AI proposals, deterministic conclusions, human decisions, workflow state,
and execution state in text. Approval may edit only description and due date. Every write is
followed by an authoritative server refresh. All terminal outcomes remain durable, and every
action remains `not_executed`.

Policy submission, extraction monitoring, clarification, and interpretation screens are
intentionally deferred. This slice begins at a completed assessment and does not call an LLM or an
enterprise system.

Create operations return `201 Created`; run, extraction, and change-plan creates include a
`Location` header.

## Manual smoke test

1. Start the complete stack in the background:

   ```bash
   docker compose up --build -d
   ```

2. Confirm the API is healthy:

   ```bash
   curl --fail http://localhost:8000/healthz
   ```

3. Create an assessment and inspect the response headers and body:

   ```bash
   curl --include --request POST \
     http://localhost:8000/api/v1/policy-changes/policy-international-travel-2026-09/impact-assessments
   ```

4. Copy the assessment path from the `Location` response header, then retrieve it:

   ```bash
   curl --fail \
     http://localhost:8000/api/v1/impact-assessments/PASTE_ASSESSMENT_ID_HERE
   ```

5. Restart only the API container:

   ```bash
   docker compose restart api
   ```

6. Repeat the retrieval command from step 4. The same completed assessment should still be returned from PostgreSQL.

7. Stop the stack without deleting the database volume:

   ```bash
   docker compose down
   ```
