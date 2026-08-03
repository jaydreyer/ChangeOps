# ChangeOps Feature-Expansion Roadmap Before AWS

## Executive recommendation

Build **three product slices** before AWS:

1. **Policy-version comparison**
2. **Change-plan revision lineage**
3. **Unified audit timeline**

Treat a Jira-style execution action as **optional** and probably defer it until after the first AWS deployment.

Do **not** add MCP before AWS.

Do **not** build an evaluation dashboard before AWS unless it can be delivered as a very small read-only page during audit-timeline work.

This produces the strongest capstone story:

> ChangeOps detects what materially changed between policy versions, calculates how enterprise impact changed, allows humans to govern AI-generated planning through immutable revisions, and exposes the complete decision and execution lineage.

That is a more differentiated and coherent product than:

> ChangeOps can call two simulated enterprise systems.

The repository has already demonstrated the difficult execution properties—approval lineage, immutable commands, deterministic routing, explicit invocation, durable side effects, idempotency, and replay history—with the Learning System. A second adapter adds less new value than it appears.

---

# 1. Current product and architecture

## Current product

ChangeOps now has a complete local golden journey:

```text
Stored policy
    ↓
AI-assisted typed extraction
    ↓
Deterministic validation and identifier resolution
    ↓
Bounded human clarification
    ↓
Deterministic immutable assessment
    ↓
Cross-domain enterprise impact discovery
    ↓
Grounded AI interpretation
    ↓
Immutable change plan
    ↓
Item-level human review
    ↓
Approval workflow
    ↓
Immutable execution-command preparation
    ↓
Explicit execution
    ↓
Durable simulated Learning System state
    ↓
Immutable execution results and replay history
```

The reviewer journey begins with the seeded policy rather than a precompleted assessment. The README documents expected outputs of three affected workers, three cleared workers, six findings, eighteen enterprise impacts, thirteen proposed actions, and two supported training commands in the golden journey.

The product now cleanly distinguishes:

- AI proposals from authoritative facts;
- policy analysis from approval;
- approval from command preparation;
- command preparation from execution;
- execution authorization from external system state;
- the original execution result from replay history.

That separation is one of the strongest parts of the project.

## Runtime architecture

The implementation is a **synchronous modular monolith**, which remains the correct architecture.

FastAPI, application services, domain logic, LangChain, LangGraph orchestration, SQLAlchemy persistence, and simulated execution all run in one backend process. PostgreSQL is the durable system of record. Next.js provides product-facing read models and workflow controls. The configured model provider is the only current external dependency. 

The local environment contains:

- PostgreSQL 17
- a migration job
- an idempotent seed job
- the FastAPI application
- the Next.js application

Compose health checks and dependency ordering ensure that migrations and seeding complete before the application starts. 

## Architectural strengths

### PostgreSQL is authoritative

Both LangGraph workflows are intentionally compiled without checkpointers. Resume starts a fresh graph invocation and derives its route from persisted application state.

That is a good, defensible decision. It prevents LangGraph checkpoints from competing with the relational domain model as the source of truth.

### Domain boundaries are unusually disciplined

The architecture explicitly keeps business logic independent from FastAPI, SQLAlchemy, LangChain, LangGraph, and external APIs. The repository standards reinforce the modular-monolith boundary and prohibit premature microservices and framework-driven domain logic. 

### AI ownership is properly constrained

The repository has a strong architectural rule:

> AI owns language in and interpretation out, and nothing authoritative in between.

The extractor cannot see worker or enterprise outcome data. The interpreter receives the persisted assessment rather than directly querying enterprise source tables. Deterministic code owns validation, impact classification, identifiers, evidence ownership, routing, approvals, and execution.

This is one of the clearest interview stories in the repository. 

### Historical artifacts have distinct meanings

The repository correctly separates:

- policy source records;
- extraction attempts;
- validated rules;
- assessments;
- change plans;
- proposed actions;
- action reviews;
- decisions;
- approval runs;
- execution commands;
- simulated enterprise state;
- execution results.

The distinction between an immutable authorization command and mutable external-system state is particularly strong.

### CI is credible and honest

The ordinary CI suite is provider-free and protects deterministic contracts, PostgreSQL integration behavior, migrations, schemas, workflow routing, grounding, and approval behavior.

The repository correctly states that green fixture evaluations are regression evidence, not a live model-quality benchmark. That honesty improves the project.

The manually dispatched live-provider smoke has the right role: compatibility and canonical-path verification, not a required merge gate.

## Current weaknesses

### The product analyzes a policy, not yet a change

Despite the name ChangeOps, the primary user operation is still effectively:

> Analyze this policy.

The product vision is closer to:

> Tell me what changed, why it matters, and what must now be done differently.

The current implementation does not yet model a baseline policy and a proposed revision as first-class related inputs.

This is the largest product gap.

### Revision governance is incomplete

The action-review flow supports a `revision_requested` terminal decision, but there is no actual revision lifecycle that produces a new plan version.

Today, “request revision” records intent but does not complete the governance loop.

That makes it a status rather than a product capability.

### Lineage exists but is fragmented

The data required for a compelling audit story is mostly present, but users must understand separate journey and workbench projections.

There is no single answer to:

> Show me everything that happened, in order, who or what performed it, what artifact was created, and what happened next.

### The current local authorization boundary blocks public deployment

Trusted actor and role headers are appropriate for a local demo, but they cannot survive an internet-facing deployment.

This is an AWS-phase concern, not a reason to build production RBAC now.

### Documentation milestone language is now awkward

The README still labels the current milestone “Milestone 5,” while the roadmap describes AWS, authentication, observability, and production operation as part of Milestone 5.

That creates semantic confusion between:

- local product completion;
- feature expansion;
- cloud production readiness.

Before the next implementation PR, introduce a clearly named **Feature Expansion Phase** or **Milestone 5A**, with AWS as **Milestone 5B** or Milestone 6.

Do not silently reinterpret the existing milestone.

---

# 2. Largest remaining product gaps

## Gap 1 — No actual before-and-after change model

This is the most important gap.

The current system can explain why a policy affects workers and enterprise objects, but it cannot answer:

- What changed from the current policy?
- Which requirements are new?
- Which requirements were removed?
- Which workers became affected?
- Which workers are no longer affected?
- Which enterprise impacts are new or cleared?
- Is this merely editorial wording or an operationally material change?

That capability would transform ChangeOps from a governed policy analyzer into a genuine change-management product.

## Gap 2 — Human revision intent has no fulfillment path

A reviewer can request revision, but the AI-generated plan is not regenerated through a governed lineage.

The product needs:

```text
Plan v1
    ↓
Human revision request
    ↓
Plan generation attempt
    ↓
Deterministic grounding validation
    ↓
Plan v2
    ↓
Selection and approval
```

The important story is not “the human edits AI output.”

It is:

> The human provides structured revision intent, the system creates a new immutable AI artifact, deterministic validation rechecks it, and the historical version remains intact.

## Gap 3 — No unified audit projection

The system has auditability at the storage level, but product-level audit comprehension still requires source-code or schema knowledge.

A portfolio reviewer should be able to inspect a single ordered timeline.

## Gap 4 — Public deployment boundary is not yet designed

The application is currently locally coherent but has not yet established:

- hosted authentication;
- trusted actor derivation;
- deployed database operations;
- secret management;
- structured request correlation;
- deployment topology;
- migration execution strategy;
- public-demo reset or tenancy constraints.

This should be solved during AWS design, not preemptively with generic platform infrastructure.

---

# 3. Candidate ranking

## 1. Policy-version comparison — Definitely build

### Product value: Very high

This is the feature that best fulfills the product name and vision.

It changes the central user question from:

> What does this policy affect?

to:

> What changed, and what operational consequences changed because of it?

### New engineering capability

It demonstrates:

- version lineage;
- deterministic semantic diffing;
- before-and-after impact calculation;
- materiality classification;
- dual-source provenance;
- added, removed, and changed impact sets.

### Portfolio value

Very high. It creates a distinctive product story rather than another generic AI workflow.

### Complexity

Moderate to high, but manageable if sliced correctly.

### Important scope correction

Do not begin by building a generalized semantic policy-diff engine.

The first version should support only the existing validated `international_travel` schema and compare canonical typed rule fields.

Do not ask an LLM to directly decide whether a change is operationally material when the typed rule difference already answers that question.

AI should explain the validated diff afterward.

---

## 2. Human-requested change-plan revision — Definitely build

### Product value: High

This closes an existing product loop rather than introducing a separate feature family.

### New governance capability

It demonstrates:

- immutable AI artifact versioning;
- human-directed AI iteration;
- supersession lineage;
- re-grounding of regenerated output;
- approval against a selected effective version.

### Portfolio value

Very high. This is a stronger human-in-the-loop story than simple approve/reject controls.

### Complexity

Moderate if the existing change-plan schema is reused.

### Scope correction

Do not permit arbitrary direct editing of the plan.

Do not create branching document collaboration.

Support one active revision chain:

```text
v1 → revision request → v2
```

A second revision can be allowed through the same model, but the UI does not need a generic tree or merge system.

---

## 3. Audit timeline — Definitely build

### Product value: High

It lets reviewers understand the full product in one view.

### New engineering capability

It demonstrates:

- read-model composition;
- stable event ordering;
- authoritative artifact references;
- actor classification;
- lifecycle explainability;
- audit projection without event sourcing.

### Portfolio value

High, especially for enterprise architecture interviews.

### Complexity

Low to moderate because the underlying records already exist.

### Scope correction

Do not introduce a new append-only generic `audit_events` table for every operation.

Build a projection over authoritative records.

Add explicit persisted records only where a genuine audit fact currently does not exist.

---

## 4. Second Jira-style execution pattern — Optional

### Product value: Moderate

Creating an issue is meaningfully different from assigning an existing course.

It introduces:

- generated external work-item content;
- destination project selection;
- external issue identity;
- create semantics;
- different idempotency ownership.

### Portfolio value: Moderate

It demonstrates that the command abstraction is not accidentally coupled to training assignments.

However, the existing execution architecture already proves most important governance properties.

### Recommendation

Defer it unless either of these becomes true:

1. Policy comparison generates a compelling operational-remediation action that naturally requires issue creation.
2. Repository refactoring reveals that the execution-command contract is secretly Learning-specific and needs validation against a second semantic.

Do not build Jira merely to claim two integrations.

---

## 5. Evaluation evidence view — Optional and small

### Product value: Low to moderate

Most end users do not need this page.

It is useful for reviewers, engineers, and interviewers.

### Portfolio value: Moderate

It demonstrates mature AI quality thinking, but the repository already documents its evaluation boundaries unusually well.

### Recommendation

Do not build a generic evaluation UI.

At most, add a small `/quality` page after the audit timeline, sourced from a committed versioned manifest or build metadata.

Do not have the production application parse CI logs or query GitHub Actions.

A viable minimal page could show:

- evaluation categories;
- dataset versions;
- prompt/schema versions;
- what each check proves;
- what it does not prove;
- latest manually recorded live-smoke metadata.

---

## 6. MCP — Remove from the pre-AWS roadmap

### Product value: None by itself

MCP is a protocol choice, not a user capability.

### Current architectural need

The current in-process adapter has several advantages:

- atomic transaction with simulated enterprise state;
- easy PostgreSQL-backed idempotency;
- no network failure modes;
- no distributed authorization context;
- no deployment complexity;
- straightforward testing.

Moving the Learning System behind MCP would reduce reliability and add no new user value.

### Recommendation

Do not add MCP before AWS.

A second action type alone is not sufficient justification.

---

# 4. Features that should definitely be built before AWS

## Required

### A. Policy-version comparison

This should be the major differentiating feature.

### B. Change-plan revision lineage

This should close the existing `revision_requested` governance loop.

### C. Unified audit timeline

This should make all existing architecture understandable through the product.

## Required preparation for AWS

Before cloud implementation begins:

- stabilize API contracts introduced by these features;
- reconcile milestone documentation;
- document the deployment trust boundary;
- decide how authenticated identity replaces demonstration headers;
- define whether demo data is shared, resettable, or per-session;
- document which operations are unavailable in the public demo.

These are design outputs, not new platform frameworks.

---

# 5. Features that should be optional or removed

## Optional: Jira execution

Build only when it naturally follows from the comparison feature or exposes a real defect in the generic command model.

## Optional: Small quality evidence page

Build only if it remains a narrow static/read-only projection.

## Removed before AWS: MCP

No current problem requires it.

## Removed: Additional policy families

A second shallow policy type would add breadth but weaken the story.

The existing domain should first demonstrate change-over-time, governance, and auditability.

## Removed: Generic policy comparison framework

Implement comparison for one closed typed schema.

Do not introduce a DSL, configurable rules engine, generic object-diff framework, or ontology.

---

# 6. Recommended sequencing

Your original ordering was:

1. policy comparison
2. plan revision
3. Jira execution
4. MCP
5. audit or evaluation
6. AWS

I recommend:

1. **Comparison foundation**
2. **Impact delta**
3. **Plan revision**
4. **Audit timeline**
5. **AWS architecture and Terraform**
6. Optional Jira after deployment or immediately before AWS only if comparison proves the need
7. MCP only after a real process boundary exists

The important change is moving audit ahead of a second adapter and removing MCP.

## Why audit precedes another adapter

A second adapter adds another branch at the end of the journey.

Audit improves every branch and every product stage.

It strengthens:

- policy comparison;
- extraction;
- clarification;
- impact assessment;
- interpretation;
- revision;
- approval;
- command preparation;
- execution;
- replay.

It also makes the AWS-deployed application much easier to demonstrate.

---

# 7. Revised roadmap from current `main` through AWS

## Phase 1 — Define policy lineage and deterministic rule comparison

### PR 25 — Policy revision relationship and validated rule diff

Deliver:

- explicit baseline/current-policy relationship;
- proposed-revision relationship;
- deterministic rule comparator;
- immutable comparison record;
- added, removed, and modified rule changes;
- dual policy provenance;
- read API;
- focused UI comparison view.

No impact delta yet.

This is the smallest credible precursor slice.

## Phase 2 — Compute impact delta

### PR 26 — Comparison assessment and enterprise impact delta

Deliver:

- run deterministic assessment for each accepted ruleset;
- compare immutable assessment outputs;
- classify newly affected, no-longer-affected, and unchanged entities;
- compare findings and enterprise impacts using semantic identity keys rather than database UUIDs;
- expose reason and evidence for each delta;
- add grounded AI interpretation of the deterministic delta only after the delta is complete.

This is where the product becomes recognizably ChangeOps.

## Phase 3 — Governed change-plan revision

### PR 27 — Revision request and immutable plan versioning

Deliver:

- immutable revision request;
- structured revision intent;
- plan-generation attempt linked to the prior plan;
- new immutable change plan version;
- grounding validation;
- `supersedes` lineage;
- read comparison between versions.

### PR 28 — Effective plan selection and approval integration

Deliver:

- deterministic effective-plan selection;
- approval-run creation tied to the selected plan lineage where appropriate;
- prevent approval ambiguity when a newer revision exists;
- UI controls for request revision, inspect versions, select effective plan, and continue to review.

Do not rebuild action review unless revised plans materially change the deterministic proposed actions. The likely design is that change-plan revision changes interpretation and recommendations, while deterministic assessment actions remain separately governed.

That boundary must be confirmed during PR 27 design.

## Phase 4 — Unified audit experience

### PR 29 — Read-only audit timeline

Deliver:

- ordered artifact-backed timeline;
- actor type: AI, deterministic system, human;
- actor identity where applicable;
- timestamp;
- artifact type and identifier;
- outcome;
- links to existing journey or workbench details;
- comparison and revision events included;
- stable deterministic ordering.

## Phase 5 — Optional execution validation

### PR 30 — Jira-style create issue, only if justified

This PR is conditional.

Skip it if no meaningful product need emerges.

If built, it must remain one operation:

```text
operational_remediation
    → jira.create_issue
```

No adapter registry. No generic tool platform. No MCP yet.

## Phase 6 — AWS architecture decision

### Architecture PR

Document and select:

- hosting topology;
- frontend/backend boundary;
- PostgreSQL hosting;
- authentication;
- secrets;
- migrations;
- logs and traces;
- demo-data lifecycle;
- cost envelope;
- public safety controls.

This PR should contain ADRs and diagrams, not speculative infrastructure code.

## Phase 7 — Terraform and deployment

Likely deployment slices:

1. foundational Terraform and network/database resources;
2. API deployment and migrations;
3. Next.js deployment and routing;
4. authentication and trusted identity propagation;
5. observability and deployment CI;
6. public demo hardening and reviewer walkthrough.

---

# 8. Next single vertical slice

## Recommended next slice

**Compare validated rules for a current policy and one proposed revision.**

Do not start with complete impact-delta analysis.

The current domain model needs a trustworthy policy-lineage and comparison aggregate first.

## User-visible outcome

A reviewer can choose:

- one current policy;
- one proposed revision;

and see:

- which validated obligations were added;
- which were removed;
- which were modified;
- both exact source references;
- whether each difference is operationally material under the supported schema.

## Why this is the right first slice

It answers a new product question while remaining bounded.

It validates the hardest domain assumptions before the system computes two assessments and compares enterprise effects.

It also avoids embedding comparison logic inside UI code or AI prompts.

---

# 9. Codex-ready implementation handoff

## Title

Implement deterministic policy-version comparison for validated international-travel rules

## Goal

Add the first vertical slice of policy-version comparison.

A user must be able to compare one current international-travel policy with one proposed revision after each has an accepted validated extraction.

The system must persist one immutable comparison artifact and expose a product-facing read view containing deterministic field-level semantic differences and provenance to both policy versions.

Do not implement enterprise impact delta, plan revision, Jira, MCP, AWS, or Terraform in this PR.

## Product behavior

Given:

- a baseline policy change;
- a proposed revision;
- one accepted extraction with resolved validated rules for each;

the system must produce an immutable comparison that identifies:

- added obligations;
- removed obligations;
- modified obligations;
- unchanged obligations where useful for context;
- operational materiality;
- exact provenance to each policy source.

Comparison must operate on validated typed rules, not raw text.

The AI must not decide the semantic diff or materiality.

## Supported scope

Only support:

```text
policy_family = international_travel
schema_version = 1
```

Both policies must:

- belong to the same organization;
- use the same supported policy family;
- have accepted extraction attempts;
- have fully resolved validated rules;
- have no pending clarification;
- be distinct policy records.

Unsupported family or schema combinations must fail closed with stable error codes.

## Data model

Introduce a narrow immutable comparison aggregate.

Suggested models:

### `PolicyComparison`

Fields:

- `id`
- `organization_id`
- `baseline_policy_change_id`
- `proposed_policy_change_id`
- `baseline_extraction_attempt_id`
- `proposed_extraction_attempt_id`
- `schema_version`
- `comparison_version`
- `comparison_fingerprint`
- `created_at`
- `created_by`

Constraints:

- baseline and proposed policies must differ;
- both policy records belong to the same organization;
- extraction attempts belong to their referenced policy;
- extraction attempts were accepted;
- comparison rows are immutable;
- unique semantic fingerprint prevents duplicate comparison artifacts.

### `PolicyRuleDifference`

Fields:

- `id`
- `policy_comparison_id`
- `sequence`
- `rule_key`
- `change_type`
- `materiality`
- `baseline_value_json`
- `proposed_value_json`
- `baseline_provenance_json`
- `proposed_provenance_json`
- `reason_code`

Closed values:

```text
change_type:
- added
- removed
- modified
- unchanged

materiality:
- operationally_material
- non_material
```

Do not create generic arbitrary path expressions if explicit supported rule keys are clearer.

## Domain design

Create a pure domain comparator, independent from FastAPI and SQLAlchemy.

Suggested input:

```python
@dataclass(frozen=True)
class PolicyRuleVersion:
    policy_change_id: str
    extraction_attempt_id: UUID
    rules: InternationalTravelPolicyRules
    provenance: InternationalTravelRuleProvenance
```

Suggested output:

```python
@dataclass(frozen=True)
class PolicyRuleDiff:
    rule_key: InternationalTravelRuleKey
    change_type: RuleChangeType
    materiality: RuleMateriality
    baseline_value: JsonValue | None
    proposed_value: JsonValue | None
    baseline_provenance: ProvenanceReference | None
    proposed_provenance: ProvenanceReference | None
    reason_code: str
```

Use an explicit comparator per supported semantic field.

Do not perform a generic recursive JSON diff.

## Rule identity

Define an explicit closed set of comparable semantics, for example:

- effective date;
- covered worker countries;
- covered employment types;
- international-travel applicability;
- required training course;
- manager approval requirement;
- nonrefundable booking restriction;
- pre-effective-date booking exemption.

The exact keys must match the current `InternationalTravelPolicyRules` model rather than inventing new policy concepts.

## Materiality

Materiality must be deterministic.

Examples:

- punctuation or source-span change with identical accepted semantic value: non-material;
- changed effective date: operationally material;
- changed employment-type coverage: operationally material;
- changed course identifier after deterministic resolution: operationally material;
- changed manager-approval requirement: operationally material;
- changed exemption behavior: operationally material.

Because the validated schema is semantic rather than textual, most accepted value changes will be material.

Do not claim to distinguish all editorial wording changes. In this slice, raw-language differences with identical validated semantics should result in no material rule change.

## Application service

Create a synchronous service that:

1. loads both policy records;
2. verifies organization and family compatibility;
3. loads the authoritative accepted extraction attempt for each;
4. verifies no unresolved clarification blocks either ruleset;
5. reconstructs the typed rule versions and provenance;
6. executes the pure comparator;
7. computes a canonical fingerprint;
8. persists comparison and ordered differences in one transaction;
9. reloads and returns the immutable aggregate.

Repeated equivalent requests should return the existing comparison.

## API

Suggested endpoints:

```http
POST /api/v1/policy-comparisons
GET /api/v1/policy-comparisons/{comparison_id}
```

Create request:

```json
{
  "baseline_policy_change_id": "...",
  "proposed_policy_change_id": "..."
}
```

Do not accept rule values, extraction IDs, materiality, or actor assertions from the request body unless there is a clear product need.

The backend should resolve authoritative accepted attempts.

Stable errors should include:

- `baseline_policy_not_ready`
- `proposed_policy_not_ready`
- `policy_comparison_family_mismatch`
- `policy_comparison_organization_mismatch`
- `policy_comparison_same_policy`
- `policy_comparison_schema_unsupported`
- `policy_comparison_lineage_inconsistent`

## UI

Add a focused comparison path to the policy-analysis entry or policy page.

The first UI does not need policy search, arbitrary upload management, or a generic comparison dashboard.

For seeded demo data, provide:

- current policy card;
- proposed revision card;
- compare control;
- summary counts;
- ordered differences;
- baseline and proposed values;
- exact source excerpts;
- materiality labels;
- reason-code explanation.

Do not combine impact delta into this UI yet.

## Seed data

Add one proposed revision of the existing international-travel policy.

Choose changes that produce understandable semantic differences, such as:

- an earlier effective date;
- expanded contractor or geography coverage;
- changed training requirement;
- a modified booking or approval obligation.

Keep the revision realistic and small enough that the reviewer can understand it quickly.

Do not add another policy family.

## Tests

### Unit

- identical rules produce no material differences;
- each supported field change produces the correct diff;
- change ordering is stable;
- provenance stays attached to the correct version;
- materiality is deterministic;
- canonical fingerprints are stable;
- source-span-only changes do not create semantic changes.

### Integration

- comparison persists atomically;
- repeated creation is idempotent;
- baseline and proposed records must differ;
- cross-organization comparison is rejected;
- unsupported schema is rejected;
- nonaccepted extraction is rejected;
- pending clarification is rejected;
- historical comparison remains unchanged after source records change;
- database immutability constraints reject update/delete where appropriate.

### API

- valid create returns `201` or existing resource according to current repository conventions;
- retrieval returns stable ordering;
- validation errors use stable codes;
- request cannot inject authoritative comparison values.

### Frontend

- summary renders;
- differences render in deterministic order;
- provenance is visible;
- material and unchanged states are not conflated;
- error states are understandable.

### Evaluation

No LLM evaluation should be added for the deterministic comparator.

Existing extraction evaluation fixtures should be extended only as needed to produce two accepted rulesets.

## Documentation

Update:

- README
- architecture
- roadmap
- decisions
- demo scenario
- new feature-expansion milestone document

Add an ADR explaining:

- typed semantic comparison rather than text diffing;
- deterministic materiality;
- immutable comparison aggregate;
- impact delta intentionally deferred.

## Explicit non-goals

Do not implement:

- enterprise impact delta;
- AI-generated diff;
- arbitrary document diffing;
- generic JSON diff framework;
- generic policy schema registry;
- workflow graph for comparison;
- change-plan revision;
- second adapter;
- MCP;
- AWS;
- Terraform;
- event sourcing.

## Acceptance criteria

The slice is complete when a reviewer can:

1. start from the two seeded policy versions;
2. compare them;
3. see deterministic semantic differences;
4. inspect provenance to both policies;
5. understand which differences are operationally material;
6. repeat comparison without duplicate artifacts;
7. verify historical comparison immutability;
8. run all existing tests, evaluations, migration checks, frontend checks, and demo-reset behavior successfully.

---

# 10. Conditions under which MCP becomes justified

MCP becomes justified only when all of the following are true:

1. There is at least one genuine external-process simulated enterprise service.
2. That service has a lifecycle or deployment boundary independent from the ChangeOps API.
3. The same governed tool contract should be callable by more than one client or runtime.
4. Network/process isolation provides a concrete security, ownership, or interoperability benefit.
5. Authorization context must cross that boundary explicitly.
6. The loss of local transaction atomicity is accepted and compensated for.
7. Idempotency and reconciliation semantics are designed for partial failure.
8. The protocol reduces custom integration code rather than adding ceremony around one function.
9. Tool selection remains deterministic.
10. No model autonomously chooses or invokes the tool.

A second in-process adapter does not meet these conditions.

A credible later MCP scenario would be:

- the simulated Jira service becomes an independently deployable application;
- it owns its own durable issue state;
- ChangeOps communicates through a stable typed protocol;
- the adapter must propagate approved actor and command identity;
- retries can occur after connection failure;
- the service can return an already-created issue by idempotency key;
- another governed client could use the same service.

Until that exists, the current explicit adapter interface is simpler and better.

---

# 11. Estimated PR count before AWS

## Recommended minimum

Five PRs:

1. comparison foundation;
2. impact delta;
3. plan revision foundation;
4. effective-plan selection and approval integration;
5. audit timeline.

Then begin AWS architecture work.

## With optional Jira

Six PRs.

## With a small quality page

Potentially six or seven, though I would fold the quality explanation into audit/documentation work rather than creating a standalone platform feature.

## Expected total before the first Terraform implementation PR

Approximately **6–7 PRs**, including one AWS architecture/ADR PR.

Do not target ten or more feature PRs before cloud work.

---

# 12. Stop condition

The feature-expansion phase ends when all of these are true:

1. A reviewer can compare a current policy with a proposed revision.
2. The system deterministically explains semantic rule changes.
3. The system deterministically explains newly affected and no-longer-affected enterprise objects.
4. AI explains the delta but cannot alter it.
5. A human can request a governed revision of an AI plan.
6. The revised plan is a new immutable artifact with validated grounding and lineage.
7. Approval unambiguously applies to the intended effective artifact.
8. A single audit timeline explains the journey across AI, deterministic code, human decisions, and execution.
9. The existing Learning execution remains reliable, idempotent, and demonstrable.
10. APIs and data models are stable enough to deploy.
11. The demo reset and CI remain reliable.
12. Every remaining proposed feature would repeat a capability already demonstrated rather than answer a new product or architecture question.

At that point, stop adding features and move to AWS.

Specifically, do not delay AWS merely to add:

- another policy family;
- another similar integration;
- MCP;
- generic evaluation infrastructure;
- generic workflow tooling;
- configurable rules;
- richer revision branching;
- notification systems;
- production-grade organizational RBAC.

The capstone is strong when it demonstrates distinct capabilities, not when every conceivable enterprise feature is present.