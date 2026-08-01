# ChangeOps AI Usage Strategy

## Status

Proposal for discussion. Not yet an accepted decision. Revised following review.

This document exists to settle two questions before `docs/milestone-2.md` is written:

1. **What should the AI workflow own, and what must it explicitly not own?**
2. **How does work move through the system, from policy submission to human-reviewed change plan?**

The first is a boundary question and the second is a process question. They constrain each other, and
answering only one leaves the milestone underspecified.

Once both are agreed, they should be recorded as ADR-0009 in `docs/decisions.md` and the milestone
document should be written against them.

---

## Principles

Four principles govern every AI step in ChangeOps. Each is stated so that a violation is detectable
rather than debatable.

1. **AI assists; deterministic code decides.** No conclusion reaches a reviewer on the model's
   authority alone.
2. **AI output is proposed until validated.** Nothing an LLM returns is persisted as fact before it
   passes schema, enum, and referential validation.
3. **Every AI claim cites something that already exists.** Evidence keys, impact records, and source
   text spans are referenced, never minted.
4. **Every AI step has a test that can fail.** Grounding is asserted, extraction is measured against
   a golden dataset, and interpretation quality is judged. See [Evaluation](#evaluation).

---

## Recommendation

Adopt a policy analysis pipeline in which AI owns **language in** and **interpretation out**, and
owns nothing in between.

```
policy text
    ↓  AI — understanding
candidate typed policy rules + per-field provenance + open questions
    ↓  deterministic validation and clarification gate
validated InternationalTravelPolicyRules
    ↓  deterministic engine (Milestone 1, unchanged)
immutable impact assessment: 18 impacts, evidence, reason codes, paths, actions
    ↓  AI — interpretation
change plan: coverage gaps, residual risk, cross-domain synthesis
    ↓
human review
```

This architecture best satisfies the project's stated goals of explainability, determinism, and
enterprise realism, and it is the direction the repository already committed to — `docs/roadmap.md`
Milestone 2 lists this workflow, and ADR-0007 already assigns "extracting structured policy changes,"
"identifying ambiguity," "synthesizing evidence," and "generating recommendations" to AI while
explicitly withholding enterprise relationships and business rules. The open work is not choosing a
direction; it is drawing the line precisely enough that the implementation cannot drift across it.

Three clarifications on the framing:

**Extraction alone is not enough.** It is a good demonstration of structured output, but it leaves
the product ending at a wall of 18 impacts and 13 proposed actions with no statement of what the
analysis could not see or what a human still has to decide. That gap is the actual product problem,
and it is the one that justifies a workflow rather than a single call.

**The risk that a model invents impacts is real, but it is not a prompting problem.** It is solved by
never putting the model in a position where an invented impact could enter the record: the
interpretation step receives an already-persisted, immutable assessment, writes to a separate
artifact, and every claim it makes must cite an evidence key that already exists. Prompting is the
last line of defense here, not the first.

**A full AI orchestrator — one model owning extraction, impact reasoning, and control flow — is the
wrong architecture, for a reason worth stating plainly.** It would reduce
`enterprise_impact_analysis.py` to a retrieval helper, make the reason codes and relationship paths
decoration, and leave no honest answer to "why does the deterministic engine exist?" Milestone 1's
value is that the impact set is reproducible, explainable, and diffable. An orchestrator that can
overrule it destroys exactly that property.

---

## How work moves through the system

The ownership boundary describes what each layer is allowed to conclude. It does not describe how a
policy becomes a reviewed change plan. That is a business process, and it is the reason this
milestone needs durable orchestration rather than a request/response handler.

```
policy document submitted
    ↓
extraction proposes typed rules, provenance, and open questions
    ↓
deterministic validation
    ├── unsupported policy ────────────→ run ends with an explanation, no assessment
    ├── clarification required ─────────→ run pauses  ← the durability requirement
    │                                        ↓
    │                                   human answers, possibly days later,
    │                                   in a different process
    │                                        ↓
    │                                   run resumes and re-validates
    └── accepted
    ↓
deterministic enterprise impact discovery (Milestone 1, unchanged)
    ↓
immutable impact assessment persisted
    ↓
interpretation reads the persisted assessment
    ↓
change plan persisted as a separate artifact
    ↓
human review
```

Three properties of this process matter architecturally.

**The pause is not an implementation detail.** A run that stops for human clarification and resumes
later in a different process cannot hold state in memory or in a request. Milestone 2's exit criteria
already require this — "ambiguous policy text pauses the workflow" and "approved clarification
resumes the same persisted workflow" — and Milestone 3 escalates it to surviving process restart.

**A run and an assessment have different lifecycles.** The interrupt sits *before* the deterministic
engine, so a workflow run can exist for days with no assessment attached, and some runs end without
ever producing one. `ImpactAssessment` is currently created only on success and has no way to
represent "we started, and stopped here, for this reason." The workflow run is therefore a separate
record that references an assessment once one exists, not a field on the assessment.

**Human clarification is an input, not a side conversation.** When a reviewer resolves an ambiguity,
that answer changes the extracted rules and therefore the impact set. It has to be captured with the
same provenance discipline as policy text. `docs/product-brief.md` already anticipates this: every
material conclusion must trace to "source data, policy evidence, deterministic rules, or explicit
human input."

---

## Why LangGraph

`CONTRIBUTING.md` requires that a technology enter the project only when a milestone contains a
problem that requires it, and specifically warns against building graphs around deterministic
functions. That rule deserves an honest answer rather than a list of desirable properties.

> LangGraph is introduced because the workflow must pause for human clarification and resume later,
> in a different process, without recomputing prior steps or losing state. If clarification and
> resume were removed from Milestone 2, sequential Python functions over a persisted state row would
> be sufficient and LangGraph would not be justified.

That claim is falsifiable, which is the point. It also sets the honest scope: the graph is a durable
state machine with checkpoints and typed transitions, not an agent loop. Nodes are invoked in an
order the code determines. The model is a node; it is never the router.

The secondary benefit — inspectable state, retries, and visible transitions across a workflow that
mixes deterministic and probabilistic steps — is real and is listed in the Milestone 2 exit criteria,
but it is not what forces the choice. The interrupt is.

---

## What the AI workflow owns

### Policy understanding

Convert `policy_changes.policy_text` into a candidate `InternationalTravelPolicyRules`.

Today `policy_text` is stored, snapshotted as evidence, and read by nothing. `structured_rules` is
hand-authored JSON in `seed_service.py`. Extraction is what connects them, and it is a genuinely hard
language task: the seeded policy contains a scope rule, an exclusion, an effective date, a
requirement, and an exception that applies to one requirement but not the other. Getting "travel
booked before September 1 is exempt from manager approval but not from training" right from prose is
real work.

Each extracted field should carry provenance — the span of policy text it came from — so a reviewer
can check the extraction without re-reading the whole policy.

### Ambiguity and uncertainty

Identify what the policy text does not determine, and produce the unresolved questions.

This is the responsibility with the largest gap between the current implementation and the product
claim. The eight unresolved questions are hardcoded strings in `seed_service.py:434`, copied verbatim
into every assessment regardless of what the policy says. "Explicit uncertainty" is currently a
fixture. The AI workflow should generate these from the text, and each question should be anchored to
the field or downstream conclusion it puts in doubt — "How is 'U.S.-based' determined?" should attach
to `worker_scope.assigned_work_country`, not float free.

The model proposes that clarification is needed. Deterministic code decides whether that pauses the
run.

### Deterministic-result interpretation

Reason over the completed assessment to produce what the deterministic engine structurally cannot:

- **Coverage gaps.** What the analysis could not see. The engine finds document impacts only where a
  `policy_document_dependency` row exists; it cannot report the document nobody mapped. Naming that
  blind spot is judgment work, it is the capability no deterministic layer can replicate, and it is
  the one I would ship first.
- **Residual risk and conflicts.** Where the policy text and the deterministic result sit awkwardly
  together — a requirement in the text with no corresponding impact, an impact whose supporting
  dependency mapping looks stale.
- **Cross-domain synthesis.** The engine emits a customer-commitment impact and a training impact
  independently; it does not observe that the same worker is the required resource on a customer
  commitment *and* lacks the training that gates their trip. Connecting those is interpretation.

Interpretation output is prose by nature — a coverage gap is only useful when it is stated in a
sentence. That is intrinsic to the reasoning and is not what the next section excludes.

### Excluded from the interpretation step

Two capabilities were considered and deliberately left out.

**Outbound artifacts.** Stakeholder emails, notifications, and communications drafted for sending are
excluded, because they are the one output this document's decision rule cannot govern: a drafted
email is not checkable against a schema, an enum, an evidence key, or a source span. This is the
boundary rule applied consistently, not a scope compromise.

**Prioritization and sequencing.** Excluded because a substantial part of it is deterministic. The
effective date is known, `proposed_actions.due_date` already exists, and ordering by date is code.
Assigning it to the model invites the model to redo work the engine already did, in a form nobody can
diff. If prioritization returns later, it should return as a deterministic ordering that
interpretation explains, not as a judgment the model makes.

---

## What the AI workflow must not own

| Not owned | Owner | Why |
|---|---|---|
| Whether an object is affected | Deterministic analyzers | The entire point of Milestone 1. The AI may not add, remove, or reclassify an impact. |
| Impact domains, classifications, reason codes, action types | Closed enums in `types.py` and `schemas/assessments.py` | Reason codes are the explainability contract. `milestone-1.md`: they "should not be generated dynamically." |
| Evidence and citation bookkeeping | `_evidence_specs` plus deterministic interpretation grounding | The AI cites evidence keys and exact policy quotes; it never mints evidence or calculates offsets, lifecycle IDs, or evidence owners. A citation that does not resolve is a validation failure, not a warning. |
| Enterprise relationships | `policy_*_dependency` tables, team memberships, commitment assignments | Letting a model write dependency rows is letting it invent enterprise facts one layer down, where it is much harder to notice. |
| Enterprise facts | Source tables | Training completion, assigned work country, booking dates. `product-brief.md`: AI is not "the authoritative source for facts already represented in enterprise data." |
| Date arithmetic, overlap, filtering, counting, ordering | Deterministic code | Commitment overlap is three comparisons. There is no interpretation here to buy. |
| Identifiers, fingerprints, sort keys | `fingerprinting.py`, serializer | Stability guarantees. |
| Schema and business validation | Pydantic + validators | Extraction output is *proposed* until deterministic validation accepts it. |
| Workflow control flow | LangGraph edges written as code | The model's output may be a router *input*; the routing logic is code. The model does not decide whether it is finished, whether to retry, or whether it may skip the clarification gate. |
| Outbound communications and artifacts | Deferred past Milestone 2 | Not checkable against anything the pipeline holds. |
| Approval and execution | Milestones 3 and 4 | `roadmap.md`: "The LLM must not directly write to enterprise systems or approve its own recommendations." |

### The decision rule

> The AI may produce anything that can be checked against something else — a schema, a closed enum,
> an existing evidence key, a span of source text. It may not produce anything that is the final
> word.

Extraction is checkable (Pydantic, referential resolution, source span). Coverage-gap reasoning is
checkable (every cited impact exists, every claimed gap corresponds to an absent dependency row).
"This worker is affected" is not checkable against anything except the model's own reasoning, which
is why the deterministic engine owns it.

---

## Two roles, not one agent

Implement the two AI steps separately, with separate inputs. Do not merge them into one prompt or one
agent with tool access to the database.

**Extractor** sees the policy text. It does not see workers, trips, training records, or the
enterprise context. Withholding that context is a safety control, not an optimization: an extractor
that can see the worker list will start reasoning about who is affected, and its output will begin to
encode conclusions rather than rules.

**Interpreter** sees the completed assessment and the policy text. It does not query source tables.
`milestone-1.md` goal 6 anticipated this — Milestone 1 should "expose deterministic enterprise
context that later AI workflows can consume without querying raw database tables directly." The
assessment aggregate is that interface. Honor it.

An agent with database tools collapses both controls at once, which is the practical form the
full-orchestrator architecture takes in code even when nobody intends to choose it.

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

**Invented impacts entering through the interpretation step.** Structural, not prompt-level:
interpretation runs after the assessment is persisted and immutable, writes to a separate artifact,
and every reference it makes to an impact or evidence key is validated against the assessment before
the result is stored. An unresolvable reference fails the step.

**Ambiguity theater.** A model asked to find ambiguity will always find some. Questions need to be
attached to a specific field or conclusion and be answerable; a free-floating list of eight plausible
concerns is what already exists in the seed, and regenerating it with an LLM is not progress.

---

## Evaluation

Evaluation is a pillar of this milestone, not a closing consequence of it. The boundary above is what
makes it tractable: because no conclusion is jointly owned, each layer can be measured on its own
terms.

Three layers, with deliberately different rigor.

**Grounding is an assertion, not an evaluation.** "Every evidence key and impact reference in an AI
output resolves against the persisted assessment" is deterministic and belongs in pytest as a hard
gate. Calling it an eval would make the rigorous half of the story look soft.

**Extraction is a golden dataset, gating on merge.** Policy text in, expected typed rules out, plus
negative cases that must fail closed. The first case already exists in the repository:
`seed_service.py:28` holds `POLICY_TEXT` and line 466 holds the hand-verified `STRUCTURED_RULES` for
the same policy, and `demo-scenario.md` is already written as executable specification. A regression
should block a merge, not appear in a report.

**Interpretation quality is judged.** Coverage and usefulness need a rubric and a judge. This is the
softest layer and should be tracked rather than gating, at least initially — claiming otherwise would
overstate what a rubric score means.

`docs/roadmap.md` sets "deterministic and AI evaluations run automatically" as a Milestone 5 exit
criterion. That is only reachable if the two never share responsibility for the same conclusion,
which is what this boundary buys.

Dataset format, rubric design, thresholds, and CI wiring belong in `docs/milestone-2.md`.

---

## Consequences for the existing guarantees

**Determinism narrows, and the claim must be restated.** Today: same source data → same assessment,
enforced by the fingerprint. After Milestone 2: same *extracted rules* → same assessment. The
deterministic guarantee is fully preserved below the extraction boundary and does not exist above it.
`input_fingerprint` already covers `policy.rules`, so an extraction that differs produces a visibly
different assessment rather than a silently different one. The extraction step needs its own version
identifier — model, prompt version, schema version — recorded alongside the run.

**Assessment immutability is preserved by not touching it.** The AI's interpretation output is a new
persisted artifact linked to the assessment, never a mutation of it. This also makes the output
re-runnable against a fixed assessment, which is what makes judged evaluation repeatable.

---

## Open questions for the discussion

1. **Does extraction stay pinned to `international_travel`, or does the schema generalize in
   Milestone 2?** Recommendation: stay pinned. "This policy is outside the supported family" is a
   stronger demonstration than a schema loose enough to absorb anything.
2. **Do the AI-generated unresolved questions replace the seeded eight, or supplement them?**
   Replacing is the honest answer; it will change the golden scenario, which per `CONTRIBUTING.md`
   requires approval.
3. **What is the clarification gate's trigger?** Any question at all, only questions touching fields
   that change the impact set, or a confidence threshold? This is now the most consequential open
   question, because the interrupt is what justifies durable orchestration. The second option is the
   most defensible and the hardest to implement.
4. **How is a run that never produces an assessment represented?** Unsupported policy, abandoned
   clarification, and extraction failure all need a terminal state that today's schema cannot express.
5. **Is human clarification captured as evidence with its own type, and does it enter the
   fingerprint?** It changes the extracted rules, so it changes the result; the traceability contract
   in `product-brief.md` already implies it must be recorded.
6. **Is interpretation separately invocable against an existing assessment, or only reachable inside
   a run?** Separately invocable is better for evaluation and for re-running after the deterministic
   engine changes.
7. **Which of the three interpretation capabilities ship in Milestone 2?** Recommendation: coverage
   gaps first, since it is the only one with no deterministic equivalent. Two done well beats three
   thinly.

---

## Not decided here

Prompt design, model selection, LangChain usage, graph node decomposition, retry policy, persistence
schema for workflow state and change plans, tracing, and evaluation dataset format. Those belong in
`docs/milestone-2.md`, written after this boundary and this process are agreed.
