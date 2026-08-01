from dataclasses import dataclass
from datetime import date, datetime
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

For schema version 1:
- the assigned-work country is also the trip origin when the policy scopes workers based in that
  country and does not state a conflicting origin; and
- limiting manager approval to nonrefundable travel is representable. Do not mark a policy
  unsupported solely because of that modifier.

Fail closed. Mark the policy unsupported when it belongs to another family or when any material
construct cannot be represented exactly. Use unresolved findings for missing or conflicting facts.

Never invent an enterprise identifier. Extract only the human-readable training-course name.
Normalize represented values while keeping provenance quotes exactly as written:
- country names and abbreviations become two-letter uppercase codes (U.S. and United States
  become US; Canada becomes CA);
- when an exclusion names both sides of a route, include both countries (for example,
  "between the United States and Canada" becomes ["US", "CA"]);
- plural worker nouns become singular schema values (employees becomes employee; contractors
  becomes contractor);
- written dates become ISO 8601 dates with the source year preserved exactly; and
- a training name is the proper title only, without a surrounding generic word such as "course".

For every material field, return one exact zero-based [start, end) source span whose quote exactly
matches the policy text. Material provenance field_path must be exactly one of:
- policy_family
- candidate_rules.kind
- candidate_rules.schema_version
- candidate_rules.effective_date
- candidate_rules.worker_scope.assigned_work_country
- candidate_rules.worker_scope.worker_types
- candidate_rules.trip_scope.origin_country
- candidate_rules.trip_scope.excluded_destination_countries
- candidate_rules.manager_approval.booking_before_effective_date_is_exempt
- candidate_rules.security_training.course_name

Return exactly one provenance entry for each material path. Do not shorten a path, add array
indexes, or invent intermediate requirement paths. Finding provenance uses
finding.<finding_code>. Findings must also cite an exact source span."""

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
        proposal=_resolve_provenance_spans(proposal, policy_text),
        raw_output=raw_output,
        parsing_error=None,
    )


def _resolve_provenance_spans(
    proposal: PolicyExtractionProposal,
    policy_text: str,
) -> PolicyExtractionProposal:
    def resolve(entry: Any) -> Any:
        if policy_text[entry.start : entry.end] == entry.quote:
            return entry

        starts: list[int] = []
        offset = 0
        while (start := policy_text.find(entry.quote, offset)) >= 0:
            starts.append(start)
            offset = start + 1
        if not starts:
            return entry

        start = min(starts, key=lambda candidate: abs(candidate - entry.start))
        return entry.model_copy(update={"start": start, "end": start + len(entry.quote)})

    return proposal.model_copy(
        update={
            "provenance": tuple(resolve(entry) for entry in proposal.provenance),
            "findings": tuple(
                finding.model_copy(update={"provenance": resolve(finding.provenance)})
                for finding in proposal.findings
            ),
        }
    )


def _json_safe(value: Any) -> Any:
    if isinstance(value, BaseMessage):
        return _json_safe(message_to_dict(value))
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "model_dump"):
        return _json_safe(value.model_dump(mode="json"))
    return repr(value)
