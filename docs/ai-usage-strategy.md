# ChangeOps AI Usage Strategy

## Status

Proposal for discussion. Not yet an accepted decision.

This document exists to settle one question before `docs/milestone-2.md` is written:

**What should the AI workflow own, and what must it explicitly not own?**

Once the boundary is agreed, it should be recorded as ADR-0009 in `docs/decisions.md` and the
milestone document should be written against it.

---

## Recommendation

Adopt the two-pass pipeline: AI owns **language in** and **interpretation out**, and owns nothing
in between.

```
policy text
    ↓  LLM pass 1 — understanding
candidate typed policy rules + per-field provenance + open questions
    ↓  deterministic validation and clarification gate
validated InternationalTravelPolicyRules
    ↓  deterministic engine (Milestone 1, unchanged)
immutable impact assessment: 18 impacts, evidence, reason codes, paths, actions
    ↓  LLM pass 2 — interpretation
change plan: prioritization, coverage gaps, residual risk, drafted narrative
    ↓
human review
```

This is Option A and Option B in sequence, and it is the right answer. It is also already the
direction the repository has committed to — `docs/roadmap.md` Milestone 2 lists this ten-step
workflow, and ADR-0007 already assigns "extracting structured policy changes," "identifying
ambiguity," "synthesizing evidence," and "generating recommendations" to AI while explicitly
withholding enterprise relationships and business rules. The open work is not choosing a direction;
it is drawing the line precisely enough that the implementation cannot drift across it.

Two clarifications on the framing:

**Option A alone is not enough.** Extraction is a good demonstration of structured output, but it
leaves the product ending at a wall of 18 impacts and 13 proposed actions with no statement of what
matters most, what the analysis could not see, or what a human still has to decide. That gap is the
actual product problem, and it is the one that justifies a workflow rather than a single call.

**The concern about Option B is real but is not a prompting problem.** "The model might make up
impacts" is not solved by careful prompt wording. It is solved by never putting the model in a
position where an invented impact could enter the record: pass 2 receives an already-persisted,
immutable assessment, writes to a separate artifact, and every claim it makes must cite an evidence
key that already exists. Prompting is the last line of defense here, not the first.

**Option C is the wrong architecture, for a reason worth stating plainly.** If the LLM owns
extraction, impact reasoning, and orchestration, then `enterprise_impact_analysis.py` becomes a
retrieval helper, the reason codes and relationship paths become decoration, and the honest answer
to "why does the deterministic engine exist?" becomes "it doesn't, really." Milestone 1's value is
that the impact set is reproducible, explainable, and diffable. An orchestrator that can overrule it
destroys exactly that property.

---

## What the AI workflow owns

Four responsibilities, in two passes.

### 1. Policy understanding (pass 1)

Convert `policy_changes.policy_text` into a candidate `InternationalTravelPolicyRules`.

Today `policy_text` is stored, snapshotted as evidence, and read by nothing. `structured_rules` is
hand-authored JSON in `seed_service.py`. Extraction is what connects them, and it is a genuinely
hard language task: the seeded policy contains a scope rule, an exclusion, an effective date, a
requirement, and an exception that applies to one requirement but not the other. Getting
"travel booked before September 1 is exempt from manager approval but not from training" right from
prose is real work.

Each extracted field should carry provenance — the span of policy text it came from — so a reviewer
can check the extraction without re-reading the whole policy.

### 2. Ambiguity and uncertainty (pass 1)

Identify what the policy text does not determine, and produce the unresolved questions.

This is the responsibility with the largest gap between the current implementation and the product
claim. The eight unresolved questions are hardcoded strings in `seed_service.py`, copied verbatim
into every assessment regardless of what the policy says. "Explicit uncertainty" is currently a
fixture. The AI workflow should generate these from the text, and each question should be anchored
to the field or downstream conclusion it puts in doubt — "How is 'U.S.-based' determined?" should
attach to `worker_scope.assigned_work_country`, not float free.

The model proposes that clarification is needed. Deterministic code decides whether that pauses the
workflow.

### 3. Deterministic-result interpretation (pass 2)

Reason over the completed assessment to produce what the deterministic engine structurally cannot:

- **Prioritization and sequencing.** 13 actions, no ordering. Which must happen before the September
  1 effective date, which block others, which are safe to batch.
- **Coverage gaps.** What the analysis could not see. The engine finds document impacts only where a
  `policy_document_dependency` row exists; it cannot report the document nobody mapped. Naming that
  blind spot is judgment work and is exactly what a reviewer needs.
- **Residual risk and conflicts.** Where the policy text and the deterministic result sit awkwardly
  together — a requirement in the text with no corresponding impact, an impact whose supporting
  dependency mapping looks stale.
- **Cross-domain synthesis.** The engine emits a customer-commitment impact and a training impact
  independently; it does not observe that the same worker is the required resource on a customer
  commitment *and* lacks the training that gates their trip. Connecting those is interpretation.

### 4. Drafting (pass 2)

Human-readable narrative: the change plan, action descriptions, stakeholder communications,
explanations of why an impact matters. Drafting only — bounded to action types the deterministic
layer already defines.

---

## What the AI workflow must not own

| Not owned | Owner | Why |
|---|---|---|
| Whether an object is affected | Deterministic analyzers | The entire point of Milestone 1. The AI may not add, remove, or reclassify an impact. |
| Impact domains, classifications, reason codes, action types | Closed enums in `types.py` and `schemas/assessments.py` | Reason codes are the explainability contract. `milestone-1.md`: they "should not be generated dynamically." |
| Evidence | `_evidence_specs` in the assessment service | The AI cites evidence keys; it never mints them. A citation that does not resolve is a validation failure, not a warning. |
| Enterprise relationships | `policy_*_dependency` tables, team memberships, commitment assignments | Letting a model write dependency rows is letting it invent enterprise facts one layer down, where it is much harder to notice. |
| Enterprise facts | Source tables | Training completion, assigned work country, booking dates. `product-brief.md`: AI is not "the authoritative source for facts already represented in enterprise data." |
| Date arithmetic, overlap, filtering, counting | Deterministic code | Commitment overlap is three comparisons. There is no interpretation here to buy. |
| Identifiers, fingerprints, sort keys, ordering | `fingerprinting.py`, serializer | Stability guarantees. |
| Schema and business validation | Pydantic + validators | Extraction output is *proposed* until deterministic validation accepts it. |
| Workflow control flow | LangGraph edges written as code | The model's output may be a router *input*; the routing logic is code. The model does not decide whether it is finished, whether to retry, or whether it may skip the clarification gate. |
| Approval and execution | Milestones 3 and 4 | `roadmap.md`: "The LLM must not directly write to enterprise systems or approve its own recommendations." |

### The decision rule

> The AI may produce anything that can be checked against something else — a schema, a closed enum,
> an existing evidence key, a span of source text. It may not produce anything that is the final
> word.

Extraction is checkable (Pydantic, referential resolution, source span). Prioritization is checkable
(every cited impact exists). "This worker is affected" is not checkable against anything except the
model's own reasoning, which is why the deterministic engine owns it.

---

## Two roles, not one agent

Implement pass 1 and pass 2 as separate steps with separate inputs. Do not merge them into one
prompt or one agent with tool access to the database.

**Extractor** sees the policy text. It does not see workers, trips, training records, or the
enterprise context. Withholding that context is a safety control, not an optimization: an extractor
that can see the worker list will start reasoning about who is affected, and its output will begin
to encode conclusions rather than rules.

**Interpreter** sees the completed assessment and the policy text. It does not query source tables.
`milestone-1.md` goal 6 anticipated this — Milestone 1 should "expose deterministic enterprise
context that later AI workflows can consume without querying raw database tables directly." The
assessment aggregate is that interface. Honor it.

An agent with database tools collapses both controls at once, which is the practical form Option C
takes in code even when nobody intends to choose it.

---

## Failure modes this boundary has to handle

These are grounded in the current implementation, not hypothetical.

**Silent under-reporting via a plausible course identifier.** `security_training.course_identifier`
must equal `training_courses.id` (`international-travel-security`). If extraction emits a reasonable
guess like `security-awareness`, two things happen quietly: `_add_training_impacts` skips the course
entirely because `course.id != policy.rules.security_training.course_identifier`, so the training
domain returns zero course impacts; and `analyze_policy` finds no matching training record for any
worker, so every affected worker is reported as needing training — including Marcus Lee, who
completed it. The assessment is wrong in both directions and looks entirely normal.

Mitigation, and a good illustration of the boundary: the model emits the course *name and evidence
span* from the policy text. A deterministic resolver maps name to catalog ID and fails or raises a
clarification when there is no confident match. The model reads language; code resolves identity.

**Coerced extraction of an unrepresentable policy.** The typed model is deliberately narrow —
`kind: Literal["international_travel"]`, `schema_version: Literal[1]`, `extra="forbid"`, and
`booking_before_effective_date_is_exempt: Literal[True]`. That last one means the schema *cannot
express* a revision that removes the pre-effective-date exemption. Under pressure to return valid
JSON, a model will set it to `True` anyway and produce a confidently wrong policy. Extraction must
fail closed with an explicit "unsupported policy" outcome. This is a feature to demonstrate, not an
embarrassment to hide.

**Invented impacts entering through the interpretation pass.** Structural, not prompt-level: pass 2
runs after the assessment is persisted and immutable, writes to a separate artifact, and every
reference it makes to an impact or evidence key is validated against the assessment before the
result is stored. An unresolvable reference fails the step.

**Ambiguity theater.** A model asked to find ambiguity will always find some. Questions need to be
attached to a specific field or conclusion and be answerable; a free-floating list of eight plausible
concerns is what already exists in the seed, and regenerating it with an LLM is not progress.

---

## Consequences for the existing guarantees

**Determinism narrows, and the claim must be restated.** Today: same source data → same assessment,
enforced by the fingerprint. After Milestone 2: same *extracted rules* → same assessment. The
deterministic guarantee is fully preserved below the extraction boundary and does not exist above
it. `input_fingerprint` already covers `policy.rules`, so an extraction that differs produces a
visibly different assessment rather than a silently different one. The extraction step needs its own
version identifier (model, prompt version, schema version) recorded alongside the run.

**Assessment immutability is preserved by not touching it.** The AI's output is a new persisted
artifact linked to the assessment, never a mutation of it. This also makes the AI output re-runnable
against a fixed assessment, which is what makes evaluation tractable.

**Evaluation splits cleanly**, which is the payoff of the whole boundary:

- Deterministic engine: existing unit, integration, and contract tests. Exact assertions.
- Extraction: a golden dataset of policy text → expected typed rules, plus negative cases that must
  fail closed.
- Interpretation: rubric or judged evaluation over grounding (does every citation resolve?),
  coverage, and usefulness.

Milestone 5's exit criterion — "deterministic and AI evaluations run automatically" — is only
achievable if the two never share responsibility for the same conclusion.

---

## Open questions for the discussion

1. **Does extraction stay pinned to `international_travel`, or does the schema generalize in
   Milestone 2?** Recommendation: stay pinned. "This policy is outside the supported family" is a
   stronger demonstration than a schema loose enough to absorb anything.
2. **Do the AI-generated unresolved questions replace the seeded eight, or supplement them?**
   Replacing is the honest answer; it will change the golden scenario, which per `CONTRIBUTING.md`
   requires approval.
3. **What is the clarification gate's trigger?** Any question at all, only questions touching fields
   that change the impact set, or a confidence threshold? The second is the most defensible and the
   hardest to implement.
4. **Does pass 2 run inside the same LangGraph run as pass 1, or is it separately invocable against
   an existing assessment?** Separately invocable is better for evaluation and for re-running after
   the deterministic engine changes.
5. **Does the change plan get its own tables and endpoint, or extend the assessment response?** The
   immutability invariant argues for separate tables and a separate endpoint.
6. **Which parts of pass 2 are actually in Milestone 2?** Prioritization, coverage gaps, residual
   risk, cross-domain synthesis, and drafting are five distinct capabilities. Shipping two of them
   well is better than five thinly.

---

## Not decided here

Prompt design, model selection, LangChain and LangGraph structure, node decomposition, retry policy,
persistence schema for workflow state, and tracing. Those belong in `docs/milestone-2.md`, written
after this boundary is agreed.
