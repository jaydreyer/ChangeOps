# ChangeOps

ChangeOps analyzes operational and policy changes, identifies affected people and systems, recommends evidence-backed actions, and preserves an auditable decision trail.

## Current milestone

Milestone 2, PR 3: Grounded Coverage-Gap Interpretation.

Milestone 0 is complete and preserved by the `v0.0.1-milestone-0` tag.

See:

- `docs/product-brief.md`
- `docs/milestone-0.md`
- `docs/milestone-1.md`
- `docs/milestone-2.md`
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
evidence, or incomplete mapping coverage. Pure deterministic validation resolves every policy
span, assessment impact, evidence key, and relationship-path reference before a separate immutable
change plan is accepted.

Interpretation is non-authoritative: it cannot add, remove, reclassify, or edit deterministic
impacts, evidence, reason codes, paths, actions, or counts. Provider and grounding failures create
append-only failed attempts and never change the completed run or assessment. Creation is
idempotent; PostgreSQL permits at most one accepted change plan per assessment while failed
attempts remain available for audit and retry. Returning an existing plan does not construct or
require a configured interpretation provider.

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
provider/model are `openai` and `gpt-5-mini`; override them with
`EXTRACTION_MODEL_PROVIDER` and `EXTRACTION_MODEL`. Interpretation defaults to the same provider
and model family and can be configured independently with `INTERPRETATION_MODEL_PROVIDER` and
`INTERPRETATION_MODEL`.

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

The integration suite creates and removes a dedicated `changeops_test` database. It does not use the development database for test assessments.

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
