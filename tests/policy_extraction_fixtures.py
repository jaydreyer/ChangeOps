from copy import deepcopy
from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from changeops.ai.policy_extractor import StructuredOutputModel
from changeops.domain.policy_extraction import PolicyExtractionProposal
from changeops.services.seed_service import POLICY_TEXT, PROPOSED_POLICY_TEXT


class FixtureStructuredOutputModel(StructuredOutputModel):
    def __init__(self, response: dict[str, Any]) -> None:
        self.response = response
        self.inputs: list[Any] = []
        self.schema: type[PolicyExtractionProposal] | None = None
        self.include_raw: bool | None = None

    def with_structured_output(
        self,
        schema: type[PolicyExtractionProposal],
        *,
        include_raw: bool,
    ) -> RunnableLambda:
        self.schema = schema
        self.include_raw = include_raw

        def respond(value: Any) -> dict[str, Any]:
            self.inputs.append(value)
            return self.response

        return RunnableLambda(respond)


def canonical_proposal_payload(
    policy_text: str = POLICY_TEXT,
    *,
    course_name: str = "International Travel Security",
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "policy_family": "international_travel",
        "support_status": "supported",
        "candidate_rules": {
            "kind": "international_travel",
            "schema_version": 1,
            "effective_date": "2026-09-01",
            "worker_scope": {
                "assigned_work_country": "US",
                "worker_types": ["employee", "contractor"],
            },
            "trip_scope": {
                "origin_country": "US",
                "excluded_destination_countries": ["US", "CA"],
            },
            "manager_approval": {
                "booking_before_effective_date_is_exempt": True,
            },
            "security_training": {"course_name": course_name},
        },
        "provenance": [],
        "findings": [],
    }
    quotes = {
        "policy_family": "traveling\ninternationally for business",
        "candidate_rules.kind": "traveling\ninternationally for business",
        "candidate_rules.schema_version": "traveling\ninternationally for business",
        "candidate_rules.effective_date": "Effective September 1, 2026",
        "candidate_rules.worker_scope.assigned_work_country": "U.S.-based",
        "candidate_rules.worker_scope.worker_types": "employees and contractors",
        "candidate_rules.trip_scope.origin_country": "United States",
        "candidate_rules.trip_scope.excluded_destination_countries": ("United States and Canada"),
        "candidate_rules.manager_approval.booking_before_effective_date_is_exempt": (
            "Travel booked before September 1, 2026 is exempt"
        ),
        "candidate_rules.security_training.course_name": course_name,
    }
    payload["provenance"] = [
        provenance(policy_text, field_path, quote) for field_path, quote in quotes.items()
    ]
    return payload


def proposed_revision_payload() -> dict[str, Any]:
    payload: dict[str, Any] = {
        "policy_family": "international_travel",
        "support_status": "supported",
        "candidate_rules": {
            "kind": "international_travel",
            "schema_version": 1,
            "effective_date": "2026-10-01",
            "worker_scope": {
                "assigned_work_country": "US",
                "worker_types": ["employee"],
            },
            "trip_scope": {
                "origin_country": "US",
                "excluded_destination_countries": ["US", "CA", "MX"],
            },
            "manager_approval": {
                "booking_before_effective_date_is_exempt": True,
            },
            "security_training": {"course_name": "International Travel Security"},
        },
        "provenance": [],
        "findings": [],
    }
    quotes = {
        "policy_family": "traveling\ninternationally for business",
        "candidate_rules.kind": "traveling\ninternationally for business",
        "candidate_rules.schema_version": "traveling\ninternationally for business",
        "candidate_rules.effective_date": "Effective October 1, 2026",
        "candidate_rules.worker_scope.assigned_work_country": "U.S.-based",
        "candidate_rules.worker_scope.worker_types": "employees",
        "candidate_rules.trip_scope.origin_country": "United States",
        "candidate_rules.trip_scope.excluded_destination_countries": (
            "United States, Canada, and Mexico"
        ),
        "candidate_rules.manager_approval.booking_before_effective_date_is_exempt": (
            "Travel booked before October 1, 2026 is exempt"
        ),
        "candidate_rules.security_training.course_name": "International Travel Security",
    }
    payload["provenance"] = [
        provenance(PROPOSED_POLICY_TEXT, field_path, quote) for field_path, quote in quotes.items()
    ]
    return payload


def accepted_model_response(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "raw": AIMessage(content="fixture structured output"),
        "parsed": PolicyExtractionProposal.model_validate(deepcopy(payload)),
        "parsing_error": None,
    }


def provenance(policy_text: str, field_path: str, quote: str) -> dict[str, Any]:
    start = policy_text.index(quote)
    return {
        "field_path": field_path,
        "start": start,
        "end": start + len(quote),
        "quote": quote,
    }
