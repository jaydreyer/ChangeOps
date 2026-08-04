# ChangeOps Remaining Work Inventory

## Purpose

This document is the master inventory for the remaining ChangeOps capstone work.

It exists to:

- preserve the remaining product and engineering ideas;
- establish their priority and sequence;
- prevent useful ideas from being forgotten;
- prevent feature expansion from becoming endless;
- distinguish committed work from optional work;
- define when ChangeOps is ready for AWS deployment and portfolio presentation.

This is a planning checklist, not an implementation specification.

Each substantial capability should receive its own milestone document and reviewable vertical slice before implementation begins.

---

## Current product state

ChangeOps currently demonstrates:

- AI-assisted policy-rule extraction;
- deterministic validation and identifier resolution;
- bounded human clarification;
- immutable policy assessments;
- worker and enterprise impact discovery;
- grounded AI interpretation;
- immutable change plans;
- item-level human review;
- approval, rejection, deferral, and revision intent;
- immutable execution-command preparation;
- explicit deterministic execution;
- simulated Learning System execution;
- real Jira Cloud issue creation;
- idempotency and replay protection;
- immutable execution results;
- policy-version comparison;
- deterministic semantic rule differences;
- enterprise impact delta;
- exact evidence and provenance;
- reliable local demo reset;
- focused evaluations and CI;
- guided enterprise UX across the golden path.
- read-only Enterprise Knowledge Catalog browse and detail views over the existing typed source
  and dependency tables;

The application already constitutes a credible end-to-end enterprise AI capstone.

Remaining work must add a distinct product, architecture, deployment, or presentation story. Work that merely adds another technology or repeats an existing capability should be rejected.

---

# Remaining-work summary

## Completed

- [x] Core policy-analysis journey
- [x] Human clarification
- [x] Immutable assessment
- [x] Enterprise impact discovery
- [x] Grounded interpretation and change plan
- [x] Human approval workflow
- [x] Immutable execution commands
- [x] Simulated Learning System execution
- [x] Idempotent execution and replay history
- [x] Policy-version comparison
- [x] Enterprise impact delta
- [x] Guided analysis UX
- [x] Guided approval and execution UX
- [x] Comparison UX and progressive disclosure
- [x] Real Jira Cloud issue creation
- [x] Presentation and interview guide foundation
- [x] Enterprise Knowledge Catalog Explorer (Milestone 7 PR A)

## Recommended remaining work

- [x] Narrow Confluence-backed document source integration and live Acme page validation
- [ ] Trusted relationship provenance and governance
- [ ] Unified audit timeline
- [ ] AWS deployment architecture decision
- [ ] Terraform implementation and AWS deployment
- [ ] Operational hardening for the public demo
- [ ] Final presentation and interview preparation

## Conditional work

- [ ] Human-requested change-plan regeneration and version lineage
- [ ] AI-proposed catalog relationship requiring human acceptance
- [ ] Evaluation evidence view
- [ ] MCP boundary

## Explicitly deferred or rejected

- [ ] Additional policy families
- [ ] Additional execution adapters
- [ ] Confluence document editing
- [ ] Autonomous tool selection
- [ ] Generic enterprise catalog platform
- [ ] Generic knowledge graph tooling
- [ ] Graph database
- [ ] Generic document crawler
- [ ] Broad RAG over enterprise content
- [ ] Generic connector framework
- [ ] Plugin marketplace
- [ ] Event-sourcing rewrite
- [ ] Microservices
- [ ] Kubernetes
- [ ] Queues and background workers without demonstrated need
- [ ] Production-scale RBAC
- [ ] Multiple AWS environments

---

# Phase 1 — Enterprise knowledge foundation

## Goal

Answer clearly:

> Where did ChangeOps get its knowledge of enterprise documents, systems, courses, commitments, and their relationships to policy rules?

This phase should explain and expose the enterprise facts that the current analysis already uses.

It must not become a generic CMDB, data catalog, or knowledge-graph product.

---

## 1. Enterprise Knowledge Catalog Explorer

### Product question

> What enterprise objects does ChangeOps know about, and where did that information come from?

### Required capability

Provide a read-only product experience for inspecting the existing fictional enterprise catalog.

The catalog should expose the current supported object categories, such as:

- documents;
- systems;
- training courses;
- workers or organizational entities where appropriate;
- customer commitments;
- enterprise processes or dependencies already represented by the current data model.

### Minimum reviewer experience

A reviewer can:

- browse catalog objects by category;
- open one object;
- see its stable identity;
- see its business-facing name and description;
- see its owner;
- see its source system;
- see its status;
- see applicable metadata;
- see trusted relationships;
- follow a relationship to the connected rule or enterprise object;
- understand whether the relationship was seeded, imported, curated, or approved.

### Flagship example

```text
Manager Travel Approval Guide
    ↓
Source: Confluence
Owner: Travel Operations
Status: Published
    ↓
Trusted relationship
    ↓
MANAGER_APPROVAL_REQUIRED
```

### Architecture constraints

- PostgreSQL remains authoritative for the imported catalog projection used by ChangeOps.
- Existing stable identities should be reused.
- The explorer is read-only in its first slice.
- No graph database.
- No generic search platform.
- No catalog administration UI.
- No arbitrary metadata-schema builder.
- No relationship editing in the first slice.
- No AI is required for basic catalog display.

### Completion criteria

- [x] Existing seeded documents, systems, and training courses are visible through a coherent
      catalog UI; workers, teams, and customer commitments remain compact assessment context.
- [ ] Object ownership and source-system provenance are visible.
- [x] Persisted typed relationship trust basis can be inspected separately from the explicitly
      missing row-origin provenance.
- [x] A reviewer can explain why the Manager Travel Approval Guide is deterministic assessment
      input for both baseline and proposed policy scopes.
- [x] Existing analysis behavior remains unchanged.
- [x] Demo reset remains safe, repeatable, and preserves the catalog projection.

PR A intentionally leaves the ownership/source-provenance criterion incomplete where the typed
tables do not persist those facts. External document identity remains PR B; relationship-origin
provenance remains a separate, later PR C decision.

---

## 2. Narrow Confluence-backed document source

### Product question

> Can an enterprise object referenced by ChangeOps correspond to an actual record in an external knowledge system?

### Recommended scope

Create a small fictional Acme knowledge base in Confluence containing approximately five to eight realistic pages.

Potential pages:

- Manager Travel Approval Guide
- International Travel Booking Procedures
- International Travel FAQ
- Corporate Expense Policy
- Travel Security and Duty-of-Care Guide
- Employee International Travel Training Overview
- Emergency Travel Escalation Procedure
- Contractor Travel Eligibility Guide

The exact inventory should match objects already represented by ChangeOps rather than introducing new concepts solely to populate Confluence.

### Import behavior

ChangeOps may import or synchronize only the fields it actually needs:

- Confluence page ID;
- title;
- URL;
- space identifier;
- version;
- status;
- owner or maintainer where available;
- last-updated timestamp;
- optional short excerpt or bounded summary;
- source fingerprint.

### Non-goals

Do not implement:

- broad Confluence crawling;
- RAG over all pages;
- embedding search;
- automatic document classification;
- automatic relationship creation;
- document editing;
- page publishing;
- bidirectional synchronization;
- webhooks;
- continuous background synchronization.

A manual or explicit refresh is sufficient for the capstone.

### External-link behavior

Where an affected document appears in ChangeOps, a reviewer should be able to:

- see that the object came from Confluence;
- open the actual Confluence page;
- return to the ChangeOps evidence and relationship view.

A Jira remediation task may include a link to the relevant Confluence page.

### Completion criteria

- [x] A small, coherent Acme Confluence knowledge base exists.
- [x] The selected catalog document record links to its real Confluence page after live setup.
- [x] The Manager Travel Approval Guide exists as an actual page after manual setup.
- [x] ChangeOps can import or resolve bounded page metadata.
- [x] Imported identity is stable and idempotent.
- [x] Automated tests do not require live Confluence.
- [x] CI uses mocked or fixture-based provider behavior.
- [x] ChangeOps never edits Confluence.

The live Acme space contains the Manager Travel Approval Guide plus bounded procedures, training,
FAQ, and policy-reference context. Only the Manager Travel Approval Guide is wired into ChangeOps.
The August 4, 2026 live walkthrough confirmed successful import, `already_current` idempotency, the
external link, responsive presentation, and zero console errors. The adapter issues only bounded
GET requests. The current local Atlassian credential nevertheless has update and delete permission,
which is an explicitly accepted limitation for the current demo environment. The operational
hardening checklist remains honest about the credential permission boundary without blocking PR B.

---

## 3. Trusted relationship provenance

### Product question

> Why does ChangeOps trust that a policy rule is related to a particular enterprise object?

### First-slice requirement

Expose relationship provenance for the existing deterministic relationships.

A trusted relationship should identify, where supported:

- source rule or object;
- target enterprise object;
- relationship type;
- business explanation;
- source of the relationship;
- creator or owning authority;
- creation timestamp;
- status;
- validation or approval history.

### Relationship-source categories

Use a closed set appropriate to the implemented data:

- seeded demonstration data;
- imported authoritative metadata;
- human-curated mapping;
- human-approved AI proposal.

Do not claim an imported or approved source when the relationship was seeded.

### Optional second slice: AI-proposed relationships

AI may propose a relationship such as:

> The Manager Travel Approval Guide appears to cover the `MANAGER_APPROVAL_REQUIRED` rule.

The proposal must include:

- source content or metadata;
- target rule;
- explanation;
- confidence or ambiguity information;
- exact evidence.

A human must accept or reject the proposal before it becomes a trusted relationship used in deterministic impact analysis.

### Authority boundary

```text
AI proposes relationship
        ↓
Human reviews evidence
        ↓
Human accepts or rejects
        ↓
Accepted relationship becomes trusted enterprise data
        ↓
Future impact analysis uses it deterministically
```

AI must never silently create authoritative relationships during policy analysis.

### Completion criteria for the required slice

- [ ] Relationship provenance is visible.
- [ ] Seeded relationships are honestly labeled.
- [ ] The reviewer can distinguish enterprise facts from AI recommendations.
- [ ] Existing impact traversal continues to use only trusted relationships.

### Decision gate for AI proposals

Implement AI-proposed relationship governance only when the read-only catalog and Confluence source are understandable and stable.

---

# Phase 2 — Unified auditability

## 4. Unified audit timeline

### Product question

> What happened across the complete ChangeOps journey, in what order, and which authoritative artifacts prove it?

### Recommended capability

Create a deterministic read projection across the existing immutable and authoritative records.

Potential timeline entries include:

- policy stored;
- extraction attempted;
- extraction accepted or rejected;
- clarification requested;
- clarification answered;
- assessment created;
- interpretation attempted;
- change plan created;
- comparison created;
- impact delta created;
- action review created;
- human decision recorded;
- approval completed;
- execution command prepared;
- execution requested;
- simulated side effect created;
- Jira issue created;
- replay prevented;
- execution failure recorded.

### Required fields

Every timeline entry should expose:

- timestamp;
- actor category;
- actor identity where applicable;
- action or event description;
- outcome;
- authoritative artifact type;
- authoritative artifact ID;
- link to the corresponding detail view.

Actor categories should remain explicit:

- AI-assisted;
- deterministic system;
- human;
- external system.

### Architecture constraints

- Build a read projection.
- Do not create a generic event-sourcing architecture.
- Do not make a synthetic event table the new source of truth.
- Derive entries from persisted authoritative artifacts.
- Define deterministic ordering for equal timestamps.
- Do not introduce queues or background materialization unless repository evidence proves it necessary.

### Completion criteria

- [ ] The complete golden path is understandable in one ordered view.
- [ ] Every event links to an authoritative persisted artifact.
- [ ] AI, deterministic system, human, and external actions are distinguishable.
- [ ] Jira creation and replay behavior are visible.
- [ ] The timeline introduces no new source of truth.
- [ ] Historical artifacts remain immutable.

---

# Phase 3 — AWS deployment

## 5. AWS architecture decision

### Product question

> What is the smallest credible public deployment architecture for ChangeOps?

### Required decisions

Document and select:

- frontend hosting;
- FastAPI hosting;
- PostgreSQL hosting;
- container registry;
- networking;
- authentication boundary;
- trusted actor propagation;
- secret storage;
- Jira and Confluence credential management;
- database migration execution;
- logging;
- metrics;
- tracing or request correlation;
- health checks;
- demo-data lifecycle;
- reset restrictions;
- backup and recovery expectations;
- cost envelope.

### Default architecture bias

Prefer a modular-monolith deployment.

Do not split the application into microservices merely because AWS makes that possible.

A likely shape may include:

- Next.js deployment;
- one containerized FastAPI service;
- managed PostgreSQL;
- managed secret storage;
- HTTPS ingress;
- centralized logs;
- Terraform-managed infrastructure.

The exact services must be selected after inspecting current repository and deployment needs.

### Authentication

The public deployment cannot trust locally supplied identity headers.

The architecture must define:

- how a user authenticates;
- how actor identity reaches the backend;
- how the backend derives rather than trusts authorization context;
- how demo access is constrained.

Do not build elaborate enterprise RBAC. A small credible authentication boundary is sufficient.

### Completion criteria

- [ ] Architecture decision is documented before Terraform work begins.
- [ ] Every AWS service solves an explicit need.
- [ ] Estimated monthly cost is documented.
- [ ] Local and public trust boundaries are distinguished.
- [ ] Secret handling is defined.
- [ ] Migration and reset behavior are defined.
- [ ] No speculative multi-environment architecture is introduced.

---

## 6. Terraform and deployment

### Goal

Deploy the existing application reproducibly.

### Required outcomes

- [ ] Terraform provisions the required AWS infrastructure.
- [ ] The backend runs from a built container.
- [ ] PostgreSQL is managed and durable.
- [ ] Database migrations run through a controlled deployment step.
- [ ] Secrets are not stored in source control or image layers.
- [ ] Health checks are available.
- [ ] Logs are centralized and usable.
- [ ] Public access is constrained by the selected authentication approach.
- [ ] Jira and optional Confluence credentials are securely configured.
- [ ] The deployed application can complete the flagship journey.
- [ ] Deployment and teardown instructions are documented.
- [ ] The expected monthly cost is verified.

### Explicit non-goals

- no Kubernetes;
- no multiple environments by default;
- no service mesh;
- no autoscaling architecture without demonstrated need;
- no production SRE platform;
- no generic CI/CD platform redesign.

---

## 7. Public-demo operational hardening

### Required checks

- [ ] Demo reset cannot run against an unrecognized database.
- [ ] Destructive actions are protected.
- [ ] External Jira writes target only the dedicated demo project.
- [ ] Confluence credential access is restricted to read-only.
- [ ] Credentials have minimal permissions.
- [ ] Rate-limit and provider failures are understandable.
- [ ] External calls use bounded timeouts.
- [ ] Sensitive values are never logged.
- [ ] Health endpoints do not expose secrets.
- [ ] Logs include correlation identifiers.
- [ ] Idempotency survives retries and uncertain responses.
- [ ] The public demo has a documented recovery procedure.

---

# Phase 4 — Portfolio and interview readiness

## 8. Presentation and interview guide

### Required presentation formats

Prepare:

- [ ] 30-second product explanation
- [ ] 2-minute product walkthrough
- [ ] 5-minute architecture walkthrough
- [ ] 10–15-minute complete capstone demonstration
- [ ] deep-dive answers for technical interviews

### Core explanations

Be prepared to explain:

- [ ] the business problem;
- [ ] why the flagship scenario is international travel;
- [ ] where enterprise catalog facts come from;
- [ ] how trusted relationships are created;
- [ ] what AI is allowed to do;
- [ ] what deterministic code owns;
- [ ] what humans own;
- [ ] why PostgreSQL is authoritative;
- [ ] why LangGraph is orchestration rather than the system of record;
- [ ] why immutable artifacts exist;
- [ ] why approval and execution are separate;
- [ ] why execution commands are immutable;
- [ ] why execution is idempotent;
- [ ] why policy comparison is deterministic;
- [ ] what the impact delta proves and does not prove;
- [ ] why Jira creation is narrow and governed;
- [ ] why ChangeOps reads but does not edit Confluence;
- [ ] why MCP was deferred;
- [ ] why microservices and event sourcing were rejected.

### Honest implementation story

Use an explanation such as:

> I defined the product boundaries and architecture, used AI coding tools as implementation partners, reviewed their plans and pull requests, challenged unsafe or overengineered decisions, and required evidence through tests, migrations, evaluations, and working vertical slices.

Do not imply that every line was manually authored without AI assistance.

### Demo ending

The strongest likely ending is:

```text
Policy change analyzed
        ↓
Enterprise impact explained
        ↓
Human approves remediation
        ↓
Immutable command prepared
        ↓
Human explicitly executes
        ↓
Real Jira issue created
        ↓
Replay does not create a duplicate
        ↓
Audit timeline shows the complete journey
```

---

# Conditional backlog

## Human-requested change-plan regeneration

### Value

Demonstrates governed AI iteration and immutable version lineage.

### Potential capability

```text
Plan v1
    ↓
Human requests revision
    ↓
New interpretation attempt
    ↓
Deterministic grounding validation
    ↓
Plan v2
    ↓
Effective version selected
    ↓
Approval applies to selected version
```

### Decision

Do not implement automatically.

Reassess after catalog, audit timeline, and AWS architecture are complete.

Build only if the current “revision requested” behavior feels materially incomplete in the final demonstration.

---

## Evaluation evidence view

### Value

Makes the project’s quality discipline visible.

### Potential content

- offline evaluation categories;
- fixture versions;
- prompt and model versions;
- grounding-validation outcomes;
- failure-code counts;
- recent live-provider smoke metadata;
- known limitations;
- what green CI proves and does not prove.

### Decision

Optional.

Prefer documentation unless a product page materially improves the capstone demonstration.

Do not build a generic evaluation platform.

---

## MCP boundary

### Decision

Deferred unless a genuine process boundary emerges.

MCP becomes justified only when:

- an external simulated or real enterprise service runs independently;
- it owns its own lifecycle and durable state;
- multiple clients benefit from a shared tool contract;
- authorization context must cross that boundary;
- network failure and reconciliation are explicitly designed;
- MCP reduces custom integration code;
- tool routing remains deterministic;
- AI does not autonomously select or invoke tools.

Jira and Confluence REST integrations alone do not automatically justify MCP.

---

# Recommended sequence

## Immediate sequence

1. [x] Add and approve this remaining-work inventory.
2. [x] Inspect current catalog models and seeded relationships.
3. [x] Define a narrow Enterprise Knowledge Catalog milestone.
4. [x] Implement the read-only catalog explorer.
5. [x] Create the bounded Acme Confluence content set using the documented manual setup.
6. [x] Add read-only Confluence metadata import and links.
7. [ ] Expose trusted relationship provenance.
8. [ ] Decide whether AI-proposed relationship governance adds sufficient value.
9. [ ] Implement the unified audit timeline.
10. [ ] Produce the AWS architecture decision.
11. [ ] Implement Terraform and deploy.
12. [ ] Complete operational hardening.
13. [ ] Finish the presentation and interview guide.

## Recommended PR packaging

Likely reviewable slices:

1. Catalog explorer over existing data
2. Confluence source records and bounded import
3. Relationship provenance
4. Optional AI-proposed relationship review
5. Unified audit timeline
6. AWS architecture decision
7. Terraform foundation
8. Deployable application and operational controls
9. Final demo and documentation polish

Do not combine all catalog and Confluence work into one oversized PR.

---

# Decision gates

## Gate A — After catalog explorer

Ask:

> Does the catalog make the current enterprise-impact logic understandable without adding new explanation?

If no, improve the catalog presentation before adding Confluence.

## Gate B — After Confluence

Ask:

> Does linking to real documents materially improve the demo and architecture story?

If no, stop Confluence work. Do not add crawling, RAG, or editing.

## Gate C — Before relationship proposals

Ask:

> Is there a meaningful governance story beyond the already seeded relationships?

If no, retain visible provenance and defer AI relationship proposals.

## Gate D — Before AWS

Confirm:

- product models and APIs are stable;
- catalog scope is closed;
- audit timeline is complete;
- Jira behavior is reliable;
- Confluence remains read-only;
- no additional feature is required to explain the flagship journey.

## Gate E — Before any additional feature after deployment

Ask:

> Does this feature answer a new product or architecture question, or does it merely add another example of something ChangeOps already proves?

Reject work in the second category.

---

# Stop condition

Feature expansion stops when:

- the Enterprise Knowledge Catalog explains where enterprise facts originate;
- at least one real Confluence document can be inspected from ChangeOps;
- trusted relationship provenance is understandable;
- the complete journey is visible through an audit timeline;
- the application is reproducibly deployed with AWS and Terraform;
- the public demo is safe and reliable;
- the project owner can confidently explain and demonstrate the system.

After those conditions are met, do not delay completion to add:

- another policy family;
- another document source;
- another execution adapter;
- more Jira operations;
- Confluence editing;
- broad RAG;
- graph databases;
- MCP;
- generic workflow configuration;
- generic catalog administration;
- richer organizational permissions.

The finished capstone should demonstrate a small number of distinct capabilities deeply and credibly.
