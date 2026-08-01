from dataclasses import dataclass
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from pydantic import ValidationError

from changeops.ai.policy_extractor import StructuredOutputModel, _json_safe
from changeops.domain.policy_interpretation import CandidateChangePlan, PolicyInterpretationInput

PROMPT_VERSION = "coverage-gap-interpretation-v1"

SYSTEM_PROMPT = """You identify grounded coverage gaps in a completed deterministic
policy assessment.
The assessment is authoritative. Findings are review concerns only: never add, remove, contradict,
reclassify, or modify an impact, reason code, evidence item, relationship path, action, or count.
Use only supplied persisted artifacts. Every reference must resolve from the input. Omit unsupported
claims; absence is preferable to speculation. Recommended actions must be human review actions, not
enterprise-system execution. Use conclusion_type review_concern. Leave asserted_enterprise_facts
and impact_mutations empty. Return an empty coverage_gaps list when no grounded gap exists."""

PROMPT = ChatPromptTemplate.from_messages(
    [("system", SYSTEM_PROMPT), ("human", "Interpret this persisted assessment input:\n{payload}")]
)


@dataclass(frozen=True)
class ConfiguredInterpretationModel:
    model: StructuredOutputModel
    provider: str
    identifier: str


@dataclass(frozen=True)
class InterpretationInvocation:
    candidate: CandidateChangePlan | None
    raw_output: Any
    parsing_error: str | None


def invoke_policy_interpreter(
    model: StructuredOutputModel,
    interpretation_input: PolicyInterpretationInput,
) -> InterpretationInvocation:
    try:
        structured = model.with_structured_output(CandidateChangePlan, include_raw=True)
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
    return InterpretationInvocation(candidate, raw, None)
