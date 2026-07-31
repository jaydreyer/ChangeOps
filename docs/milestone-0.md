#   Milestone 0: Deterministic Impact-Assessment Foundation

## Objective

Implement the smallest backend slice that proves ChangeOps can convert a policy change into an evidence-backed impact assessment and a proposed action requiring human approval.

## Scenario

A fictional company changes its international-travel policy:

> International employee travel now requires vice-president approval.

The system evaluates the change against seeded enterprise data and identifies one affected employee.

## Required behavior

1. Seed one organization, one employee, one policy change, and enough supporting data to establish why the employee is affected.
2. Provide an API operation that creates an analysis for the seeded policy change.
3. Persist the completed analysis in PostgreSQL.
4. Return:
   - the affected employee;
   - the impact explanation;
   - references to the evidence used;
   - one proposed action;
5. Provide an API operation for retrieving the analysis by ID.
6. Preserve the result across application restarts.
7. Include automated tests for the primary flow.

## Architectural constraints

- Use Python, FastAPI, PostgreSQL, SQLAlchemy, Alembic, and Docker Compose.
- Keep analysis deterministic for this slice.
- Do not use an LLM or LangGraph yet.
- Do not add a frontend.
- Do not add authentication or authorization.
- Do not add MCP.
- Do not simulate Workday, Salesforce, Jira, or other external systems.
- Do not introduce a vector database.
- Keep domain logic separate from FastAPI route handlers.
- Use explicit domain names such as `PolicyChange`, `ImpactAssessment`, `Evidence`, `ProposedAction`, and `ApprovalStatus`.

## Acceptance criteria

- The development environment starts with one documented command.
- Database migrations run successfully.
- Seed data can be loaded repeatedly without creating duplicates.
- Creating an analysis returns a persisted analysis ID.
- Retrieving that ID returns the affected employee, explanation, evidence, proposed action, and approval status.
- The proposed action remains unexecuted.
- Tests demonstrate the full API-to-database flow.
- The README explains how to run and test the slice.

## Before implementation

Inspect the existing repository and provide:

1. The proposed file changes.
2. The proposed database schema.
3. The API request and response contracts.
4. The deterministic analysis rule.
5. The test plan.
6. Any assumptions or recommended deviations.

Do not begin implementation until the plan has been reviewed.