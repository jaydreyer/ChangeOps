# ChangeOps Demonstration Scenario

## Purpose

This document defines the initial demonstration scenario for ChangeOps.

It serves as the reference case for Milestone 0: Deterministic Impact-Assessment Foundation. The seeded data, analysis rules, expected findings, and expected recommendations in this document should be treated as the golden test case for the first implementation.

The purpose of the scenario is not to model every possible enterprise policy change. It is to prove that ChangeOps can:

1. represent a policy change;
2. evaluate the change against enterprise data;
3. identify affected and unaffected people;
4. explain why each person is or is not affected;
5. cite the evidence supporting each conclusion;
6. recommend appropriate follow-up actions;
7. persist and retrieve the completed assessment.

Milestone 0 uses deterministic rules. It does not use an LLM, LangGraph, MCP, external enterprise systems, or automated execution.

---

## Fictional Organization

### Organization

**Name:** Acme Global Manufacturing  
**Industry:** Manufacturing  
**Headquarters:** Minneapolis, Minnesota, United States

Acme Global Manufacturing employs workers in several countries and regularly sends employees and contractors on international business trips.

All names, records, policies, and systems in this scenario are fictional.

---

## Policy Change

### Policy title

International Business Travel Approval and Security Training

### Policy owner

Corporate Security and Global Travel

### Effective date

September 1, 2026

### Policy text

Effective September 1, 2026, U.S.-based employees and contractors traveling internationally for business must complete the International Travel Security course before departure.

Manager approval is required before any nonrefundable international travel is booked.

Travel booked before September 1, 2026 is exempt from the new manager-approval requirement. However, travelers departing on or after September 1, 2026 must still complete the International Travel Security course before departure.

Travel between the United States and Canada is excluded from this policy.

### Intended interpretation

For Milestone 0, the following deterministic interpretations apply:

- A worker is considered U.S.-based when the worker’s assigned work country is the United States.
- Both employees and contractors may be affected.
- International travel means business travel from the United States to a country other than the United States or Canada.
- Travel to Canada is excluded.
- The security-course requirement applies when the departure date is on or after September 1, 2026.
- The manager-approval requirement applies when:
  - the departure date is on or after September 1, 2026;
  - the destination is covered by the policy; and
  - the travel was not booked before September 1, 2026.
- A trip booked before September 1, 2026 is exempt only from the new manager-approval requirement.
- A preexisting booking does not exempt the traveler from the security-course requirement.

These interpretations are implementation rules for the first deterministic slice. A later AI-enabled release may extract, classify, and flag uncertainty in these rules directly from policy text.

---

## Seeded Workers and Trips

### 1. Sarah Johnson

**Worker ID:** `worker-sarah-johnson`  
**Worker type:** Employee  
**Department:** Human Resources  
**Manager:** Mike Wilson  
**Assigned work country:** United States  
**Destination:** France  
**Departure date:** September 15, 2026  
**Booking date:** Not yet booked  
**Security course status:** Not completed

#### Expected result

Sarah is affected by both requirements.

#### Expected reasoning

- Sarah is a U.S.-based employee.
- France is an international destination covered by the policy.
- Her departure is after the September 1 effective date.
- Her trip has not been booked, so it is not exempt from the manager-approval requirement.
- She has not completed the required security course.

#### Expected recommendations

- Require manager approval before nonrefundable booking.
- Assign the International Travel Security course.
- Require course completion before departure.

---

### 2. Marcus Lee

**Worker ID:** `worker-marcus-lee`  
**Worker type:** Contractor  
**Department:** Information Technology  
**Manager:** Anita Patel  
**Assigned work country:** United States  
**Destination:** Japan  
**Departure date:** October 2, 2026  
**Booking date:** Not yet booked  
**Security course status:** Completed

#### Expected result

Marcus is affected by the manager-approval requirement but does not require a new course assignment.

#### Expected reasoning

- Marcus is a U.S.-based contractor.
- Contractors are included in the policy.
- Japan is an international destination covered by the policy.
- His departure is after the effective date.
- His trip has not been booked, so manager approval is required before nonrefundable booking.
- He has already completed the security course.

#### Expected recommendations

- Require manager approval before nonrefundable booking.
- Do not assign a duplicate security course.
- Confirm that the existing course completion remains valid through the departure date.

For Milestone 0, the course completion should be treated as valid. Course expiration logic is outside the scope of this slice.

---

### 3. Elena García

**Worker ID:** `worker-elena-garcia`  
**Worker type:** Employee  
**Department:** Finance  
**Manager:** Carlos Martín  
**Assigned work country:** Spain  
**Destination:** United States  
**Departure date:** September 20, 2026  
**Booking date:** August 25, 2026  
**Security course status:** Not completed

#### Expected result

Elena is not affected.

#### Expected reasoning

- Elena is assigned to Spain and is therefore not U.S.-based.
- The policy applies only to U.S.-based employees and contractors.
- Her travel should not be included in the affected population.

#### Expected recommendations

No action.

---

### 4. David Miller

**Worker ID:** `worker-david-miller`  
**Worker type:** Employee  
**Department:** Sales  
**Manager:** Jennifer Brooks  
**Assigned work country:** United States  
**Destination:** Germany  
**Departure date:** September 10, 2026  
**Booking date:** August 20, 2026  
**Security course status:** Not completed

#### Expected result

David is affected by the security-course requirement but exempt from the new manager-approval requirement.

#### Expected reasoning

- David is a U.S.-based employee.
- Germany is a covered international destination.
- His departure is after the effective date.
- His travel was booked before September 1, so the booking is exempt from the new manager-approval requirement.
- The booking exemption does not apply to the security-course requirement.
- He has not completed the required course.

#### Expected recommendations

- Assign the International Travel Security course.
- Require course completion before departure.
- Do not require retroactive manager approval for the existing booking.

---

### 5. Priya Shah

**Worker ID:** `worker-priya-shah`  
**Worker type:** Employee  
**Department:** Product Management  
**Manager:** Robert Chen  
**Assigned work country:** United States  
**Destination:** Canada  
**Departure date:** September 18, 2026  
**Booking date:** Not yet booked  
**Security course status:** Not completed

#### Expected result

Priya is not affected.

#### Expected reasoning

- Priya is a U.S.-based employee.
- Her departure occurs after the effective date.
- However, travel between the United States and Canada is explicitly excluded from the policy.

#### Expected recommendations

No action.

---

### 6. Thomas Green

**Worker ID:** `worker-thomas-green`  
**Worker type:** Employee  
**Department:** Operations  
**Manager:** Linda Evans  
**Assigned work country:** United States  
**Destination:** Mexico  
**Departure date:** August 20, 2026  
**Booking date:** August 1, 2026  
**Security course status:** Not completed

#### Expected result

Thomas is not affected.

#### Expected reasoning

- Thomas is a U.S.-based employee.
- Mexico would otherwise be a covered international destination.
- His departure occurs before the September 1 effective date.
- Neither requirement applies to this trip.

#### Expected recommendations

No action.

---

## Seeded Supporting Evidence

The analysis must not return conclusions without evidence. Each finding should reference one or more persisted evidence records.

### Worker evidence

Each worker record should provide:

- worker ID;
- worker type;
- assigned work country;
- department;
- manager.

### Trip evidence

Each trip record should provide:

- traveler ID;
- origin country;
- destination country;
- departure date;
- booking date;
- booking status.

### Training evidence

Each training record should provide:

- worker ID;
- course identifier;
- completion status;
- completion date, when applicable.

### Policy evidence

The policy record should provide:

- policy ID;
- policy title;
- policy version;
- effective date;
- policy text;
- the relevant policy section or rule supporting each finding.

---

## Expected Assessment Summary

The completed impact assessment should produce the following summary.

### Affected workers

- Sarah Johnson
- Marcus Lee
- David Miller

### Unaffected workers

- Elena García
- Priya Shah
- Thomas Green

### Required manager approvals

- Sarah Johnson
- Marcus Lee

### Required security-course assignments

- Sarah Johnson
- David Miller

## Reviewer lifecycle fixtures

The browser-facing lifecycle is verified with focused frontend and PostgreSQL integration fixtures,
not a persistent scenario-management feature:

- the landing page explains the governed journey before analysis begins, and the analysis page
  leads with reviewer questions while retaining authoritative technical detail in disclosures;
- the golden accepted extraction completes without clarification;
- a conflicting pre-effective booking value pauses the same run for one typed `true`
  clarification, then resumes it;
- an unsupported policy family stops before assessment and leaves future steps unavailable;
- malformed or provider-failed extraction persists a stable failure code and cannot continue;
- interpretation provider failure leaves the deterministic assessment intact and retryable;
- completed approval remains separate from execution eligibility and command preparation;
- executing the same supported training command twice creates one assignment plus `succeeded` and
  `already_applied` history.

Run `make demo-reset` before a reviewer session. The command preserves all fictional source records
described above and removes prior generated lifecycle records so the landing page starts with no
stale run or approval history.

### Already compliant with security training

- Marcus Lee

### Exempt from new manager approval due to booking date

- David Miller

---

## Expected Findings

The assessment should contain findings equivalent to the following.

### Finding 1: Sarah Johnson requires manager approval

**Finding type:** Worker impact  
**Severity:** Action required

Sarah Johnson’s planned trip to France is covered by the policy. The trip has not been booked, so manager approval is required before any nonrefundable booking.

**Evidence references:**

- Sarah Johnson worker record
- Sarah Johnson France trip record
- Policy effective-date rule
- Policy manager-approval rule
- Policy destination-scope rule

---

### Finding 2: Sarah Johnson requires security training

**Finding type:** Training impact  
**Severity:** Action required

Sarah Johnson is scheduled to depart after the policy effective date and has not completed the International Travel Security course.

**Evidence references:**

- Sarah Johnson worker record
- Sarah Johnson France trip record
- Sarah Johnson training record
- Policy security-course rule

---

### Finding 3: Marcus Lee requires manager approval

**Finding type:** Worker impact  
**Severity:** Action required

Marcus Lee is a U.S.-based contractor with planned business travel to Japan after the effective date. His trip has not been booked, so manager approval is required before nonrefundable booking.

**Evidence references:**

- Marcus Lee worker record
- Marcus Lee Japan trip record
- Policy worker-type rule
- Policy manager-approval rule
- Policy destination-scope rule

---

### Finding 4: Marcus Lee already satisfies the training requirement

**Finding type:** Compliance confirmation  
**Severity:** Informational

Marcus Lee has already completed the International Travel Security course. No duplicate assignment is needed.

**Evidence references:**

- Marcus Lee training record
- Policy security-course rule

---

### Finding 5: David Miller requires security training

**Finding type:** Training impact  
**Severity:** Action required

David Miller is departing for Germany after the effective date and has not completed the required security course.

**Evidence references:**

- David Miller worker record
- David Miller Germany trip record
- David Miller training record
- Policy security-course rule

---

### Finding 6: David Miller is exempt from the new approval requirement

**Finding type:** Policy exception  
**Severity:** Informational

David Miller’s travel was booked before September 1, 2026. The trip is therefore exempt from the new manager-approval requirement.

**Evidence references:**

- David Miller Germany trip record
- Policy booking-date exception

---

### Finding 7: Existing travel guidance is outdated

**Finding type:** Documentation impact  
**Severity:** Action required

The existing international-travel guidance does not mention the new manager-approval requirement, the security-course requirement, the effective date, or the Canada exclusion.

**Evidence references:**

- Current international-travel knowledge article
- New policy record

This finding may be represented in the data model during Milestone 0 even if full documentation analysis is deferred to a later milestone.

---

## Expected Recommended Actions

The system should recommend actions but must not execute them during Milestone 0.

### Action 1: Obtain manager approval for Sarah Johnson

**Action type:** Approval request recommendation  
**Target:** Sarah Johnson’s manager  
**Related worker:** Sarah Johnson  
**Execution status:** Not executed

Recommended outcome:

Obtain documented manager approval before any nonrefundable travel is booked.

---

### Action 2: Assign security training to Sarah Johnson

**Action type:** Training assignment recommendation  
**Target:** Sarah Johnson  
**Execution status:** Not executed

Recommended outcome:

Assign the International Travel Security course and require completion before September 15, 2026.

---

### Action 3: Obtain manager approval for Marcus Lee

**Action type:** Approval request recommendation  
**Target:** Marcus Lee’s manager  
**Related worker:** Marcus Lee  
**Execution status:** Not executed

Recommended outcome:

Obtain documented manager approval before any nonrefundable travel is booked.

---

### Action 4: Assign security training to David Miller

**Action type:** Training assignment recommendation  
**Target:** David Miller  
**Execution status:** Not executed

Recommended outcome:

Assign the International Travel Security course and require completion before September 10, 2026.

---

### Action 5: Update international-travel guidance

**Action type:** Documentation update recommendation  
**Target:** International Travel Knowledge Article  
**Execution status:** Not executed

Recommended outcome:

Update the travel guidance to include:

- the September 1, 2026 effective date;
- the U.S.-based worker scope;
- inclusion of employees and contractors;
- the security-course requirement;
- the manager-approval requirement;
- the pre-effective-date booking exception;
- the Canada exclusion.

---

## Existing Knowledge Article

### Article title

Booking International Business Travel

### Article ID

`kb-international-travel-booking`

### Current article text

Employees planning international business travel should book through the approved corporate travel provider. Travelers should confirm passport and visa requirements before departure and submit expenses through the standard expense process.

### Expected documentation impact

This article conflicts with the new operating requirements because it does not instruct covered travelers to:

- obtain manager approval before nonrefundable booking;
- complete the International Travel Security course;
- account for the September 1 effective date;
- apply the preexisting-booking exception;
- exclude travel to Canada.

The article is not factually false, but it is incomplete and would create operational risk if left unchanged.

---

## Expected Unresolved Questions

Milestone 0 may store unresolved questions even though deterministic answers are supplied for implementation.

The expected unresolved questions are:

1. How is “U.S.-based” officially determined in the source HR system?
2. Does the policy apply to workers temporarily assigned to the United States?
3. How long does the International Travel Security course remain valid?
4. Who records and stores manager approval?
5. Does approval apply per trip, per booking, or per traveler?
6. Does a refundable reservation require approval before it becomes nonrefundable?
7. Which team owns updates to the travel knowledge article?
8. Are any countries subject to stricter security-review requirements outside this policy?

For Milestone 0, these questions must not block the deterministic demonstration scenario.

---

## Deterministic Analysis Rules

The first implementation should apply explicit rules similar to the following.

### Rule 1: Worker scope

A worker is in scope when:

- assigned work country equals `US`; and
- worker type is `employee` or `contractor`.

### Rule 2: Destination scope

A trip is in scope when:

- origin country equals `US`;
- destination country is not `US`; and
- destination country is not `CA`.

### Rule 3: Effective-date scope

The policy applies when:

- departure date is on or after `2026-09-01`.

### Rule 4: Manager approval

Manager approval is required when:

- the worker is in scope;
- the destination is in scope;
- the effective-date rule applies; and
- the booking date is absent or is on or after `2026-09-01`.

### Rule 5: Security training

Security training is required when:

- the worker is in scope;
- the destination is in scope;
- the effective-date rule applies; and
- no completed training record exists.

### Rule 6: Booking exception

A trip booked before `2026-09-01` is exempt from the new manager-approval requirement.

The booking exception does not remove the security-training requirement.

---

## Expected API-Level Outcome

The precise API design may be proposed during implementation, but the persisted assessment must support retrieval of:

- assessment ID;
- policy-change ID;
- assessment status;
- assessment creation timestamp;
- affected workers;
- unaffected workers or exclusion results;
- findings;
- evidence references;
- recommended actions;
- unresolved questions.

A recommended action must be clearly marked as unexecuted.

Milestone 0 should not represent a recommendation as approved, rejected, or pending approval because no approval workflow exists yet.

---

## Golden Scenario Assertions

Automated tests should verify at least the following:

1. Exactly three workers are classified as affected.
2. Sarah Johnson requires manager approval.
3. Sarah Johnson requires security training.
4. Marcus Lee requires manager approval.
5. Marcus Lee does not receive a duplicate training recommendation.
6. David Miller is exempt from manager approval.
7. David Miller still requires security training.
8. Elena García is excluded because she is not U.S.-based.
9. Priya Shah is excluded because travel to Canada is out of scope.
10. Thomas Green is excluded because his departure occurs before the effective date.
11. Every action-producing finding contains evidence references.
12. Every recommended action remains unexecuted.
13. The completed assessment can be retrieved after the application restarts.
14. Running the seed process more than once does not create duplicate records.
15. Running the deterministic assessment repeatedly produces equivalent results.

---

## Out of Scope for This Scenario

The following capabilities are intentionally excluded from Milestone 0:

- policy document upload;
- PDF or document parsing;
- LLM-based policy extraction;
- LangGraph orchestration;
- semantic search;
- vector databases;
- automatic ambiguity resolution;
- user authentication;
- role-based access control;
- human approval workflows;
- action execution;
- Workday integration;
- learning-system integration;
- travel-system integration;
- Jira integration;
- Salesforce integration;
- MCP servers;
- notifications;
- production deployment;
- AWS infrastructure;
- Terraform;
- frontend user experience.

These capabilities may be added in later vertical slices after the deterministic foundation is working and tested.

---

## Definition of Success

The demonstration scenario is successful when a developer can run the application, create an impact assessment for the seeded policy, and retrieve a persisted result that correctly:

- identifies Sarah Johnson, Marcus Lee, and David Miller as affected;
- explains the different requirements that apply to each person;
- excludes Elena García, Priya Shah, and Thomas Green for the correct reasons;
- links every material conclusion to evidence;
- recommends appropriate actions without executing them;
- produces the same result consistently across repeated runs.

---

## Milestone 1 Enterprise Extension

Milestone 1 preserves every worker result, finding, and recommendation above and adds the following
fictional enterprise context.

### Teams and managers

- People Operations, managed by Mike Wilson, contains Sarah Johnson.
- Technology Operations, managed by Anita Patel, contains Marcus Lee.
- Customer Delivery, managed by Jennifer Brooks, contains David Miller.
- Domestic Operations contains the unaffected workers and remains unaffected.

Mike Wilson and Anita Patel require approval review. Jennifer Brooks requires booking-exception
review for David Miller. The first three teams are operationally affected because each contains one
directly affected worker.

### Systems

- Acme Travel Request is affected because it supports changed approval handling.
- Acme Learning Hub is affected because completion verification or assignment is required.
- Acme Expense remains unaffected because no explicit policy dependency or resulting rule connects
  it to the change.

### Documents

- International Business Travel Policy requires update.
- Booking International Business Travel requires update.
- Manager Travel Approval Guide requires review.
- Expense Submission Guide remains unaffected.

Document impacts come only from explicit typed policy dependencies.

### Training

The International Travel Security course is an explicit course entity connected to the policy.
Sarah Johnson and David Miller have worker-specific incomplete-training impacts. Marcus Lee's valid
completion prevents an incomplete-training impact and duplicate assignment.

### Customer commitments

Sarah Johnson is required for the Northwind Renewable Energy on-site delivery from September 14
through September 18. Her September 15 affected trip overlaps that period, so the commitment
requires review.

Marcus Lee's Contoso Retail assignment does not overlap his October 2 departure and remains
unaffected.

### Expected enterprise assessment

The seeded assessment returns 18 affected enterprise impacts:

- 6 people impacts: 3 workers and 3 managers;
- 3 team impacts;
- 2 system impacts;
- 3 document impacts;
- 3 training impacts: 1 course and 2 incomplete worker requirements;
- 1 customer-commitment impact.

Every impact contains a stable reason code, evidence references, a stable sort key, and an ordered
relationship path. The complete response contains the four Milestone 0 worker actions plus nine
cross-domain actions. All 13 actions remain `not_executed`.

## Milestone 5A Policy Comparison Extension

The ordinary source catalog now contains a second policy record:

**Title:** Proposed International Business Travel Revision

**Effective date:** October 1, 2026

**Source identity:** `policy-international-travel-proposed-2026-10`

The proposed source keeps the existing international-travel family, U.S. work-location scope,
manager-approval exemption contract, and International Travel Security course. It makes three
bounded semantic changes supported by the current typed schema:

- effective date changes from September 1 to October 1, 2026;
- contractor coverage is removed, leaving employees;
- Mexico is added to the excluded destination countries alongside the United States and Canada.

The seed contains neither policy's accepted extraction, analysis run, assessment, nor comparison.
The reviewer analyzes both through the product. Comparison remains unavailable until each selected
source has a completed run whose authoritative attempt contains accepted typed rules and no
pending clarification.

The deterministic comparison then returns exactly three ordered differences:

1. `effective_date` — `modified` — `POLICY_EFFECTIVE_DATE_MODIFIED`;
2. `worker_scope.worker_types:contractor` — `removed` — `WORKER_TYPE_REMOVED`;
3. `trip_scope.excluded_destination_countries:MX` — `added` —
   `EXCLUDED_DESTINATION_ADDED`.

Each applicable semantic value includes provenance from its owning accepted extraction. An absent
collection member has no fabricated source span on that side. Every difference is operationally
material within the supported schema. Repeating the request reuses the immutable comparison.

This extension compares accepted policy obligations only. It does not compare assessments,
workers, enterprise impacts, proposed actions, approvals, commands, or execution results. The
product explicitly labels enterprise impact delta as not yet calculated.

`make demo-reset` removes generated comparisons and all existing workflow history while preserving
both policy sources and the rest of the fictional catalog.

## Milestone 5B Enterprise Impact Delta Extension

Both policy sources own business-equivalent seeded dependencies to the two active supporting
systems, three relevant documents, and the International Travel Security course. The dependency
rows have source-specific record identifiers, but the deterministic impact comparator never uses
those identifiers as enterprise-impact identity.

The demonstration executes both assessments against the same enterprise catalog state. Shared
worker, team, membership, trip, system, document, course, training, commitment, and assignment
facts remain unchanged between executions, and the source-specific policy dependency sets are
business-equivalent after excluding row and policy identifiers. An integration test enforces this
fixture invariant.

The resulting delta compares two authoritative persisted assessment outcomes. In a non-controlled
scenario where enterprise source facts changed between assessment executions, the delta would not
prove that policy changes alone caused every observed difference. Milestone 5B deliberately does
not generalize the demo invariant into enterprise catalog snapshot versioning.

The product presents this result in progressive layers: policies compared, accepted semantic
changes, a compact response-derived change summary, operational summary counts, and three visible
detail groups. Worker, finding, and enterprise-impact records are collapsed independently by
default. Their summaries retain classification, business title, reason code, and side status;
opening one record reveals full persisted explanations, evidence, relationship paths, stable
identity, and source-record lineage. Worker totals are explicitly labeled as worker-trip outcomes.

The proposed assessment deterministically classifies all six travelers as unaffected:

- Sarah Johnson is no longer affected because September 15 is before the proposed October 1
  effective date;
- Marcus Lee is no longer affected because contractor coverage was removed;
- David Miller is no longer affected because September 10 is before the proposed effective date;
- Elena García remains outside the U.S. worker-location scope;
- Priya Shah remains excluded because her destination is Canada;
- Thomas Green remains unaffected, with Mexico now explicitly excluded by the proposed policy.

No proposed worker finding is produced because no traveler is affected. The proposed assessment
retains four policy-level enterprise impacts: the three relevant document impacts and the required
International Travel Security course impact.

Creating the policy comparison also creates exactly one immutable enterprise impact delta with:

- 0 workers became affected;
- 3 workers no longer affected: David Miller, Marcus Lee, and Sarah Johnson, in stable identity
  order;
- 0 workers remained affected;
- 0 findings introduced;
- 6 findings disappeared;
- 0 enterprise impacts introduced;
- 14 enterprise impacts removed: 6 people, 3 teams, 2 systems, 2 worker-training requirements,
  and 1 customer commitment.

The three unchanged document impacts and unchanged course impact do not produce delta items.
Unaffected-to-unaffected worker results likewise do not produce items. Each worker item contains
both persisted assessment explanations and reason codes. Each finding or impact item contains the
applicable persisted explanation, reason code, evidence snapshots, and impact relationship path;
the absent side remains explicitly absent.

The delta fingerprint excludes comparison, assessment, finding, impact, and evidence UUIDs.
Repeated creation reuses both the semantic comparison and its one-to-one delta. Database triggers
reject delta or item update/delete and validate that every lineage record belongs to the correct
assessment side. `make demo-reset` removes both delta tables before comparisons while preserving
the two source policies and their dependency catalog.

The landing page labels the action **Compare policy versions** and explains that eligibility
requires accepted validated rules and completed assessments on both sides. Analysis creation does
not repeat its POST during recovery. UTC-stable client timestamps avoid server/browser hydration
differences; an interrupted response is reconciled with one authoritative entry read, after which
recovery controls only reopen the persisted run.

## Milestone 6 Jira Execution Extension

The proposed assessment contains one `operational_remediation` recommendation for the primary
International Business Travel Policy document. After the baseline/proposed comparison exists, the
reviewer approves that recommendation and completes all other decisions. Command preparation
creates one `jira.create_issue` command whose frozen human-readable description includes the three
semantic policy changes, document impact and deterministic reason, persisted evidence, command and
comparison IDs, baseline/proposed assessment IDs, and extraction lineage.

Explicit execution creates one Task in the configured Enterprise Change Management project. The
project's Task workflow places it in To Do. The workbench shows the returned Jira key and link plus
the immutable success result. Repeating execution returns `already_applied`, references the same
receipt, and performs no second Jira request. A mocked ambiguous availability failure demonstrates
the at-most-once safety rule: ChangeOps records the unavailable outcome and refuses to resend when
the first delivery may have succeeded.
