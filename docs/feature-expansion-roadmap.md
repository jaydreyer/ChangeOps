# ChangeOps Feature-Expansion Roadmap Before AWS

## Executive recommendation

Build **three product capabilities** before AWS:

1. **Policy comparison**
2. **Governed plan revision**
3. **Unified audit**

These capabilities will likely be implemented through **four vertical slices**:

1. **Policy comparison foundation**
2. **Enterprise impact delta**
3. **Change-plan revision**
4. **Audit timeline**

The capability count and implementation-slice count are intentionally different. Policy comparison requires a trusted semantic-comparison foundation before enterprise impact delta can build on it.

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

## 1. Policy comparison — Definitely build

### Product value: Very high

This is the feature that best fulfills the product name and vision.

It changes the central user question from:

> What does this policy affect?

to:

> What changed, and what operational consequences changed because of it?

### New engineering capability

It demonstrates:

- baseline/proposed lineage;
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

### A. Policy comparison

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

The three capabilities should be delivered through four likely vertical slices:

1. **Policy comparison foundation**
2. **Enterprise impact delta**
3. **Change-plan revision**
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

# 7. Roadmap from current `main` through AWS

## Capability 1 — Policy comparison

This capability is likely to require two vertical slices.

### Slice 1 — Policy comparison foundation

Establish comparison between one baseline policy and one proposed revision using one immutable comparison aggregate. This slice intentionally does not introduce policy version numbering, current-version flags, supersession state, general revision management, or policy lifecycle administration.

The first slice is governed by [`docs/milestone-5a-policy-comparison.md`](milestone-5a-policy-comparison.md). The roadmap intentionally does not repeat API design, table design, endpoint payloads, test lists, or other implementation details governed by that milestone.

**Status: complete.** The product now resolves two completed accepted analyses, compares their
schema-v1 typed semantics deterministically, persists one immutable fingerprinted aggregate,
preserves side-specific provenance, exposes create/retrieve APIs and a focused Next.js experience,
and resets generated comparisons without removing either source policy.

### Slice 2 — Enterprise impact delta

Extend the trusted policy comparison into before-and-after enterprise consequences. Deterministic code must continue to own the authoritative delta; AI may explain the completed, grounded delta but cannot alter it.

This is where the product becomes recognizably ChangeOps: it can explain not only what policy semantics changed, but what operational consequences changed because of them.

## Capability 2 — Governed plan revision

### Slice 3 — Change-plan revision

Close the existing `revision_requested` governance loop through immutable, human-directed plan revision with validated grounding and unambiguous approval lineage.

The product principle remains that humans provide revision intent and govern the result; they do not directly overwrite AI-generated historical artifacts. Detailed lifecycle and approval behavior belongs in the milestone that governs this slice.

## Capability 3 — Unified audit

### Slice 4 — Audit timeline

Provide one ordered, product-facing projection over authoritative artifacts so reviewers can understand AI proposals, deterministic decisions, human actions, approvals, execution, and replay without learning the storage schema.

This remains a projection over authoritative records, not a move to event sourcing or a generic audit-event table.

## Optional execution validation

A Jira-style execution action remains conditional. Build it only if comparison produces a meaningful product need or reveals a real coupling defect in the current command abstraction.

## AWS architecture and deployment

After the four likely product slices, make the explicit AWS architecture decisions for hosting, PostgreSQL, authentication, secrets, migrations, observability, demo-data lifecycle, cost, and public safety. Terraform and deployment follow those decisions.

The local trusted-header boundary must be replaced for public deployment, but that remains AWS-phase work rather than pre-AWS product scope.

---

# 8. Next single vertical slice

## Recommended next slice

**Calculate enterprise impact delta from two immutable policy assessments.**

The trustworthy immutable semantic comparison aggregate now exists. The next slice should derive
before-and-after enterprise consequences without changing the completed policy comparison or
allowing AI to author authoritative delta.

## User-visible outcome

A reviewer should be able to see which workers and enterprise objects became affected, remained
affected, or were cleared, with deterministic evidence explaining every delta.

## Why this is the right first slice

It builds directly on the completed semantic comparison while keeping assessment snapshots and
enterprise facts authoritative. It is the next point where ChangeOps can answer not only what
policy obligations changed, but what operational consequences changed.

---

# 9. Conditions under which MCP becomes justified

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

# 10. Expected slices before AWS

## Recommended product sequence

Four likely vertical slices:

1. policy comparison foundation;
2. enterprise impact delta;
3. change-plan revision;
4. audit timeline.

Then begin AWS architecture work. A governing milestone may refine how a slice is packaged into pull requests without changing the roadmap's three-capability direction.

## With optional Jira

One additional optional slice.

## With a small quality page

Potentially one additional optional slice, though I would fold the quality explanation into audit/documentation work rather than creating a standalone platform feature.

## Expected total before the first Terraform implementation PR

Approximately **4 product slices** followed by one AWS architecture/ADR decision point. Pull-request count is an implementation-planning detail rather than a roadmap commitment.

Do not target ten or more feature PRs before cloud work.

---

# 11. Stop condition

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
