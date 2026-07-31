# Milestone 1 Implementation Notes

## Existing components to extend

- Extend the SQLAlchemy source model, Alembic history, and idempotent seed service.
- Preserve `analyze_policy` as the Milestone 0 worker-and-trip analyzer; add a second pure
  deterministic analyzer for enterprise impacts.
- Extend the existing assessment service transaction, evidence snapshot builder, fingerprint,
  eager loading, serializer, Pydantic contract, and the two existing assessment endpoints.
- Preserve the current stable semantic ordering conventions rather than relying on UUID or row
  order.

## New source entities

- Teams, with a manager worker and an explicit worker-to-team membership.
- Enterprise systems.
- Enterprise documents.
- Training courses referenced by existing completion records.
- Customer commitments and worker assignments.
- Separate typed policy-to-system, policy-to-document, and policy-to-course dependencies.

Managers are represented by worker records and referenced through `workers.manager_worker_id`.
This gives managers stable keys and relational integrity without introducing a second person model.

## Assessment persistence

- `assessment_enterprise_impacts` stores one immutable, queryable impact record.
- `assessment_impact_evidence` links impacts to existing immutable evidence snapshots.
- `assessment_impact_path_elements` stores ordered, structured relationship paths.
- `proposed_actions` gains an optional enterprise-impact link so cross-domain actions remain in
  the existing action collection with `execution_status = not_executed`.
- The existing service persists workers, findings, evidence, enterprise impacts, paths, actions,
  and questions in one transaction.

## Milestone 0 compatibility

- Existing endpoints and top-level worker results, findings, evidence, actions, and questions stay
  in place.
- Existing worker classifications, reason codes, six findings, and four worker actions remain
  unchanged.
- New response fields are additive: `input_fingerprint`, enterprise-impact summary fields, and
  categorized `enterprise_impacts`.
- Existing worker rows retain `manager_name`; stable manager and team foreign keys supplement it.

## Scoped deviations and decisions

- Worker-to-team membership uses a narrow typed table with one current membership per worker; no
  unused membership history or generalized organization graph is introduced.
- Three typed policy-dependency tables are used instead of one polymorphic target table, preserving
  PostgreSQL foreign-key integrity.
- Enterprise impact collections contain affected objects only. Unaffected seeded objects remain
  queryable source records and are covered by negative tests; existing worker results continue to
  return both affected and unaffected classifications.
- No generalized graph, rules engine, workflow framework, background processing, AI, approval, or
  execution capability is introduced.
