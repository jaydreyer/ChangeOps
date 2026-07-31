# ChangeOps: Initial Product Brief

## Product vision

ChangeOps helps organizations understand and safely act on changes that affect employees, policies, customers, documentation, and operational systems.

Instead of relying on employees to manually identify every downstream impact, ChangeOps gathers evidence from connected systems, produces an impact assessment, recommends actions, and routes consequential actions through human approval before execution.

## Initial use case

An HR or operations leader submits a new or revised employee policy.

ChangeOps:

1. Extracts the policy’s effective date, scope, requirements, and exceptions.
2. Identifies affected employee populations.
3. Finds related and conflicting documentation.
4. Identifies systems and workflows requiring changes.
5. Produces an evidence-backed impact assessment.
6. Recommends specific actions.
7. Requires human approval before executing write actions.
8. Records a complete audit trail.

## Initial demonstration scenario

Effective September 1, employees traveling internationally for company business must complete the International Travel Security course and obtain manager approval before making any nonrefundable booking. The policy applies to U.S.-based employees and contractors. Travel booked before the effective date is exempt.

## Target users

- HR operations leaders
- Legal and compliance teams
- Product operations teams
- Enterprise knowledge managers
- Internal-platform teams
- Change-management leaders

## Core product principles

- Evidence before action
- Human control over consequential decisions
- Deterministic rules where deterministic rules are sufficient
- Clear separation between recommendations and execution
- Full traceability
- Least-privilege access
- Recoverable workflows
- Explicit uncertainty
- No hidden autonomous writes

## Version 0.1 scope

Version 0.1 will:

- accept one policy-change request;
- extract structured policy details;
- identify affected employees and contractors;
- retrieve related knowledge articles;
- identify conflicting guidance;
- generate an impact assessment;
- recommend actions;
- display evidence supporting each major finding.

Version 0.1 will run locally and will not yet include production AWS infrastructure, generalized MCP integrations, or autonomous write actions.

## Success criteria

The first release is successful when a reviewer can submit the demonstration policy and receive an accurate, understandable assessment containing:

- affected populations;
- applicable exceptions;
- related documentation;
- documentation conflicts;
- affected systems;
- unresolved questions;
- recommended actions;
- supporting evidence.

## Future capabilities

Later releases may add:

- human approval and resumable workflows;
- simulated HR, CRM, work-management, and knowledge-system MCP servers;
- action execution;
- role-based permissions;
- evaluation datasets;
- adversarial tests;
- AWS deployment;
- Terraform infrastructure;
- CI/CD;
- observability;
- usage and cost controls;
- multi-tenant public demonstration environments.

## Non-goals

ChangeOps is not:

- a general-purpose chatbot;
- a fully autonomous decision-maker;
- a replacement for legal or HR review;
- a real Workday or Salesforce integration in its public demonstration form;
- a system allowed to make high-impact employment decisions.