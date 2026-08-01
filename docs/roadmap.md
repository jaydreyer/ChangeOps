ChangeOps Delivery Roadmap

Roadmap Principles

ChangeOps is built as a sequence of usable vertical slices.

Each milestone must:

* add a demonstrable product capability;
* preserve the behavior and tests of earlier milestones;
* introduce technology only when the product problem requires it;
* prefer deterministic code over probabilistic AI where rules are known;
* preserve evidence, explainability, and auditability;
* keep consequential actions under human control.

The intended product progression is:

Deterministic assessment
    ↓
Enterprise impact discovery
    ↓
AI-assisted interpretation and planning
    ↓
Human approval
    ↓
Enterprise execution
    ↓
Portfolio-grade operations

⸻

Milestone 0 — Deterministic Impact Assessment

Product capability

Assess a structured policy change against seeded enterprise data and produce a persisted, evidence-backed impact assessment.

Proves

* normalized enterprise data can support policy analysis;
* known policy rules can be evaluated deterministically;
* affected workers and trips can be identified;
* findings include supporting evidence;
* proposed actions can be generated without executing them;
* assessments can be stored as immutable snapshots.

Technologies

* Python
* FastAPI
* PostgreSQL
* SQLAlchemy
* Alembic
* Docker
* pytest

Not included

* LLMs
* LangChain
* LangGraph
* frontend
* AWS
* MCP
* approvals
* action execution

Exit criteria

* the golden international-travel scenario passes;
* assessments persist across restarts;
* findings, evidence, and proposed actions are correct;
* assessment results use stable ordering;
* source changes do not mutate previously persisted assessments;
* integration tests pass against PostgreSQL.

⸻

Milestone 1 — Enterprise Impact Discovery

Product capability

Expand a worker-and-trip assessment into a deterministic view of the enterprise resources and obligations affected by the policy change.

The assessment should identify impacts across:

* people;
* teams;
* systems;
* documentation;
* training;
* customer commitments.

Proves

* operational changes can propagate across multiple enterprise domains;
* enterprise relationships can be modeled explicitly;
* affected and unaffected objects can be distinguished;
* every impact can be traced through a deterministic relationship path;
* cross-domain impact analysis can remain reproducible and explainable;
* AI is not required for facts already represented by structured data and known rules.

Technologies added

No major framework is added.

Milestone 1 extends the existing:

* PostgreSQL domain model;
* deterministic Python analyzers;
* FastAPI response models;
* immutable assessment persistence;
* automated test suite.

Architectural boundary

Milestone 1 answers:

Given a validated structured policy change, what enterprise objects are affected?

It does not interpret unstructured policy text and does not generate speculative recommendations.

The analyzer uses:

* persisted enterprise relationships;
* explicit dependency mappings;
* deterministic impact rules;
* stable reason codes;
* ordered evidence paths.

Not included

* LLMs
* LangChain
* LangGraph
* embeddings or vector search
* agents
* MCP
* live enterprise integrations
* approval workflows
* action execution
* generalized graph-database infrastructure

Exit criteria

* the golden scenario identifies affected people, teams, systems, documents, training, and customer commitments;
* at least one seeded object in each applicable domain remains unaffected;
* each impact includes evidence, a stable reason code, and an ordered relationship path;
* deterministic proposed actions remain unexecuted;
* repeated assessments with equivalent inputs produce equivalent semantic results;
* source changes produce new assessments without modifying historical snapshots;
* unit, integration, and API contract tests pass.

⸻

Milestone 2 — AI-Assisted Change Planning

Status: backend complete. The API workflow and quality gates satisfy this milestone's backend exit
criteria. The integrated reviewer UI remains deferred to Milestone 5, where Next.js is
intentionally introduced.

Product capability

Accept unstructured policy text, convert it into a validated structured change, run deterministic enterprise impact discovery, and produce an evidence-backed change plan.

This is the first AI milestone.

Proves

* policy text can be converted into typed domain input;
* uncertain or ambiguous interpretations can be surfaced rather than hidden;
* deterministic analysis can operate on AI-extracted rules;
* AI can synthesize findings into recommendations without becoming the source of truth;
* a multi-step AI workflow can pause, resume, retry, and preserve state;
* every recommendation can be traced to policy text and deterministic evidence.

Technologies added

* LLM provider
* LangChain
* structured model output
* LangGraph
* persisted graph state
* tracing
* prompt and workflow evaluation support

Expected workflow

1. ingest policy text;
2. extract structured policy claims;
3. validate schema and business constraints;
4. identify ambiguities or missing information;
5. pause for clarification when required;
6. resume with approved clarification;
7. run deterministic enterprise impact discovery;
8. collect supporting evidence;
9. generate an evidence-backed change plan;
10. persist the workflow result and recommendations.

Architectural boundary

AI is responsible for:

* interpreting unstructured language;
* identifying ambiguity;
* synthesizing evidence;
* drafting recommendations and explanations.

Deterministic code remains responsible for:

* validating known business constraints;
* resolving persisted enterprise relationships;
* applying policy rules;
* determining factual impacts;
* enforcing allowed action types;
* calculating fingerprints and stable identifiers.

The LLM must not directly write to enterprise systems or approve its own recommendations.

Not included

* execution of proposed actions;
* approval of consequential actions;
* MCP tools;
* live enterprise APIs;
* autonomous system changes.

Exit criteria

* policy text produces a validated typed policy representation;
* invalid or unsupported extraction fails safely;
* ambiguous policy text pauses the workflow;
* approved clarification resumes the same persisted workflow;
* the golden policy produces the expected structured representation;
* deterministic impacts remain stable for equivalent structured rules;
* each recommendation cites policy evidence and deterministic impact evidence;
* graph state, retries, failures, and transitions are visible;
* no consequential action executes automatically.
* pull requests protect deterministic tests, PostgreSQL integration tests, migrations, lint,
  formatting, and offline AI evaluations;
* a manually triggered live-provider smoke verifies provider contracts without adding live calls
  to ordinary CI.

⸻

Milestone 3 — Human Review and Approval

Status: in progress. PR 1 implements item-level review persistence and deterministic terminal
decisions. PR 2 implements the separate durable assessment-level approval run, stable membership,
deterministic interruption/resume, count reconciliation, and transition audit history. The
reviewer interface remains a separate later slice.

Product capability

Allow reviewers to inspect, edit, approve, reject, or defer proposed actions before anything consequential is executed.

Proves

* humans remain accountable for consequential decisions;
* recommendations can be reviewed with their supporting evidence;
* proposed actions can be changed without losing their original history;
* approval decisions can pause and resume the workflow;
* reviewer identity, comments, and decisions can be audited.

Technologies added

* approval data model
* item-level review API workflow
* role-aware authorization sufficient for the demonstration

Planned slices

* PR 1 — action review and decision foundation;
* PR 2 — durable approval interruption and resume (implemented);
* PR 3 — focused reviewer interface.

Approval behavior

Reviewers must be able to:

* inspect the original policy evidence;
* inspect deterministic findings;
* inspect AI-generated recommendations;
* edit proposed action parameters;
* approve an action;
* reject an action;
* request revision or clarification;
* record decision rationale.

Approval applies to specific proposed actions, not to an undifferentiated assessment as a whole.

Not included

* execution against enterprise systems;
* automatic approval;
* bulk approval without item-level visibility;
* unrestricted production authorization.

Exit criteria

* no consequential action can advance without an explicit approval decision;
* rejected actions cannot execute;
* edited actions preserve both original and approved values;
* approval interruption survives process restart;
* the same workflow resumes after a decision;
* every decision records actor, timestamp, rationale, evidence, and resulting status;
* authorization rules prevent unauthorized approval.

⸻

Milestone 4 — Simulated Enterprise Execution

Product capability

Execute approved actions against simulated enterprise systems and record the result as part of the audit trail.

Proves

* approved recommendations can become controlled operational changes;
* enterprise-style tool calls can be isolated behind stable interfaces;
* execution can be idempotent;
* partial failures can be handled without duplicating successful work;
* tool inputs and outputs can be audited;
* execution remains subordinate to approval and permissions.

Technologies added

* MCP
* simulated enterprise-system APIs
* execution adapters
* idempotency keys
* retry and failure handling
* execution audit events

Simulated systems

The demonstration may include focused simulations for:

* Workday-style worker data;
* learning-management assignments;
* Jira-style operational tasks;
* Salesforce-style customer commitments;
* knowledge-system document updates.

Only implement actions required by the golden scenario.

Do not build complete replicas of these products.

Expected execution flow

1. load an approved action;
2. verify approval and authorization;
3. validate the action against the current system state;
4. generate or reuse an idempotency key;
5. call the appropriate MCP tool;
6. capture the request and response;
7. update execution status;
8. record audit events;
9. surface partial or failed execution for review.

Exit criteria

* no action executes without approval;
* unauthorized execution is blocked;
* repeated execution does not duplicate effects;
* successfully completed actions are not repeated after retry;
* failed actions expose actionable error information;
* every action records actor, evidence, approval, request, result, and status;
* the golden scenario updates the expected simulated systems.

⸻

Milestone 5 — Portfolio Application and Production Readiness

Product capability

Deliver ChangeOps as a usable, deployable, observable end-to-end application that demonstrates realistic enterprise AI engineering.

Proves

* users can move through the complete change-management workflow;
* infrastructure can be created reproducibly;
* application behavior is observable;
* permissions are enforced across the workflow;
* the public demonstration reflects enterprise constraints;
* AI quality and deterministic correctness can be evaluated separately.

Technologies added

* Next.js
* TypeScript
* AWS
* Terraform
* deployment CI/CD
* authentication
* authorization
* observability
* production-oriented evaluation tooling

User experience

The portfolio application should support:

* submitting a policy change;
* reviewing extracted policy rules;
* resolving ambiguities;
* viewing enterprise impacts;
* reviewing supporting evidence;
* inspecting proposed actions;
* approving, rejecting, or editing actions;
* viewing execution results;
* reviewing the complete audit history.

The interface should explain the workflow rather than hide it behind a generic chatbot.

Likely AWS architecture

* ECS Fargate for the API and workflow service;
* RDS PostgreSQL;
* ECR;
* Application Load Balancer;
* Secrets Manager or Parameter Store;
* CloudWatch;
* S3 where document storage is required;
* a suitable frontend deployment target for Next.js.

The final deployment architecture should be selected based on operating cost, maintainability, and demonstration needs rather than maximum service count.

Production-readiness scope

* authentication and role-based authorization;
* secrets management;
* structured logging;
* metrics and traces;
* workflow and tool-call observability;
* database backup and migration strategy;
* deployment CI/CD beyond the repository's existing merge-quality gates;
* security checks;
* evaluation datasets;
* deterministic regression tests;
* LLM extraction and recommendation evaluations;
* documented operational limitations.

Exit criteria

* the golden scenario works end to end through the user interface;
* infrastructure is reproducible from Terraform;
* deployment occurs through CI/CD;
* authentication and authorization protect sensitive actions;
* logs and traces connect user requests, workflow runs, assessments, approvals, and executions;
* deterministic and AI evaluations run automatically;
* the public demo contains no real employer, worker, or customer data;
* the README and architecture documentation accurately describe the deployed system;
* a reviewer can understand the product, architecture, tradeoffs, and safety controls without source-code archaeology.

⸻

Deployment Sequencing

Deployment should occur incrementally rather than being deferred entirely until Milestone 5.

Recommended sequence:

* local Docker Compose through Milestone 1;
* minimal non-production cloud deployment during or immediately after Milestone 2;
* persistent hosted workflow and approval environment by Milestone 3;
* integrated simulated-tool environment by Milestone 4;
* portfolio-grade infrastructure, security, observability, and CI/CD in Milestone 5.

The minimal deployment should validate deployability without prematurely building full production infrastructure.

⸻

Cross-Cutting Requirements

The following requirements apply to every milestone.

Explainability

Every material conclusion must be traceable to:

* source data;
* policy evidence;
* a deterministic rule;
* an AI workflow step;
* or a human decision.

Immutability

Completed assessments, recommendations, decisions, and execution records must preserve their historical state.

Determinism

Known business rules, identifiers, sorting, fingerprints, validation, and permission checks must be implemented deterministically.

Human control

No consequential action may be executed without explicit human approval.

Evaluation

Each milestone must add tests or evaluations appropriate to its risks:

* deterministic unit and integration tests for rules;
* golden datasets for policy extraction;
* workflow tests for pause and resume;
* approval authorization tests;
* idempotency and failure tests for execution;
* end-to-end and observability checks for deployment.

Scope discipline

Each milestone must implement only the records, integrations, and workflows needed for the golden scenario.

Enterprise realism does not require recreating an entire enterprise software suite.

⸻

Technology Introduction Rule

A technology enters the project only when the milestone contains a product or architectural problem that requires it.

Examples:

* PostgreSQL enters when normalized enterprise data and immutable assessments must persist.
* LangChain enters when unstructured policy text must be converted into validated typed input and evidence-backed recommendations.
* LangGraph enters when the workflow requires branching, durable state, retries, interruption, clarification, and resume.
* MCP enters when approved actions must invoke enterprise-style tools through a governed interface.
* Next.js enters when reviewers need a usable end-to-end workflow.
* AWS enters once a stable application slice exists and deployment risk needs to be addressed.
* Terraform enters when the hosted environment must be reproducible.

Technologies should not be introduced solely to increase the number of tools represented in the repository.
