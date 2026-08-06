# ChangeOps Presentation & Interview Guide

> A practical guide for demonstrating ChangeOps, explaining its architecture, and defending its engineering decisions with confidence.

## Purpose

This document is **not technical documentation**. It prepares the project owner to:

- demonstrate ChangeOps;
- explain the architecture;
- discuss design decisions;
- answer interview questions; and
- present the project confidently.

The focus is on **why the system is designed this way**, not on documenting every implementation detail.

## At a glance

| Layer | Focus | Target time |
|---|---|---:|
| [1](#layer-1--30-second-explanation) | Product and business value | 30 seconds |
| [2](#layer-2--two-minute-demo) | End-to-end product story | 2 minutes |
| [3](#layer-3--five-minute-architecture-walkthrough) | System architecture and responsibilities | 5 minutes |
| [4](#layer-4--ai-boundaries) | What AI does—and deliberately does not do | 2–3 minutes |
| [5](#layer-5--architecture-decisions) | Defensible engineering tradeoffs | As needed |
| [6](#layer-6--expected-interview-questions) | Concise interview answers | As needed |
| [7](#layer-7--deep-dives) | Major subsystem concepts | 3–5 minutes each |
| [8](#layer-8--demo-tips) | A smooth, focused presentation | Before the demo |

---

## Layer 1 — 30-second explanation

### Talk track

> Policy changes rarely stay inside a policy document. They affect people, training, approvals, documentation, customer commitments, and enterprise systems. ChangeOps turns a policy change into an evidence-backed impact assessment, compares revisions, recommends governed actions, routes consequential changes through human approval, and executes only what was explicitly approved. AI helps interpret ambiguous language and explain results, while deterministic code owns facts, classifications, workflow transitions, and execution. That gives enterprises the speed of AI without surrendering control, repeatability, or auditability.

### Five points to land

1. **Business problem:** Organizations discover downstream effects manually and often miss them.
2. **Product:** ChangeOps traces a change from policy through impact, approval, and execution.
3. **AI value:** AI interprets language and synthesizes evidence where judgment is useful.
4. **AI constraint:** Deterministic code retains authority over facts and consequential actions.
5. **Enterprise value:** Every conclusion and action is explainable, reviewable, and auditable.

---

## Layer 2 — Two-minute demo

Walk through the product from beginning to end **without discussing code**.

### Recommended flow

| Time | Stage | What to show | What to say |
|---:|---|---|---|
| 0:00–0:20 | **Policy** | The international-travel policy and effective date | “A business user begins with a real operational change, not a technical workflow.” |
| 0:20–0:45 | **Analysis** | Extracted rules, scope, exceptions, and any clarification | “The policy becomes a validated, reviewable set of rules. Ambiguity is surfaced instead of hidden.” |
| 0:45–1:05 | **Comparison** | Baseline and proposed policy differences | “ChangeOps compares business meaning, so wording-only changes do not create false operational differences.” |
| 1:05–1:25 | **Impact** | Affected workers, enterprise objects, reason codes, and evidence | “Every impact explains what is affected, why, and which evidence supports the conclusion.” |
| 1:25–1:45 | **Approval** | Proposed actions and the review workbench | “A recommendation is not permission. Consequential actions require an explicit human decision.” |
| 1:45–2:00 | **Execution** | Prepared command and simulated result | “Only the approved intent is converted into an executable command, and retries are safe.” |

### Closing line

> ChangeOps preserves one continuous chain from policy language to evidence, decision, and execution result.

---

## Layer 3 — Five-minute architecture walkthrough

### The architecture in one sentence

ChangeOps is a synchronous modular monolith in which PostgreSQL owns durable truth, LangGraph makes workflow topology explicit, deterministic services own business decisions, and AI is isolated to language understanding and grounded interpretation.

### Component responsibilities

| Component | Role | Why it exists |
|---|---|---|
| **FastAPI** | Exposes typed HTTP boundaries for analysis, comparison, approval, and execution | It provides clear request/response contracts, validation, and a straightforward integration surface. |
| **PostgreSQL** | Stores source data, workflow state, immutable artifacts, approvals, commands, and results | Enterprise workflows need durable, queryable, transactionally consistent state with enforceable constraints. |
| **LangGraph** | Expresses analysis and approval workflow topology, routing, and pause/resume boundaries | The graph makes multi-stage orchestration visible and extensible without becoming the system of record. |
| **Deterministic services** | Validate rules, classify impacts, compare policies, calculate deltas, authorize transitions, and map commands | Known rules should be repeatable, testable, and explainable. |
| **Immutable artifacts** | Preserve completed assessments, comparisons, deltas, evidence, and decisions | Historical conclusions must continue to mean what they meant when a decision was made. |
| **Human approval** | Separates recommendation from authorization | Consequential enterprise actions require accountable human judgment. |
| **Execution adapters** | Apply approved commands to the simulated Learning System and real Jira Cloud | The same governance boundary supports durable local effects and one narrowly scoped external write. |

### Suggested walkthrough

1. **Start at the API boundary.** FastAPI receives a request and validates its contract.
2. **Show workflow orchestration.** LangGraph coordinates stages but persists no authoritative state of its own.
3. **Move to deterministic analysis.** Typed services apply validated rules to enterprise facts.
4. **Land on PostgreSQL.** Durable lifecycle state and completed artifacts are persisted transactionally.
5. **Separate interpretation from truth.** AI can explain an assessment but cannot rewrite it.
6. **Finish with governance.** Approval creates authority; command preparation freezes intent; execution records the outcome.

> **Key framing:** LangGraph coordinates work. PostgreSQL remembers it. Deterministic services decide it. Humans authorize it.

---

## Layer 4 — AI boundaries

### What AI owns

- extracting candidate structured rules from unstructured policy language;
- identifying ambiguity and proposing clarification questions;
- synthesizing persisted evidence into a human-readable interpretation; and
- explaining recommendations without changing authoritative results.

### What AI does not own

| Question | Concise answer |
|---|---|
| **Why doesn’t AI classify workers?** | Worker classification applies known dates, locations, worker types, trips, exceptions, and training facts. Deterministic code produces the same answer from the same validated inputs and can show the exact rule that caused it. |
| **Why doesn’t AI execute actions?** | Execution changes enterprise state. It requires explicit authorization, strict validation, stable identifiers, idempotency, and a complete audit record—not probabilistic judgment. |
| **Why doesn’t AI update Jira or another enterprise system?** | A model may recommend an action, but a governed adapter must enforce permissions, schemas, allowed fields, and approved intent before any external write occurs. |
| **Why doesn’t AI persist state?** | Durable state requires transactions, constraints, concurrency control, stable identity, and reliable recovery. PostgreSQL provides those guarantees; model context does not. |

### Principle to remember

> **AI assists; deterministic code decides; humans authorize.**

AI output remains proposed until validated. It cannot create enterprise facts, invent evidence, route itself around controls, approve recommendations, or perform authoritative calculations.

---

## Layer 5 — Architecture decisions

| Decision | Concise explanation |
|---|---|
| **PostgreSQL is authoritative** | It provides durable, transactional, queryable state and lets the database enforce ownership, immutability, uniqueness, and lifecycle invariants. |
| **LangGraph has no checkpointer** | Cross-process recovery is derived from explicit PostgreSQL records. A resumed run starts a fresh graph invocation and routes from durable domain state instead of restoring opaque framework state. |
| **Artifacts are immutable** | Assessments, comparisons, deltas, and decisions are historical evidence. Mutating them would change the basis on which earlier approvals or actions were made. New information creates a new artifact. |
| **Approval is separate from execution** | Approval answers “may this happen?” Execution answers “did it happen, and what was the result?” Keeping them separate prevents a recommendation or approval from becoming an accidental write. |
| **Command preparation is explicit** | Preparation translates an approved action into a stable, inspectable execution contract. Reviewers can see exactly what will be sent before side effects occur. |
| **Execution is idempotent** | Retries are inevitable. Stable command identity and recorded results prevent the same approved action from producing duplicate enterprise changes. |
| **Comparison is deterministic** | Policy comparison operates on validated typed semantics. The same two rulesets always yield the same differences, and wording-only changes do not create noise. |
| **Impact delta is deterministic** | Delta calculation compares persisted assessments by stable business meaning, producing reproducible operational changes without model variability. |
| **Evidence is copied, not recomputed** | A delta must explain what each assessment concluded at creation time. Snapshotting evidence prevents later source-data changes from rewriting history. |
| **MCP is intentionally deferred** | The project first proves the approval, command, idempotency, lineage, and audit boundaries with simulated systems. MCP becomes useful when real tool interoperability is needed, not merely to add another technology. |

---

## Layer 6 — Expected interview questions

### Architecture and technology

| Question | Concise answer |
|---|---|
| **Why LangGraph instead of plain Python?** | Plain Python could run the current flow. LangGraph is used because explicit nodes, conditional routes, and pause/resume boundaries make the workflow easier to inspect and extend. PostgreSQL—not LangGraph—provides durability. |
| **Why not let the LLM do everything?** | Most of the system handles known facts and rules where variability is a liability. AI is reserved for language interpretation and synthesis; deterministic code protects correctness, reproducibility, and control. |
| **Why not event sourcing?** | The product needs immutable outputs and a strong audit trail, but it does not currently need to reconstruct all state from a universal event log. Relational current state plus immutable decision and result records is simpler and sufficient. |
| **Why not microservices?** | The domains are still evolving together, the workload is local and synchronous, and independent scaling is not yet required. A modular monolith preserves boundaries without adding network, deployment, and consistency complexity. |
| **Why not vector search?** | The current scenario uses structured policy rules and explicit enterprise relationships. Exact relational queries and typed comparisons are more accurate and explainable than similarity search for this problem. |
| **Why no queues?** | Current operations are bounded and synchronous. Durable database state already supports safe retry and resume. A queue should be introduced when real workload, latency, or integration requirements justify asynchronous processing. |

### Data and domain modeling

| Question | Concise answer |
|---|---|
| **Why immutable data?** | Completed artifacts are evidence used by later decisions. Immutability preserves historical meaning, enables reliable comparison, and prevents silent revision of the audit trail. |
| **Why compare business identity instead of UUIDs?** | Regenerating the same logical assessment creates new database rows and UUIDs. Matching on stable business identity distinguishes real operational change from persistence noise. |
| **Why separate comparison from impact delta?** | Comparison asks what changed in policy semantics. Impact delta asks what changed for people and enterprise objects. Keeping them separate makes each result clearer, testable, and independently explainable. |
| **Why simulate enterprise systems?** | Simulation proves command mapping, approval lineage, idempotency, and result capture without requiring privileged credentials or risking real side effects. The adapter boundary remains replaceable. |

### Follow-up answers worth remembering

- **What would make you adopt microservices?** Independent scaling, ownership, deployment cadence, or reliability requirements at a proven domain boundary.
- **What would make you add a queue?** Long-running integrations, burst handling, provider rate limits, or a need to decouple command acceptance from execution.
- **What would make you add vector search?** A validated retrieval use case over a large unstructured corpus where semantic recall matters and every retrieved result can still be grounded.
- **What would make you add MCP?** Multiple real enterprise tools that benefit from a standard discovery and invocation contract after the authorization boundary is mature.

---

## Layer 7 — Deep dives

### Policy analysis

Policy analysis turns unstructured language into validated rules and then applies those rules to enterprise facts.

The important boundary is between **candidate interpretation** and **authoritative analysis**. AI may propose typed rules and identify ambiguity. Deterministic validation either accepts those rules, requests clarification, or fails closed. Only validated rules enter the impact engine.

**Emphasize:** uncertainty is surfaced explicitly; unsupported policies are not forced into the schema.

### Comparison

Comparison evaluates the business meaning of two accepted policy rulesets. It compares effective dates, scope, worker types, destinations, exceptions, and requirements—not prose or database identity.

This makes the result stable and operationally useful: a rewritten sentence with unchanged meaning produces no semantic difference, while a changed exception or requirement does.

**Emphasize:** AI may help extract each source policy, but it is not invoked to calculate the comparison.

### Impact delta

Impact delta explains how a policy change affects persisted enterprise outcomes:

- workers who became, remained, or are no longer affected;
- findings that appeared or disappeared; and
- enterprise impacts that were introduced or removed.

Items are matched by stable business identity. Each side carries the explanation and evidence captured in its own assessment, so the delta never rewrites history by consulting mutable source data.

**Emphasize:** semantic policy change and operational impact change are related but distinct questions.

### Approval

Approval is a durable human decision over an immutable proposed action. The reviewer sees the original recommendation, evidence, allowed modifications, and the rationale required for the decision.

The original action is never overwritten. Approval produces a separate decision record and, when appropriate, an effective approved action.

**Emphasize:** recommendation, authorization, and execution are three different lifecycle events.

### Execution

Execution begins only after approval. A preparation step maps the approved intent into a stable command with explicit lineage. The execution service validates that lineage again, invokes a governed adapter, and stores the result.

Idempotency means replay cannot duplicate the underlying action. Learning uses a unique local
assignment. Jira uses a durable at-most-once delivery gate because Create Issue has no unique
client idempotency key: confirmed success replays locally, while an ambiguous lost response is not
resent without an intentionally deferred reconciliation capability.

Jira is deliberately create-only. Updates and transitions would authorize different consequences,
require new command semantics, and complicate replay and drift handling without strengthening this
milestone's core proof.

**Emphasize:** the adapter is replaceable; immutable authorization and honest failure semantics are
the real design.

### Auditability

Auditability is built into the data model rather than reconstructed from application logs. A reviewer can trace:

```text
policy source
  → extracted and validated rules
  → impact assessment and evidence
  → proposed action
  → human decision and rationale
  → prepared command
  → execution result
```

Immutable snapshots, stable reason codes, explicit provenance, and database constraints keep that chain trustworthy even as source data changes.

**Emphasize:** logs help operators; persisted domain records explain business decisions.

### Evaluations

Evaluation follows architectural ownership:

- deterministic tests verify rules, classifications, comparisons, deltas, routing, constraints, and idempotency;
- contract evaluations replay fixed model outputs to test parsing, grounding, provenance, and fail-closed behavior; and
- live provider checks verify compatibility and end-to-end invariants without making CI depend on model variability.

**Emphasize:** every AI step has an evaluation that can fail, while deterministic guarantees remain independently testable.

---

## Layer 8 — Demo tips

### Ideal walkthrough order

1. Start with the policy and its business consequence.
2. Show validated rules and one meaningful exception.
3. Show one affected and one unaffected worker.
4. Open the evidence behind a conclusion.
5. Compare the baseline and proposed policy.
6. Move from impact to a proposed action.
7. Approve the action with a clear rationale.
8. Prepare, inspect, and execute the command.
9. Open the unified audit timeline and end on the execution result, Jira receipt, and prevented
   replay in one ordered chain.

### Where to pause

- **After the policy:** ask what downstream effects the reviewer would normally have to find manually.
- **At an exception:** show that ChangeOps explains unaffected cases, not only positive matches.
- **At the evidence:** reinforce that conclusions are traceable.
- **Before approval:** state that no enterprise write has occurred.
- **Before execution:** show that approved intent and executable command are distinct.
- **At the result:** close the loop back to the original policy.

### Common reviewer questions

- Is the LLM making the final classification?
- What happens when the policy is ambiguous?
- Can a user execute an unapproved action?
- What happens if execution is retried?
- Why is LangGraph needed if PostgreSQL stores the state?
- How do comparisons behave when records have different UUIDs?
- What changes when simulated integrations become real?
- Why does ChangeOps preserve a separate document ID when a Confluence page ID exists?
- What happens to imported metadata when Confluence is unavailable?
- Why is the audit timeline a read projection instead of an event store?
- How are events with equal timestamps ordered?
- Why do failed attempts and prevented replays remain visible?

### What not to explain unless asked

- every API route;
- table-by-table schema details;
- migration history;
- individual framework decorators;
- every graph node;
- frontend component structure; or
- speculative production infrastructure.

Keep the main story at the level of **problem → evidence → decision → controlled action**.

### Common pitfalls

| Pitfall | Better approach |
|---|---|
| Starting with the technology stack | Start with the policy-change problem and its business risk. |
| Calling the workflow an autonomous agent | Describe it as governed orchestration with explicit boundaries. |
| Saying AI “determines impact” | Say AI proposes structured interpretation; deterministic services determine impact. |
| Treating approval as execution | Show them as separate records and separate user actions. |
| Spending too long on the happy path | Include one exception, clarification, or unaffected worker to demonstrate trustworthiness. |
| Overclaiming production readiness | Be direct that enterprise systems are simulated while the governance contract is real. |
| Explaining every feature | Choose one strong example and follow it through the complete lineage. |

### Pre-demo checklist

- [ ] Seed data and services are running.
- [ ] The canonical policy scenario loads successfully.
- [ ] Analysis and comparison entry states are ready.
- [ ] At least one action is available for review.
- [ ] Actor identity and role are set correctly.
- [ ] The simulated Learning target and configured Jira project are in a known state.
- [ ] The optional Confluence page is explicitly refreshed, or the honest not-imported state is
      part of the walkthrough.
- [ ] Browser zoom and window size make evidence readable.
- [ ] A backup API response or screenshot is available.

---

## Goal

After the presentation, someone should understand:

- **the product:** ChangeOps turns policy changes into evidence-backed, governed action;
- **the architecture:** AI, deterministic services, workflow orchestration, persistence, and human approval have distinct responsibilities; and
- **the engineering decisions:** every boundary exists to improve explainability, repeatability, safety, or auditability.

They should not need to read the source code to understand why ChangeOps is built the way it is.
