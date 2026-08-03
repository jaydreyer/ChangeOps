# Milestone 5B — Enterprise Impact Delta

## Status

Complete.

This document records the implemented vertical slice after Milestone 5A. Repository code,
migrations, tests, and the golden demo scenario remain the source of truth.

## Product capability

Extend one deterministic policy comparison to answer:

> What operational consequences changed between the baseline and proposed accepted policies?

A reviewer can now identify:

- workers who became affected;
- workers who are no longer affected;
- workers who remain affected;
- findings introduced or disappeared;
- enterprise impacts introduced or removed;
- the persisted deterministic reason and evidence on every applicable side.

AI explanation remains deferred. AI does not calculate, match, classify, persist, or serialize the
delta.

## Smallest architectural extension

Repository inspection showed that the two immutable assessments already contain the authoritative
worker results, findings, impacts, evidence, paths, and proposed actions. A read projection could
recalculate differences but would not durably anchor the assessment pair or own an idempotent
historical artifact. Extending the Milestone 5A tables would mix accepted-rule and assessment
lifecycles and conflict with the comparison aggregate's narrow immutability contract.

The implemented design therefore adds one separate immutable aggregate:

```text
PolicyComparison
    1 ── 0..1 PolicyComparisonImpactDelta
                    1 ── * PolicyComparisonImpactDeltaItem
```

The aggregate is generated in the existing synchronous comparison transaction. No workflow graph,
background job, queue, provider call, or new dependency is required.

## Deterministic identity and classification

The pure comparator uses closed stable business identities:

- worker result: worker ID + trip ID;
- finding: worker ID + trip ID + finding type + severity + rule code;
- enterprise impact: domain + object type + source key + classification + reason code.

Database UUIDs never participate in matching. Source record UUIDs remain in the completed artifact
only as lineage references.

Worker classification:

- `became_affected`;
- `no_longer_affected`;
- `remained_affected`.

Finding classification:

- `introduced`;
- `disappeared`.

Enterprise-impact classification:

- `introduced`;
- `removed`.

Unaffected-to-unaffected worker results and unchanged findings or enterprise impacts are omitted.
Stable item ordering is workers, findings, then enterprise impacts; each category is ordered by
stable identity.

## Explainability and evidence

Each applicable side snapshots only persisted assessment records:

- record lineage ID;
- deterministic explanation;
- deterministic classification and reason codes;
- evidence record IDs, stable keys, source types, source IDs, labels, and source snapshots;
- enterprise-impact relationship paths.

The delta never fabricates an absent-side explanation. A missing matching finding or impact is
represented as absent. Worker transitions retain both affected and unaffected assessment results
when both exist.

The semantic delta fingerprint contains the contract version, stable baseline/proposed policy
identities, stable item identities, classifications, delta reason codes, and semantic side values.
It excludes database UUIDs, display text, explanations, and evidence record IDs. Regenerated rows
with unchanged business meaning therefore produce the same fingerprint.

## Persistence

Migration `0011_enterprise_impact_delta` adds:

- `policy_comparison_impact_deltas`;
- `policy_comparison_impact_delta_items`.

The parent stores:

- policy comparison;
- organization;
- baseline and proposed assessment IDs;
- `enterprise-impact-delta-v1` contract version;
- SHA-256 semantic fingerprint;
- creator and creation time.

The child stores:

- global stable sequence;
- closed item kind and change type;
- stable business identity;
- deterministic delta reason code;
- applicable baseline/proposed source-record IDs;
- applicable baseline/proposed authoritative snapshots.

PostgreSQL enforces one delta per comparison, valid side shapes, closed classifications, and stable
sequence/identity uniqueness. Insert triggers validate that the two assessments belong to the
comparison's policies and accepted attempts and that each child lineage record belongs to the
correct assessment side. Update/delete triggers make parent and children immutable.

Impact-delta creation and new comparison creation are atomic. Repeating an equivalent create
request returns the existing comparison and delta. A delta failure rolls back a new comparison.

## API

The existing narrow resources remain:

```http
POST /api/v1/policy-comparisons
GET /api/v1/policy-comparisons/{comparison_id}
```

Creation still accepts only baseline and proposed policy IDs; actor identity remains in
`X-ChangeOps-Actor`. The response now includes `impact_delta` with:

- baseline/proposed assessment lineage;
- contract and fingerprint;
- seven summary counts;
- ordered worker, finding, and enterprise-impact item collections;
- side-specific reasons, evidence, and paths.

Historical comparisons without a delta serialize `impact_delta = null`. Repeating their
equivalent create request creates the missing one-to-one delta without rewriting the comparison.
Clients cannot inject delta values.

## Frontend

The focused comparison page now presents:

- the existing semantic comparison;
- seven operational summary counts;
- grouped worker, finding, and enterprise-impact changes;
- baseline/proposed assessment explanations;
- deterministic delta and assessment reason codes;
- expandable authoritative evidence;
- relationship paths;
- assessment IDs and delta fingerprint;
- an explicit boundary that AI explanation remains deferred.

It retains a stable unavailable state for a historical comparison without a delta.

## Seed and golden behavior

Both policy sources now own business-equivalent system, document, and training dependency records.
This avoids treating an incomplete proposed dependency catalog as a real operational removal.
Dependency row IDs remain source-specific and are not used as impact identity.

The golden delta is:

- 0 workers became affected;
- 3 workers no longer affected;
- 0 workers remained affected;
- 0 findings introduced;
- 6 findings disappeared;
- 0 enterprise impacts introduced;
- 14 enterprise impacts removed.

The proposed assessment retains three document impacts and one policy-required course impact;
those four unchanged impacts do not produce delta items.

## Quality coverage

Pure domain tests cover all closed classifications, ordering, duplicate stable identity, and UUID-
independent fingerprints. PostgreSQL/API tests cover atomic creation, exact golden behavior,
idempotent reuse, complete evidence/path serialization, inability to inject authoritative values,
historical stability, parent/child immutability, and demo reset. Seed tests cover the expanded
source-specific dependency catalog and repeatability. Frontend tests cover populated, empty, and
historical-unavailable states.

All prior backend, frontend, migration round-trip, offline evaluation, demo-reset, and production-
build gates remain required.

## Explicitly deferred

- AI explanation of delta;
- proposed-action delta;
- change-plan revision;
- review or approval changes;
- Jira;
- MCP;
- AWS;
- Terraform;
- generalized policy comparison;
- additional policy families.

## Recommended next vertical slice

Implement governed immutable change-plan revision. That closes the existing
`revision_requested` loop and proves versioned AI-artifact governance without changing the now
authoritative semantic comparison, enterprise impact delta, or assessment snapshots. If AI delta
explanation is later approved, persist it as a separate grounded non-authoritative artifact.
