ChangeOps: Initial Product Brief

Document status

This document preserves the product vision and Version 0.1 baseline. The README and roadmap are
authoritative for delivered milestone status.

Product vision

ChangeOps helps organizations understand and safely act on policy and operational changes that affect people, teams, documentation, training, customer commitments, and enterprise systems.

Instead of relying on employees to manually identify every downstream impact, ChangeOps builds an evidence-backed view of what is affected, proposes specific actions, routes consequential actions through human approval, executes approved actions through governed enterprise interfaces, and preserves a complete audit trail.

ChangeOps uses deterministic software for known rules and enterprise relationships. AI is introduced where interpretation, ambiguity resolution, evidence synthesis, and planning require judgment.

⸻

Product problem

Operational changes rarely remain contained within the document where they are announced.

A revised policy may affect:

* employees and contractors;
* managers and teams;
* approval processes;
* training requirements;
* knowledge articles and procedures;
* enterprise systems;
* customer delivery commitments.

Organizations often identify these effects manually through meetings, spreadsheets, institutional knowledge, and follow-up work distributed across multiple teams.

This creates predictable risks:

* affected groups are missed;
* conflicting guidance remains published;
* system changes are discovered late;
* customer commitments are overlooked;
* recommended actions lack supporting evidence;
* changes are executed without consistent approval or traceability.

ChangeOps is intended to make this process structured, explainable, and governable.

⸻

Initial use case

An HR or operations leader submits a new or revised employee policy.

ChangeOps progressively supports the following workflow:

1. Accept the policy change.
2. Extract or receive its effective date, scope, requirements, and exceptions.
3. Validate the policy representation.
4. Identify affected employees, contractors, managers, and teams.
5. Trace impacts to related systems, documentation, training, and customer commitments.
6. Produce an evidence-backed impact assessment.
7. Surface ambiguity and unresolved questions.
8. Recommend specific actions.
9. Require human approval for consequential actions.
10. Execute approved actions through governed enterprise tools.
11. Record the complete decision and execution history.

Not every step requires AI.

Known rules, persisted enterprise relationships, validation, permissions, identifiers, and impact classifications should remain deterministic.

⸻

Initial demonstration scenario

Effective September 1, employees traveling internationally for company business must complete the International Travel Security course and obtain manager approval before making any nonrefundable booking.

The policy applies to U.S.-based employees and contractors.

Travel booked before the effective date is exempt.

The demonstration scenario includes fictional enterprise data representing:

* employees and contractors;
* managers and teams;
* planned international travel;
* training completion records;
* travel-related systems;
* policy and knowledge documents;
* customer commitments connected to selected travelers.

The scenario is intentionally narrow enough to understand quickly while still demonstrating how one policy change can propagate across an enterprise.

⸻

Target users

* HR operations leaders
* Legal and compliance teams
* Product operations teams
* Enterprise knowledge managers
* Internal-platform teams
* Change-management leaders
* Training and enablement teams
* Customer operations leaders

⸻

Core product principles

Evidence before action

Every material conclusion and recommendation should be supported by source data, policy evidence, deterministic rules, or explicit human input.

Human control over consequential decisions

ChangeOps may recommend actions, but consequential actions require explicit human approval.

Deterministic rules where sufficient

Known business rules, enterprise relationships, validations, permissions, identifiers, sorting, and fingerprints should be implemented deterministically.

AI for interpretation and synthesis

AI should be used for tasks such as:

* interpreting unstructured policy language;
* identifying ambiguity;
* synthesizing evidence;
* drafting recommendations;
* explaining proposed changes.

AI should not become the authoritative source for facts already represented in enterprise data.

Clear separation between recommendation and execution

A proposed action is not an executed action.

The system must preserve this distinction in its data model, workflow, interface, and audit history.

Full traceability

A reviewer should be able to determine:

* what changed;
* what was affected;
* why it was classified as affected;
* what evidence was used;
* what action was proposed;
* who approved or rejected it;
* what was executed;
* what result was returned.

Least-privilege access

Users and tools should receive only the permissions required for their assigned role and action.

Recoverable workflows

Long-running or interrupted workflows should preserve state and resume safely.

Explicit uncertainty

Ambiguous, unsupported, or incomplete conclusions should be surfaced rather than hidden behind confident language.

No hidden autonomous writes

ChangeOps must not silently modify enterprise systems.

⸻

Version 0.1 scope

Version 0.1 establishes the trusted deterministic foundation for ChangeOps.

It will:

* load one structured policy-change scenario;
* evaluate the policy against seeded enterprise data;
* identify affected employees and contractors;
* identify affected managers and teams;
* identify related systems;
* identify related documentation;
* identify applicable training requirements;
* identify affected customer commitments;
* produce an immutable impact assessment;
* include supporting evidence for each major finding;
* include stable reason codes and relationship paths;
* propose deterministic actions without executing them;
* distinguish affected and unaffected enterprise objects;
* expose the assessment through a stable API.

Version 0.1 will run locally using Docker Compose.

It will not yet include:

* unstructured policy ingestion;
* LLM-based extraction;
* LangChain;
* LangGraph;
* human approval workflows;
* MCP integrations;
* action execution;
* a production frontend;
* production AWS infrastructure;
* autonomous write actions.

⸻

Version 0.1 product outcome

A reviewer should be able to run the demonstration scenario and answer:

* Which workers are affected?
* Which workers are exempt?
* Which managers and teams are involved?
* Which systems support the changed process?
* Which documents require review or update?
* Which training requirement applies?
* Which customer commitments may require review?
* Why was each object classified as affected?
* What deterministic action is proposed?
* What evidence supports the conclusion?

The result should be reproducible from the same source data and remain unchanged after it is persisted.

⸻

Version 0.1 success criteria

The first release is successful when a reviewer can create the demonstration assessment and receive an accurate, understandable result containing:

* affected and unaffected workers;
* applicable exceptions;
* affected managers and teams;
* related systems;
* related documentation;
* training impacts;
* affected customer commitments;
* unresolved questions;
* proposed actions;
* supporting evidence;
* stable reason codes;
* ordered relationship paths.

The release must also demonstrate that:

* equivalent inputs produce equivalent semantic results;
* relevant source-data changes produce a new result;
* earlier assessments remain immutable;
* proposed actions remain unexecuted;
* integration tests pass against PostgreSQL;
* a reviewer can explain why every seeded object was included or excluded.

⸻

Planned capability progression

Deterministic impact discovery

ChangeOps first establishes a trusted enterprise context using normalized data, explicit relationships, and deterministic rules.

This layer determines what is factually affected.

AI-assisted interpretation and planning

Milestone 2 accepts unstructured policy text and uses AI to:

* extract a typed policy representation;
* identify ambiguity;
* request clarification;
* synthesize deterministic findings;
* produce an evidence-backed change plan.

The deterministic impact engine remains authoritative for known rules and enterprise relationships.

Human review and approval

Milestone 3 allows reviewers to:

* inspect evidence;
* edit recommendations;
* approve actions;
* reject actions;
* request clarification;
* record decision rationale.

Governed execution

Milestone 4 explicitly executes only the supported training-assignment command against a simulated
Learning System. Approval alone never executes an action; unsupported approvals remain visible.

Portfolio-grade operation

The final public application will add:

* a usable end-to-end interface;
* authentication and authorization;
* cloud deployment;
* infrastructure as code;
* observability;
* evaluation datasets;
* CI/CD;
* security and operational controls.

⸻

Capstone and possible expansion capabilities

Later releases may add:

* simulated HR, CRM, learning, work-management, and knowledge-system MCP servers;
* additional justified execution operations and enterprise adapters;
* role-based permissions;
* live model-quality datasets and reporting;
* adversarial tests;
* AWS deployment;
* Terraform infrastructure;
* CI/CD;
* observability;
* usage and cost controls;
* multi-tenant public demonstration environments.

These capabilities should be introduced only when the product milestone contains a problem that requires them.

⸻

Non-goals

ChangeOps is not:

* a general-purpose chatbot;
* a generic agent platform;
* a fully autonomous decision-maker;
* a replacement for legal, HR, compliance, or operational review;
* a system permitted to make high-impact employment decisions;
* a real Workday or Salesforce integration in its public demonstration form;
* a system that treats LLM output as authoritative enterprise data;
* a generalized graph database or configuration-management platform;
* a complete replica of an enterprise software suite;
* a system allowed to execute consequential actions without approval.

⸻

Product boundary

ChangeOps is responsible for:

* organizing evidence;
* applying known rules;
* discovering enterprise impacts;
* surfacing uncertainty;
* proposing actions;
* coordinating review;
* governing execution;
* preserving traceability.

Human reviewers remain responsible for:

* resolving material ambiguity;
* assessing legal or policy implications;
* approving consequential actions;
* rejecting inappropriate recommendations;
* accepting accountability for final decisions.
