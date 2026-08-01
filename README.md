# ChangeOps

ChangeOps analyzes operational and policy changes, identifies affected people and systems, recommends evidence-backed actions, and preserves an auditable decision trail.

## Current milestone

Milestone 2, PR 1: Structured Policy Extraction.

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

This slice intentionally has no LangGraph workflow, clarification, pause/resume, assessment
creation, interpretation, agent, RAG, or UI.

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
`EXTRACTION_MODEL_PROVIDER` and `EXTRACTION_MODEL`.

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

The create operation returns `201 Created` and a `Location` header containing the retrieval path.

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
