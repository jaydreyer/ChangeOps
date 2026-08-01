from dataclasses import dataclass
from typing import Any, Literal, Protocol

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from pydantic import ValidationError

from changeops.ai.policy_extractor import _json_safe
from changeops.domain.policy_interpretation import (
    CandidateChangePlan,
    CandidateCoverageGapFinding,
    EvidenceReference,
    ImpactReference,
    PolicyInterpretationInput,
    PolicySpanReference,
    ProposedChangePlan,
)

PROMPT_VERSION = "coverage-gap-interpretation-v4"

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
return them at the top level. Ground each gap with exact policy_quotes copied from policy_text,
existing impact_ids copied from impacts when applicable, and existing evidence_keys copied from the
supplied artifacts when applicable. Do not calculate character offsets or return policy IDs,
assessment IDs, evidence-owner IDs, or relationship-path positions; deterministic application code
constructs those references. Return an empty coverage_gaps list when no grounded gap exists."""

PROMPT = ChatPromptTemplate.from_messages(
    [("system", SYSTEM_PROMPT), ("human", "Interpret this persisted assessment input:\n{payload}")]
)


class InterpretationStructuredOutputModel(Protocol):
    def with_structured_output(
        self,
        schema: type[ProposedChangePlan],
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
            ProposedChangePlan,
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
        proposal = (
            parsed
            if isinstance(parsed, ProposedChangePlan)
            else ProposedChangePlan.model_validate(parsed)
        )
    except ValidationError as error:
        boundary_fields = {"asserted_enterprise_facts", "impact_mutations"}
        if any(boundary_fields.intersection(map(str, item["loc"])) for item in error.errors()):
            return InterpretationInvocation(None, raw, "structured_output_boundary_violation")
        return InterpretationInvocation(None, raw, "structured_output_validation_failed")
    return InterpretationInvocation(
        _ground_proposed_change_plan(proposal, interpretation_input),
        raw,
        None,
    )


def _ground_proposed_change_plan(
    proposal: ProposedChangePlan,
    interpretation_input: PolicyInterpretationInput,
) -> CandidateChangePlan:
    impact_by_id = {item.id: item for item in interpretation_input.impacts}
    assessment_id = interpretation_input.impact_assessment_id

    def ground_finding(finding) -> CandidateCoverageGapFinding:
        impact_ids = list(dict.fromkeys(finding.impact_ids))

        def ground_evidence(evidence_key: str) -> EvidenceReference:
            cited_owner = next(
                (
                    impact_by_id[impact_id]
                    for impact_id in impact_ids
                    if impact_id in impact_by_id
                    and evidence_key in impact_by_id[impact_id].evidence_keys
                ),
                None,
            )
            if cited_owner is not None:
                return EvidenceReference(
                    assessment_id=assessment_id,
                    evidence_key=evidence_key,
                    impact_id=cited_owner.id,
                )

            finding_owner = next(
                (
                    owner
                    for owner in interpretation_input.findings
                    if evidence_key in owner.evidence_keys
                ),
                None,
            )
            if finding_owner is not None:
                return EvidenceReference(
                    assessment_id=assessment_id,
                    evidence_key=evidence_key,
                    finding_id=finding_owner.id,
                )

            impact_owner = next(
                (
                    owner
                    for owner in interpretation_input.impacts
                    if evidence_key in owner.evidence_keys
                ),
                None,
            )
            if impact_owner is not None:
                if impact_owner.id not in impact_ids:
                    impact_ids.append(impact_owner.id)
                return EvidenceReference(
                    assessment_id=assessment_id,
                    evidence_key=evidence_key,
                    impact_id=impact_owner.id,
                )

            return EvidenceReference(
                assessment_id=assessment_id,
                evidence_key=evidence_key,
            )

        evidence_references = tuple(
            ground_evidence(key) for key in dict.fromkeys(finding.evidence_keys)
        )
        policy_spans = []
        for quote in dict.fromkeys(finding.policy_quotes):
            start = interpretation_input.policy_text.find(quote)
            if start < 0:
                start = 0
            policy_spans.append(
                PolicySpanReference(
                    policy_change_id=interpretation_input.policy_change_id,
                    start=start,
                    end=start + len(quote),
                    quote=quote,
                )
            )

        return CandidateCoverageGapFinding(
            finding_key=finding.finding_key,
            title=finding.title,
            observed_limitation=finding.observed_limitation,
            why_it_matters=finding.why_it_matters,
            recommended_review_action=finding.recommended_review_action,
            conclusion_type=finding.conclusion_type,
            policy_spans=tuple(policy_spans),
            impact_references=tuple(
                ImpactReference(assessment_id=assessment_id, impact_id=impact_id)
                for impact_id in impact_ids
            ),
            evidence_references=evidence_references,
            asserted_enterprise_facts=finding.asserted_enterprise_facts,
            impact_mutations=finding.impact_mutations,
        )

    return CandidateChangePlan(
        summary=proposal.summary,
        coverage_gaps=tuple(ground_finding(finding) for finding in proposal.coverage_gaps),
    )
