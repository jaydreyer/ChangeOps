Milestone 1 — Enterprise Impact Discovery

Status

Planned

Purpose

Milestone 1 expands ChangeOps from a worker-and-trip policy assessment into a deterministic enterprise impact discovery capability.

Milestone 0 proved that ChangeOps can:

* load a structured policy change;
* evaluate it against seeded enterprise data;
* produce deterministic findings and proposed actions;
* preserve supporting evidence;
* persist an immutable assessment snapshot;
* return a stable API response.

Milestone 1 extends that foundation so a policy change can be traced beyond directly affected workers to the enterprise resources and obligations connected to them.

The milestone answers a broader product question:

What people, systems, documentation, training requirements, and customer commitments are affected by this change, and what evidence supports each conclusion?

Milestone 1 remains deterministic. It does not introduce an LLM, LangGraph, MCP, or external enterprise integrations.

AI-assisted interpretation and planning begin in Milestone 2.

⸻

Product Outcome

At the end of Milestone 1, a user can run the existing international-travel policy scenario and receive a categorized enterprise impact assessment covering:

* people;
* organizational teams;
* business systems;
* knowledge and policy documentation;
* training requirements;
* customer commitments.

Each reported impact must include:

* a stable impact type;
* the affected enterprise object;
* an explanation;
* one or more deterministic reason codes;
* supporting evidence;
* the relationship path connecting the policy change to the affected object;
* a proposed action when action is appropriate.

The result should demonstrate that ChangeOps understands not only who is affected, but how a change propagates through an enterprise.

⸻

Milestone Narrative

The demonstration scenario remains the updated international-travel policy.

The policy introduces requirements such as:

* manager approval for international travel;
* completion of security-awareness training;
* additional approval for designated destinations;
* an effective date controlling which trips are subject to the change.

Milestone 0 identifies affected workers and trips.

Milestone 1 follows those findings into related enterprise domains.

For example:

International travel policy
    ↓
Employee with planned travel
    ↓
Manager and organizational team
    ↓
Travel-request system
    ↓
Security-awareness training
    ↓
Travel knowledge articles
    ↓
Customer commitment affected by the employee's travel

The dependency path must be derived from persisted relationships and explicit deterministic rules. It must not be inferred by an LLM.

⸻

Goals

1. Expand the enterprise domain model

Represent the minimum additional enterprise entities needed to demonstrate cross-domain change impact.

2. Discover impacts across multiple domains

Extend the analyzer so one assessment can identify affected people, systems, documents, training, and customer commitments.

3. Preserve explainability

Every impact must show why it was included and which persisted relationships support it.

4. Preserve reproducibility

The same source data and analyzer version must continue to produce the same semantic result.

5. Preserve assessment immutability

New impact records must become part of the persisted assessment snapshot. Changes to source data after assessment creation must not alter earlier assessments.

6. Prepare a clean boundary for Milestone 2

Milestone 1 should expose deterministic enterprise context that later AI workflows can consume without querying raw database tables directly.

⸻

Non-Goals

Milestone 1 will not include:

* LLM calls;
* LangChain;
* LangGraph;
* agents;
* prompt management;
* vector search or embeddings;
* semantic retrieval;
* MCP servers or clients;
* live Workday, Salesforce, Jira, or knowledge-system integrations;
* human approval workflows;
* action execution;
* authentication or authorization;
* a production web interface;
* notifications;
* background jobs;
* message queues;
* generalized graph-database infrastructure;
* a generic rules-engine platform;
* user-created policies or dependency mappings.

The milestone must not become a general enterprise configuration-management database.

Only model the relationships required by the current demonstration scenario.

⸻

Scope

Enterprise Domains

Milestone 1 adds deterministic impact discovery for the following domains.

People

Existing workers remain the primary directly affected objects.

Milestone 1 adds organizational context sufficient to report:

* the affected worker;
* the worker’s manager;
* the worker’s team.

A manager or team is affected because one or more connected workers require review, approval, training, communication, or operational support.

Systems

Represent business systems involved in the travel-policy workflow.

The seeded scenario should include a small number of fictional systems, such as:

* a travel-request system;
* a learning-management system;
* an HR worker-record system.

System impact should be based on explicit relationships between:

* a policy rule or resulting action;
* an enterprise process;
* the system supporting that process.

Milestone 1 does not simulate those systems or call their APIs.

Documentation

Represent the small set of knowledge or policy documents that require review when the policy changes.

Examples may include:

* the primary international-travel policy;
* a travel-booking knowledge article;
* a manager approval guide;
* a security-training FAQ.

Document impact must be based on explicit applicability or dependency records, not text similarity.

Training

Represent the training course associated with the current security-training rule.

The assessment should identify:

* which course is affected;
* which workers have completed it;
* which affected workers require completion or verification;
* why the course is relevant to the policy change.

Existing worker training records should remain the authoritative completion source.

Customer Commitments

Represent a narrowly scoped fictional customer commitment that may be affected by planned employee travel.

Examples include:

* a scheduled customer implementation;
* an on-site delivery commitment;
* a contractual coverage obligation.

A customer commitment is affected only when a deterministic relationship connects it to:

* an affected worker;
* an affected trip;
* an overlapping date range;
* or a required employee role.

This domain is included to demonstrate that operational changes can propagate beyond internal HR processes.

It must remain intentionally small.

⸻

Proposed Source Data Model

The final schema may vary, but the implementation should support the following concepts.

Teams

Represents an organizational team.

Minimum fields:

* stable identifier;
* organization identifier;
* name;
* manager worker identifier.

Workers should reference a team.

Enterprise Systems

Represents a fictional business system.

Minimum fields:

* stable identifier;
* organization identifier;
* name;
* system type;
* description;
* active status.

Documents

Represents a policy, procedure, guide, or knowledge article.

Minimum fields:

* stable identifier;
* organization identifier;
* title;
* document type;
* source-system label;
* version;
* status.

The milestone does not require storing or parsing full document bodies.

Training Courses

Represents an enterprise training requirement.

Minimum fields:

* stable identifier;
* organization identifier;
* course code;
* name;
* active status.

Existing training records should reference a course rather than relying only on an unstructured course name.

Customer Commitments

Represents a fictional obligation associated with a customer.

Minimum fields:

* stable identifier;
* organization identifier;
* customer name;
* commitment type;
* description;
* start date;
* end date;
* status.

Commitment Assignments

Connects workers or roles to customer commitments.

Minimum fields:

* customer commitment identifier;
* worker identifier;
* assignment role;
* required status.

Policy Dependencies

Represents explicit relationships between a policy change or policy rule and another enterprise object.

A dependency should identify:

* policy change or rule identifier;
* target domain;
* target object identifier;
* relationship type;
* explanation or source note.

The implementation may use typed relational tables instead of one polymorphic dependency table if that produces stronger integrity and simpler queries.

Do not introduce a graph database.

PostgreSQL relationships are sufficient for the current scenario.

⸻

Assessment Snapshot Model

Milestone 1 must persist discovered impacts as part of the immutable assessment aggregate.

A suitable model is a categorized impact record containing:

* assessment identifier;
* impact domain;
* impact object type;
* source object identifier;
* stable source key;
* display name;
* impact classification;
* explanation;
* deterministic reason code;
* proposed action type, when applicable;
* stable sort key.

Supporting evidence and dependency paths must also be persisted.

The exact relational design is an implementation decision, but it must preserve:

* referential clarity;
* deterministic serialization;
* immutable historical results;
* straightforward querying;
* explainable links between findings and impacts.

Avoid storing the complete Milestone 1 response as one opaque JSON document.

JSONB may be used for narrowly scoped evidence snapshots or structured metadata, but important domain relationships should remain queryable.

⸻

Impact Domains and Classifications

The public API should use explicit, stable domain values.

Suggested domains:

people
teams
systems
documents
training
customer_commitments

Suggested classifications:

directly_affected
operationally_affected
review_required
update_required
notification_required
unaffected

Not every domain must use every classification.

The implementation should define the valid combinations in deterministic code rather than allow arbitrary strings.

⸻

Deterministic Discovery Rules

The rules below define the intended behavior for the seeded demonstration scenario. Exact names may be adjusted to align with the current codebase.

People

A worker is directly affected when an existing Milestone 0 rule produces an affected classification for the worker’s trip.

A manager is operationally affected when a connected worker requires manager approval or exception review.

Teams

A team is operationally affected when at least one worker on the team is directly affected.

The team impact should summarize the number of affected workers without replacing the individual worker findings.

Systems

The travel-request system is affected when the policy introduces or changes approval handling for an assessed trip.

The learning-management system is affected when training completion must be verified or assigned.

The HR worker-record system is affected only when the scenario includes an action requiring worker attributes or eligibility data to be reviewed or maintained.

Do not mark every seeded system as affected merely because it exists.

Documents

A document is affected when an explicit policy dependency identifies that document as:

* containing the changed policy;
* explaining a changed process;
* instructing a manager or worker about a changed requirement;
* or referencing a superseded requirement.

The resulting impact should state whether the document requires review or update.

Training

The security-awareness course is affected when the changed policy contains a training requirement tied to that course.

A worker-specific training impact exists when an affected worker lacks a valid completion record.

The course-level impact and worker-level finding should remain distinct.

Customer Commitments

A customer commitment is affected when:

1. an assigned worker is directly affected;
2. the connected trip or policy requirement overlaps the commitment period; and
3. the policy finding could reasonably delay, block, or require review of the worker’s participation.

The analyzer must record the exact deterministic conditions that produced the impact.

No customer-risk score or speculative business impact should be generated in Milestone 1.

⸻

Relationship Paths

Every non-worker impact must include a relationship path explaining how the analyzer reached it.

Example:

policy_change:international-travel-2026
→ rule:security-training-required
→ worker:worker-1042
→ training_course:security-awareness

Another example:

policy_change:international-travel-2026
→ trip:trip-2041
→ worker:worker-1042
→ customer_commitment:commitment-3001

Paths must use stable semantic identifiers.

They should be stored as ordered path elements, not only rendered as prose.

A path element should contain at least:

* object type;
* stable object key;
* display label;
* relationship to the next element when applicable.

The API serializer must return path elements in their persisted order.

⸻

API Changes

The existing create-and-retrieve assessment endpoints should remain the primary interface:

POST /api/v1/policy-changes/{policy_change_id}/impact-assessments
GET /api/v1/impact-assessments/{assessment_id}

Avoid adding a second assessment workflow unless the current endpoint cannot be evolved without breaking its meaning.

The assessment response should add an enterprise-impact section while preserving existing worker results, findings, evidence, proposed actions, and unresolved questions.

A representative response shape is:

{
  "id": "assessment-id",
  "policy_change_id": "policy-change-id",
  "status": "completed",
  "analyzer_version": "2.0.0",
  "input_fingerprint": "sha256-value",
  "summary": {
    "workers_assessed": 4,
    "workers_affected": 3,
    "enterprise_impacts": 11,
    "impacts_by_domain": {
      "people": 3,
      "teams": 2,
      "systems": 2,
      "documents": 2,
      "training": 1,
      "customer_commitments": 1
    }
  },
  "worker_results": [],
  "findings": [],
  "enterprise_impacts": {
    "people": [],
    "teams": [],
    "systems": [],
    "documents": [],
    "training": [],
    "customer_commitments": []
  },
  "proposed_actions": [],
  "unresolved_questions": []
}

This is illustrative rather than a binding schema.

The final API design should prioritize:

* backward clarity;
* stable ordering;
* explicit types;
* useful evidence;
* minimal duplication.

⸻

Analyzer Architecture

The current pure deterministic analyzer should remain independent from FastAPI, SQLAlchemy, and external I/O.

Milestone 1 may split analysis into deterministic domain modules, for example:

analysis/
    worker_impact.py
    team_impact.py
    system_impact.py
    document_impact.py
    training_impact.py
    customer_commitment_impact.py

An application-level coordinator may invoke these modules in a fixed order.

Do not introduce LangGraph merely to coordinate deterministic Python functions.

A normal application service or domain coordinator is sufficient.

Each domain analyzer should:

* accept immutable typed input;
* return immutable typed results;
* avoid database access;
* avoid HTTP access;
* avoid global mutable state;
* use stable reason codes;
* be independently testable.

⸻

Input Fingerprinting

The assessment input fingerprint must expand to include all source data that can influence enterprise impact discovery.

This includes, as applicable:

* workers;
* managers and teams;
* trips;
* training records and courses;
* policy rules;
* policy dependencies;
* enterprise systems;
* documents;
* customer commitments;
* commitment assignments;
* unresolved seeded questions.

Canonicalization must preserve semantic stability and exclude irrelevant database details such as row insertion order.

Changing an impact-producing source record must change the fingerprint.

Reordering equivalent source records must not change it.

⸻

Seed Scenario Changes

Extend the existing idempotent seed process with stable fictional records.

The scenario should contain enough data to prove both positive and negative behavior.

At minimum, seed:

* two teams;
* managers connected to affected workers;
* three enterprise systems, with at least one remaining unaffected;
* three or four documents, with at least one remaining unaffected;
* one security-awareness training course;
* worker training records that include both completed and incomplete cases;
* two customer commitments, with only one affected;
* explicit policy dependencies connecting the travel policy to selected systems, documents, and training;
* commitment assignments connecting selected workers to customer commitments.

Repeated seed execution must remain idempotent.

Do not add dozens of records for visual scale. The dataset should remain small enough that a reviewer can understand every assessment result.

⸻

Proposed Actions

Milestone 1 may add deterministic proposed-action types such as:

request_manager_approval
assign_training
verify_training_completion
review_team_travel
review_system_workflow
update_document
notify_document_owner
review_customer_commitment

Actions remain proposals only.

Every action must continue to use:

execution_status = not_executed

No action may call an external or simulated enterprise system in this milestone.

Action execution and approval are deferred to later milestones.

⸻

Reason Codes

Every deterministic conclusion must use a stable reason code.

Examples:

WORKER_MANAGER_APPROVAL_REQUIRED
TEAM_HAS_AFFECTED_WORKERS
SYSTEM_SUPPORTS_CHANGED_APPROVAL_PROCESS
DOCUMENT_REFERENCES_CHANGED_POLICY
TRAINING_REQUIRED_BY_POLICY
WORKER_TRAINING_INCOMPLETE
CUSTOMER_COMMITMENT_OVERLAPS_AFFECTED_TRAVEL

Reason codes are part of the explainability contract.

They should not be generated dynamically or derived from display text.

⸻

Implementation Plan

Phase 1 — Domain design

* Review the current Milestone 0 schema and assessment aggregate.
* Define the minimum new source entities.
* Define enterprise impact domain types and classifications.
* Define relationship-path representation.
* Record material architecture decisions in docs/decisions.md.
* Create an Alembic migration plan.

Phase 2 — Persistence and seed data

* Add new source tables and relationships.
* Add assessment-snapshot tables for enterprise impacts and paths.
* Extend ORM relationships and loading strategies.
* Extend the idempotent seed process.
* Add persistence and seed tests.

Phase 3 — Deterministic analyzers

* Add immutable domain input and output types.
* Implement team-impact discovery.
* Implement system-impact discovery.
* Implement document-impact discovery.
* Implement training-impact discovery.
* Implement customer-commitment-impact discovery.
* Add stable reason codes and action types.
* Add unit tests for each domain.

Phase 4 — Assessment integration

* Extend the assessment application service.
* Expand input fingerprinting.
* Persist the complete impact aggregate in one transaction.
* Preserve rollback behavior.
* Extend eager loading for assessment retrieval.
* Verify historical assessment immutability.

Phase 5 — API and serialization

* Extend Pydantic response schemas.
* Add categorized enterprise impacts.
* Add impact summaries.
* Add relationship paths.
* Preserve stable semantic ordering.
* Add API integration tests.

Phase 6 — Documentation and demonstration

* Update docs/architecture.md.
* Update docs/roadmap.md if necessary.
* Update docs/demo-scenario.md only where the demonstrated outputs have changed.
* Update docs/decisions.md.
* Update the README with the Milestone 1 capability.
* Add example requests and representative responses.
* Document the boundary between deterministic Milestone 1 behavior and AI-enabled Milestone 2 behavior.

⸻

Testing Requirements

Unit tests

Unit tests must cover:

* each impact-domain rule;
* positive and negative impact cases;
* stable reason codes;
* relationship-path construction;
* action generation;
* date-overlap behavior;
* duplicate-impact prevention;
* stable ordering;
* fingerprint canonicalization.

Integration tests

Integration tests must verify:

* migrations apply to an empty database;
* seed execution is idempotent;
* assessment creation includes all expected impact domains;
* unaffected objects are not incorrectly reported;
* the complete aggregate is committed atomically;
* failed creation leaves no partial assessment;
* assessment retrieval reproduces the created snapshot;
* source-data changes do not mutate an existing assessment;
* a later assessment reflects relevant source-data changes;
* semantically identical inputs produce the same fingerprint;
* relevant input changes produce a different fingerprint.

API contract tests

Contract tests must verify:

* existing endpoints remain available;
* response models reject invalid domain and classification values;
* enterprise impact collections use stable ordering;
* relationship paths preserve order;
* summary counts match returned records;
* proposed actions remain unexecuted.

⸻

Acceptance Scenario

The seeded international-travel policy assessment should produce a result demonstrating all of the following:

1. At least one worker is directly affected.
2. At least one worker is unaffected.
3. At least one manager is operationally affected.
4. At least one team is affected because it contains an affected worker.
5. At least one seeded team remains unaffected.
6. The travel-request system is identified because approval behavior changes.
7. The learning-management system is identified because training verification or assignment is required.
8. At least one seeded system remains unaffected.
9. At least one travel-related document requires review or update.
10. At least one seeded document remains unaffected.
11. The security-awareness course is connected to the policy requirement.
12. At least one affected worker lacks valid training completion.
13. At least one affected worker already satisfies the training requirement.
14. One customer commitment is identified through an affected worker and overlapping dates.
15. At least one customer commitment remains unaffected.
16. Every non-worker impact includes an ordered relationship path.
17. Every impact contains evidence and a stable reason code.
18. Every proposed action remains unexecuted.
19. Re-running the assessment with unchanged inputs produces an equivalent semantic result.
20. Earlier assessments remain unchanged when source data is later modified.

⸻

Definition of Done

Milestone 1 is complete when:

* the enterprise domain model supports the scoped demonstration scenario;
* impact discovery covers people, teams, systems, documents, training, and customer commitments;
* all discovery logic is deterministic;
* each impact includes evidence, reason codes, and a relationship path;
* the assessment remains an immutable persisted snapshot;
* input fingerprinting includes all impact-producing data;
* existing Milestone 0 behavior remains supported;
* seed data remains stable and idempotent;
* unit, integration, and API contract tests pass;
* the API returns categorized enterprise impacts using stable ordering;
* no LLM, LangGraph, MCP, or external-system integration is present;
* architecture and roadmap documentation reflect the completed implementation;
* a reviewer can understand why every seeded object was classified as affected or unaffected.

⸻

Milestone Exit Demonstration

A successful Milestone 1 demo should take only a few minutes.

1. Start the Docker Compose environment.
2. Apply migrations and run the seed job.
3. Create an assessment for the seeded international-travel policy.
4. Show the affected and unaffected workers.
5. Show the categorized enterprise impacts.
6. Open one system, document, training, and customer-commitment impact.
7. Trace each impact through its relationship path.
8. Show its evidence, reason code, and proposed action.
9. Retrieve the persisted assessment again.
10. Demonstrate stable output and immutable history.

The demo should end with the architectural boundary for the next milestone:

Milestone 1 deterministically discovers what is affected. Milestone 2 introduces AI to interpret unstructured policy changes, coordinate evidence-backed analysis, and propose a change plan.

⸻

Portfolio Signal

Milestone 1 demonstrates:

* disciplined domain modeling;
* deterministic rule design;
* cross-domain enterprise reasoning;
* explainable impact analysis;
* immutable audit-oriented persistence;
* stable API design;
* transaction integrity;
* thoughtful separation between deterministic software and AI;
* restraint in technology selection.

The milestone is intentionally not an AI milestone.

Its purpose is to establish the trusted enterprise context that later AI behavior will consume.