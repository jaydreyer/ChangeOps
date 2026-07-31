# ChangeOps Architecture

This document describes the current Milestone 1 implementation.

## High-level architecture

```mermaid
flowchart LR
    Client["HTTP client"]

    subgraph Compose["Local Docker Compose environment"]
        API["FastAPI API<br/>Uvicorn"]
        Migrate["Alembic migration job"]
        Seed["Idempotent seed job"]
        DB[("PostgreSQL 17<br/>persistent volume")]
    end

    subgraph Application["ChangeOps synchronous modular monolith"]
        Routes["API routes and<br/>Pydantic schemas"]
        Service["Assessment application service"]
        Rules["Typed policy-rule validation"]
        WorkerAnalyzer["Pure worker-and-trip analyzer"]
        EnterpriseAnalyzer["Pure enterprise-impact analyzer"]
        Fingerprint["Canonical input fingerprint"]
        Serializer["Stable response serializer"]
        ORM["SQLAlchemy models and sessions"]
    end

    Client -->|"POST or GET /api/v1"| API
    API --> Routes
    Routes --> Service
    Service --> Rules
    Service --> WorkerAnalyzer
    Service --> EnterpriseAnalyzer
    Service --> Fingerprint
    Service --> ORM
    Service --> Serializer
    ORM --> DB
    Migrate --> DB
    Seed --> DB
```

ChangeOps remains a synchronous modular monolith. The HTTP, application, domain, serialization, and
persistence code run in one Python process. PostgreSQL is the only separate application runtime.

## Major runtime components

### API

The FastAPI application preserves the existing endpoints:

- `GET /healthz`
- `POST /api/v1/policy-changes/{policy_change_id}/impact-assessments`
- `GET /api/v1/impact-assessments/{assessment_id}`

The create response adds an input fingerprint, enterprise-impact summary, and categorized
enterprise impacts. Existing worker results, findings, evidence, proposed actions, and unresolved
questions remain available.

Pydantic constrains impact domains, object types, classifications, and action types. It also
validates allowed domain-classification combinations.

### Assessment application service

The assessment service coordinates one synchronous transaction:

1. Load the policy and every organization record that can influence impact discovery.
2. Validate `policy_changes.structured_rules` as `InternationalTravelPolicyRules`.
3. Convert SQLAlchemy records to immutable domain input.
4. Run the existing pure worker-and-trip analyzer.
5. Run the pure enterprise-impact analyzer using the worker result and loaded context.
6. Calculate a SHA-256 fingerprint from canonicalized policy, source, dependency, and question
   input.
7. Persist the complete assessment aggregate.
8. Commit once, then reload the aggregate with explicit eager loading.

Any exception before commit rolls back the assessment, workers results, findings, evidence,
enterprise impacts, paths, actions, and copied questions.

### Deterministic analyzers

Both analyzers are pure Python. They do not import FastAPI or SQLAlchemy, perform database or
network I/O, or mutate input.

The Milestone 0 analyzer continues to evaluate:

- worker and trip scope;
- policy effective date;
- booking-date approval exception;
- security-training completion.

The Milestone 1 analyzer deterministically derives:

- directly affected workers;
- operationally affected managers and teams;
- systems connected to changed approval or training rules;
- documents connected through explicit policy dependencies;
- the policy-required course and worker-specific incomplete-training impacts;
- customer commitments with a required assigned worker and inclusive trip-date overlap.

It returns immutable impacts, stable reason codes, evidence keys, ordered path elements, and
unexecuted action proposals. Domain ordering is fixed as people, teams, systems, documents,
training, and customer commitments.

### Input fingerprint

The canonical fingerprint includes:

- analyzer version and complete typed policy input;
- workers and managers;
- worker-team memberships and teams;
- trips;
- courses and completion records;
- systems, documents, and all typed policy dependencies;
- customer commitments and assignments;
- unresolved questions.

Every source collection is sorted by stable semantic identifier before canonical JSON encoding.
Database row order does not affect the fingerprint; a relevant field change does.

### Response serializer

The serializer reads only the persisted assessment snapshot. It:

- sorts worker results, findings, evidence, impacts, actions, and questions by semantic keys;
- preserves persisted path sequence;
- groups impacts into six explicit domain collections;
- calculates summary counts from the returned persisted records;
- links action identifiers to their enterprise impacts;
- always serializes action execution as `not_executed`.

It does not query mutable source tables.

## Request and persistence flow

```mermaid
sequenceDiagram
    participant Client
    participant API as FastAPI route
    participant Service as Assessment service
    participant DB as PostgreSQL
    participant Worker as Worker analyzer
    participant Enterprise as Enterprise analyzer

    Client->>API: POST policy change assessment
    API->>Service: create_impact_assessment(policy_change_id)
    Service->>DB: Load all policy and enterprise context
    DB-->>Service: Typed source records
    Service->>Worker: Analyze workers and trips
    Worker-->>Service: Worker results, findings, actions
    Service->>Enterprise: Analyze explicit relationships
    Enterprise-->>Service: Impacts, paths, actions
    Service->>Service: Canonical fingerprint
    Service->>DB: Insert complete immutable aggregate
    DB-->>Service: Commit
    Service->>DB: Reload persisted aggregate
    DB-->>Service: Snapshot
    Service-->>API: Persisted assessment
    API-->>Client: 201 Created and Location
```

Retrieval loads the aggregate with `selectinload` and serializes it with the same stable ordering.
There are no assessment update or delete endpoints.

## Persistence model

### Source data

Milestone 0 source tables remain:

- `organizations`
- `workers`
- `trips`
- `training_records`
- `policy_changes`
- `policy_change_questions`

Milestone 1 adds:

- `teams`
- `worker_team_memberships`
- `enterprise_systems`
- `enterprise_documents`
- `training_courses`
- `customer_commitments`
- `commitment_assignments`
- `policy_system_dependencies`
- `policy_document_dependencies`
- `policy_training_dependencies`

Managers use stable worker records referenced by `workers.manager_worker_id`. A narrow membership
table gives each demonstration worker one current team. Separate dependency tables preserve real
foreign keys to systems, documents, and courses; there is no polymorphic graph target.

`training_records.course_identifier` now references `training_courses.id`.

### Immutable assessment aggregate

The Milestone 0 snapshot tables remain:

- `impact_assessments`
- `assessment_worker_results`
- `findings`
- `evidence`
- `finding_evidence`
- `proposed_actions`
- `assessment_unresolved_questions`

Milestone 1 adds:

- `assessment_enterprise_impacts`
- `assessment_impact_evidence`
- `assessment_impact_path_elements`

Enterprise impacts store domain, object type, stable source key, display name, classification,
explanation, reason code, and sort key in relational columns. Evidence remains a narrowly scoped
JSONB source snapshot linked through join tables. Relationship paths are ordered rows containing
object type, stable key, display label, and relationship to the next element.

`proposed_actions` may reference a finding, an enterprise impact, or both. A database check requires
at least one parent, and the existing `execution_status = 'not_executed'` constraint remains.

Assessment immutability is an application invariant:

- each analysis creates a new aggregate;
- source changes never update prior snapshots;
- the API exposes no assessment mutation;
- all aggregate rows commit atomically.

## Seeded demonstration

The idempotent seed contains:

- six travelers and six manager worker records;
- four teams and six memberships;
- three systems, one unaffected;
- four documents, one unaffected;
- one explicit International Travel Security course;
- six completion records;
- typed policy dependencies for two systems, three documents, and the course;
- two customer commitments and assignments, one affected by date overlap.

The completed golden assessment returns:

- three affected and three unaffected traveler results;
- six Milestone 0 findings;
- 18 enterprise impacts across all six domains;
- 13 proposed actions, all unexecuted;
- eight copied unresolved questions.

## External dependencies and boundaries

The running application communicates only with PostgreSQL.

There are no:

- LLM, LangChain, LangGraph, prompt, agent, embedding, or vector-search dependencies;
- MCP or live enterprise integrations;
- graph databases;
- background workers or message queues;
- approval workflows or action execution;
- frontend, authentication, or authorization components.

## Technology stack

### Runtime

- Python 3.12
- FastAPI 0.141.1
- Uvicorn 0.52.0
- Pydantic Settings 2.14.2
- SQLAlchemy 2.0.51
- Psycopg 3.3.4
- Alembic 1.18.5
- PostgreSQL 17
- Docker Compose

### Development and testing

- pytest 9.1.1
- httpx2 2.9.1 through FastAPI `TestClient`
- Ruff 0.16.1
- a dedicated PostgreSQL `changeops_test` database created and removed by the integration fixture
