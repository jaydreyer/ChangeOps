from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from langchain_core.messages import BaseMessage, message_to_dict
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from pydantic import ValidationError

from changeops.domain.policy_extraction import PolicyExtractionProposal

PROMPT_VERSION = "international-travel-extraction-v1"
SCHEMA_VERSION = "policy-extraction-v1"

SYSTEM_PROMPT = """You extract proposed policy rules from source text.

You support only the international_travel policy family and schema version 1. The current schema
requires all of the following:
- a policy effective date;
- an assigned-work-country and one or more employee/contractor worker types;
- an origin country and excluded destination countries;
- manager approval with bookings before the effective date exempt;
- a required training-course name.

Fail closed. Mark the policy unsupported when it belongs to another family or when any material
construct cannot be represented exactly. Use unresolved findings for missing or conflicting facts.

Never invent an enterprise identifier. Extract only the human-readable training-course name.
For every material field, return one exact zero-based [start, end) source span whose quote exactly
matches the policy text. Findings must also cite an exact source span."""

PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        ("human", "Extract proposed rules from this policy text:\n\n{policy_text}"),
    ]
)


@runtime_checkable
class StructuredOutputModel(Protocol):
    def with_structured_output(
        self,
        schema: type[PolicyExtractionProposal],
        *,
        include_raw: bool,
    ) -> Runnable[Any, Any]: ...


@dataclass(frozen=True)
class ConfiguredExtractionModel:
    model: StructuredOutputModel
    provider: str
    identifier: str


@dataclass(frozen=True)
class ExtractionInvocation:
    proposal: PolicyExtractionProposal | None
    raw_output: dict[str, Any] | list[Any] | str | int | float | bool | None
    parsing_error: str | None


def invoke_policy_extractor(
    model: StructuredOutputModel,
    policy_text: str,
) -> ExtractionInvocation:
    try:
        structured_model = model.with_structured_output(
            PolicyExtractionProposal,
            include_raw=True,
        )
        response = structured_model.invoke(PROMPT.invoke({"policy_text": policy_text}))
    except Exception as error:
        return ExtractionInvocation(
            proposal=None,
            raw_output=None,
            parsing_error=f"model_invocation_failed: {type(error).__name__}: {error}",
        )

    if not isinstance(response, dict):
        return ExtractionInvocation(
            proposal=None,
            raw_output=_json_safe(response),
            parsing_error="structured_output_contract_error: expected a mapping response",
        )

    parsed = response.get("parsed")
    parsing_error = response.get("parsing_error")
    raw_output = _json_safe(response.get("raw"))

    if parsing_error is not None:
        return ExtractionInvocation(
            proposal=None,
            raw_output=raw_output,
            parsing_error=f"structured_output_parsing_failed: {parsing_error}",
        )

    try:
        proposal = (
            parsed
            if isinstance(parsed, PolicyExtractionProposal)
            else PolicyExtractionProposal.model_validate(parsed)
        )
    except ValidationError as error:
        return ExtractionInvocation(
            proposal=None,
            raw_output=raw_output,
            parsing_error=f"structured_output_validation_failed: {error}",
        )

    return ExtractionInvocation(
        proposal=proposal,
        raw_output=raw_output,
        parsing_error=None,
    )


def _json_safe(value: Any) -> Any:
    if isinstance(value, BaseMessage):
        return message_to_dict(value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "model_dump"):
        return _json_safe(value.model_dump(mode="json"))
    return repr(value)
