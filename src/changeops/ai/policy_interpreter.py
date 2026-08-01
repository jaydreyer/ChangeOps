from dataclasses import dataclass
from typing import Any, Literal, Protocol

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from pydantic import ValidationError

from changeops.ai.policy_extractor import _json_safe
from changeops.domain.policy_interpretation import CandidateChangePlan, PolicyInterpretationInput

PROMPT_VERSION = "coverage-gap-interpretation-v3"

SYSTEM_PROMPT = """You identify grounded coverage gaps in a completed deterministic
policy assessment.
The assessment is authoritative. Findings are review concerns only: never add, remove, contradict,
reclassify, or modify an impact, reason code, evidence item, relationship path, action, or count.
The authoritative policy representation intentionally stores the effective date in
policy_effective_date rather than duplicating it inside accepted_rules. Treat policy_effective_date
and accepted_rules together as the complete accepted policy input. The absence of effective_date
inside accepted_rules is not a coverage gap.
Use only supplied persisted artifacts. Every reference must resolve from the input. Omit unsupported
claims; absence is preferable to speculation. Recommended actions must be human review actions, not
enterprise-system execution. Use conclusion_type review_concern. Leave asserted_enterprise_facts
and impact_mutations empty. The top-level object has exactly summary and coverage_gaps. Reference
arrays, asserted_enterprise_facts, and impact_mutations belong only inside each coverage gap; never
return them at the top level. Every evidence reference must identify exactly one owner: set either
impact_id or finding_id, never both. Set impact_id only when that evidence_key appears in the cited
impact's supplied evidence_keys and that impact is cited by the coverage gap. Set finding_id only
when the evidence_key appears in that finding's supplied evidence_keys. Return an empty
coverage_gaps list when no grounded gap exists."""

PROMPT = ChatPromptTemplate.from_messages(
    [("system", SYSTEM_PROMPT), ("human", "Interpret this persisted assessment input:\n{payload}")]
)


class InterpretationStructuredOutputModel(Protocol):
    def with_structured_output(
        self,
        schema: type[CandidateChangePlan],
        *,
        method: Literal["function_calling"],
        include_raw: bool,
    ) -> Runnable[Any, Any]: ...


@dataclass(frozen=True)
class ConfiguredInterpretationModel:
    model: InterpretationStructuredOutputModel
    provider: str
    identifier: str


@dataclass(frozen=True)
class InterpretationInvocation:
    candidate: CandidateChangePlan | None
    raw_output: Any
    parsing_error: str | None


def invoke_policy_interpreter(
    model: InterpretationStructuredOutputModel,
    interpretation_input: PolicyInterpretationInput,
) -> InterpretationInvocation:
    try:
        structured = model.with_structured_output(
            CandidateChangePlan,
            method="function_calling",
            include_raw=True,
        )
        response = structured.invoke(
            PROMPT.invoke({"payload": interpretation_input.model_dump_json()})
        )
    except Exception as error:
        return InterpretationInvocation(
            None, None, f"model_invocation_failed: {type(error).__name__}"
        )
    if not isinstance(response, dict):
        return InterpretationInvocation(
            None, _json_safe(response), "structured_output_contract_error"
        )
    raw = _json_safe(response.get("raw"))
    if response.get("parsing_error") is not None:
        return InterpretationInvocation(None, raw, "structured_output_parsing_failed")
    try:
        parsed = response.get("parsed")
        candidate = (
            parsed
            if isinstance(parsed, CandidateChangePlan)
            else CandidateChangePlan.model_validate(parsed)
        )
    except ValidationError as error:
        boundary_fields = {"asserted_enterprise_facts", "impact_mutations"}
        if any(boundary_fields.intersection(map(str, item["loc"])) for item in error.errors()):
            return InterpretationInvocation(None, raw, "structured_output_boundary_violation")
        return InterpretationInvocation(None, raw, "structured_output_validation_failed")
    return InterpretationInvocation(
        _resolve_candidate_references(candidate, interpretation_input),
        raw,
        None,
    )


def _resolve_candidate_references(
    candidate: CandidateChangePlan,
    interpretation_input: PolicyInterpretationInput,
) -> CandidateChangePlan:
    candidate = _resolve_policy_spans(candidate, interpretation_input.policy_text)
    impact_by_id = {item.id: item for item in interpretation_input.impacts}
    finding_by_id = {item.id: item for item in interpretation_input.findings}

    def resolve_finding(finding):
        cited_impact_ids = {item.impact_id for item in finding.impact_references}

        def valid_impact_owner(reference) -> bool:
            impact = impact_by_id.get(reference.impact_id)
            return (
                impact is not None
                and impact.id in cited_impact_ids
                and reference.evidence_key in impact.evidence_keys
            )

        def valid_finding_owner(reference) -> bool:
            owner = finding_by_id.get(reference.finding_id)
            return owner is not None and reference.evidence_key in owner.evidence_keys

        def resolve_owner(reference):
            if valid_impact_owner(reference):
                return reference.model_copy(update={"finding_id": None})
            if valid_finding_owner(reference):
                return reference.model_copy(update={"impact_id": None})

            if reference.impact_id is not None and reference.finding_id is None:
                owners = [
                    impact.id
                    for impact_id in cited_impact_ids
                    if (impact := impact_by_id.get(impact_id)) is not None
                    and reference.evidence_key in impact.evidence_keys
                ]
                if len(owners) == 1:
                    return reference.model_copy(update={"impact_id": owners[0]})

            if reference.finding_id is not None and reference.impact_id is None:
                owners = [
                    owner.id
                    for owner in interpretation_input.findings
                    if reference.evidence_key in owner.evidence_keys
                ]
                if len(owners) == 1:
                    return reference.model_copy(update={"finding_id": owners[0]})

            return reference

        return finding.model_copy(
            update={
                "evidence_references": tuple(
                    resolve_owner(reference) for reference in finding.evidence_references
                )
            }
        )

    return candidate.model_copy(
        update={"coverage_gaps": tuple(resolve_finding(item) for item in candidate.coverage_gaps)}
    )


def _resolve_policy_spans(
    candidate: CandidateChangePlan,
    policy_text: str,
) -> CandidateChangePlan:
    def resolve(span):
        if policy_text[span.start : span.end] == span.quote:
            return span

        starts: list[int] = []
        offset = 0
        while (start := policy_text.find(span.quote, offset)) >= 0:
            starts.append(start)
            offset = start + 1
        if not starts:
            return span

        start = min(starts, key=lambda match: abs(match - span.start))
        return span.model_copy(update={"start": start, "end": start + len(span.quote)})

    return candidate.model_copy(
        update={
            "coverage_gaps": tuple(
                finding.model_copy(
                    update={"policy_spans": tuple(resolve(span) for span in finding.policy_spans)}
                )
                for finding in candidate.coverage_gaps
            )
        }
    )
