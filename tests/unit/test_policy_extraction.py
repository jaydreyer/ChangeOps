from copy import deepcopy
from datetime import date

import pytest
from langchain_core.messages import AIMessage
from pydantic import ValidationError

from changeops.ai.policy_extractor import invoke_policy_extractor
from changeops.domain.policy_extraction import (
    PolicyExtractionProposal,
    TrainingCourseReference,
)
from changeops.domain.policy_extraction_validation import validate_policy_extraction
from changeops.services.seed_service import POLICY_TEXT, STRUCTURED_RULES
from tests.policy_extraction_fixtures import (
    FixtureStructuredOutputModel,
    accepted_model_response,
    canonical_proposal_payload,
)

COURSES = (
    TrainingCourseReference(
        identifier="international-travel-security",
        name="International Travel Security",
        active=True,
    ),
)


def test_langchain_structured_output_extracts_typed_proposal_without_enterprise_context() -> None:
    payload = canonical_proposal_payload()
    model = FixtureStructuredOutputModel(accepted_model_response(payload))

    invocation = invoke_policy_extractor(model, POLICY_TEXT)

    assert invocation.proposal == PolicyExtractionProposal.model_validate(payload)
    assert invocation.parsing_error is None
    assert model.schema is PolicyExtractionProposal
    assert model.include_raw is True
    messages = model.inputs[0].to_messages()
    rendered_prompt = "\n".join(str(message.content) for message in messages)
    assert POLICY_TEXT in rendered_prompt
    assert "international-travel-security" not in rendered_prompt
    assert "Sarah Johnson" not in rendered_prompt
    assert "candidate_rules.security_training.course_name" in rendered_prompt
    assert "Do not shorten a path" in rendered_prompt
    assert "assigned-work country is also the trip origin" in rendered_prompt
    assert "nonrefundable travel is representable" in rendered_prompt


def test_material_provenance_rejects_noncanonical_field_paths() -> None:
    payload = canonical_proposal_payload()
    payload["provenance"][0]["field_path"] = "effective_date"

    with pytest.raises(ValidationError):
        PolicyExtractionProposal.model_validate(payload)


def test_extractor_resolves_exact_quotes_to_nearest_source_spans() -> None:
    payload = canonical_proposal_payload()
    course_entry = next(
        item
        for item in payload["provenance"]
        if item["field_path"] == "candidate_rules.security_training.course_name"
    )
    second_course_start = POLICY_TEXT.rindex(course_entry["quote"])
    course_entry.update(
        {
            "start": second_course_start + 3,
            "end": second_course_start + 3 + len(course_entry["quote"]),
        }
    )
    model = FixtureStructuredOutputModel(accepted_model_response(payload))

    invocation = invoke_policy_extractor(model, POLICY_TEXT)

    assert invocation.proposal is not None
    resolved_entry = next(
        item
        for item in invocation.proposal.provenance
        if item.field_path == "candidate_rules.security_training.course_name"
    )
    assert resolved_entry.start == second_course_start
    assert resolved_entry.end == second_course_start + len(resolved_entry.quote)


@pytest.mark.parametrize(
    ("field_path", "raw_value"),
    [
        ("worker_scope.assigned_work_country", "U.S.-based"),
        ("worker_scope.worker_types", ["employees", "contractors"]),
        ("trip_scope.origin_country", "United States"),
        ("trip_scope.excluded_destination_countries", ["United States", "Canada"]),
    ],
)
def test_candidate_rules_reject_unnormalized_values(
    field_path: str,
    raw_value: str | list[str],
) -> None:
    payload = canonical_proposal_payload()
    section, field = field_path.split(".")
    payload["candidate_rules"][section][field] = raw_value

    with pytest.raises(ValidationError):
        PolicyExtractionProposal.model_validate(payload)


def test_validation_resolves_course_name_and_accepts_rules() -> None:
    proposal = PolicyExtractionProposal.model_validate(canonical_proposal_payload())

    result = validate_policy_extraction(
        proposal,
        policy_text=POLICY_TEXT,
        policy_effective_date=date(2026, 9, 1),
        training_courses=COURSES,
    )

    assert result.outcome == "accepted"
    assert result.issues == ()
    assert result.accepted_rules is not None
    assert result.accepted_rules.model_dump(mode="json") == STRUCTURED_RULES


def test_invalid_provenance_fails_validation() -> None:
    payload = canonical_proposal_payload()
    payload["provenance"][0]["start"] += 1
    proposal = PolicyExtractionProposal.model_validate(payload)

    result = validate_policy_extraction(
        proposal,
        policy_text=POLICY_TEXT,
        policy_effective_date=date(2026, 9, 1),
        training_courses=COURSES,
    )

    assert result.outcome == "validation_failed"
    assert {issue.code for issue in result.issues} == {"invalid_provenance_span"}
    assert result.accepted_rules is None


def test_unresolvable_course_name_fails_closed() -> None:
    payload = canonical_proposal_payload()
    payload["candidate_rules"]["security_training"]["course_name"] = "Invented Course"
    course_provenance = next(
        item
        for item in payload["provenance"]
        if item["field_path"] == "candidate_rules.security_training.course_name"
    )
    course_provenance.update(
        {
            "start": POLICY_TEXT.index("International Travel Security"),
            "end": POLICY_TEXT.index("International Travel Security")
            + len("International Travel Security"),
            "quote": "International Travel Security",
        }
    )
    proposal = PolicyExtractionProposal.model_validate(payload)

    result = validate_policy_extraction(
        proposal,
        policy_text=POLICY_TEXT,
        policy_effective_date=date(2026, 9, 1),
        training_courses=COURSES,
    )

    assert result.outcome == "validation_failed"
    assert [issue.code for issue in result.issues] == ["training_course_not_found"]


def test_invalid_exception_behavior_is_not_coerced() -> None:
    payload = canonical_proposal_payload()
    payload["candidate_rules"]["manager_approval"]["booking_before_effective_date_is_exempt"] = (
        False
    )
    proposal = PolicyExtractionProposal.model_validate(payload)

    result = validate_policy_extraction(
        proposal,
        policy_text=POLICY_TEXT,
        policy_effective_date=date(2026, 9, 1),
        training_courses=COURSES,
    )

    assert result.outcome == "validation_failed"
    assert "unsupported_exception_behavior" in {issue.code for issue in result.issues}


def test_explicit_non_material_ambiguity_does_not_block_accepted_rules() -> None:
    payload = canonical_proposal_payload()
    quote = "business"
    start = POLICY_TEXT.index(quote)
    payload["findings"] = [
        {
            "kind": "unresolved",
            "code": "non_material_ambiguity",
            "message": "Wording does not affect a schema field.",
            "field_path": None,
            "provenance": {
                "field_path": "finding.non_material_ambiguity",
                "start": start,
                "end": start + len(quote),
                "quote": quote,
            },
        }
    ]

    result = validate_policy_extraction(
        PolicyExtractionProposal.model_validate(payload),
        policy_text=POLICY_TEXT,
        policy_effective_date=date(2026, 9, 1),
        training_courses=COURSES,
    )

    assert result.outcome == "accepted"
    assert result.accepted_rules is not None


def test_malformed_structured_output_is_explicit_failure() -> None:
    response = {
        "raw": {"content": "{not-json"},
        "parsed": None,
        "parsing_error": ValueError("invalid JSON"),
    }
    model = FixtureStructuredOutputModel(response)

    result = invoke_policy_extractor(model, POLICY_TEXT)

    assert result.proposal is None
    assert result.raw_output == {"content": "{not-json"}
    assert result.parsing_error is not None
    assert result.parsing_error.startswith("structured_output_parsing_failed:")


def test_raw_model_metadata_dates_are_json_safe() -> None:
    payload = canonical_proposal_payload()
    model = FixtureStructuredOutputModel(
        {
            "raw": AIMessage(
                content="fixture",
                response_metadata={"provider_date": date(2026, 8, 1)},
            ),
            "parsed": PolicyExtractionProposal.model_validate(payload),
            "parsing_error": None,
        }
    )

    result = invoke_policy_extractor(model, POLICY_TEXT)

    assert result.raw_output["data"]["response_metadata"]["provider_date"] == "2026-08-01"


def test_invalid_closed_literal_is_a_structured_output_failure() -> None:
    payload = canonical_proposal_payload()
    payload["candidate_rules"]["kind"] = "general_travel"
    model = FixtureStructuredOutputModel(
        {
            "raw": {"content": "invalid literal fixture"},
            "parsed": payload,
            "parsing_error": None,
        }
    )

    result = invoke_policy_extractor(model, POLICY_TEXT)

    assert result.proposal is None
    assert result.parsing_error is not None
    assert result.parsing_error.startswith("structured_output_validation_failed:")


def test_unsupported_policy_family_fails_closed() -> None:
    payload = deepcopy(canonical_proposal_payload())
    payload["policy_family"] = "domestic_expense"
    payload["support_status"] = "unsupported"
    payload["candidate_rules"] = None
    family_quote = "traveling\ninternationally for business"
    payload["provenance"] = [
        item for item in payload["provenance"] if item["field_path"] == "policy_family"
    ]
    payload["findings"] = [
        {
            "kind": "unsupported",
            "code": "unsupported_policy_family",
            "message": "Domestic expense policy is unsupported.",
            "field_path": "policy_family",
            "provenance": {
                **payload["provenance"][0],
                "field_path": "finding.unsupported_policy_family",
                "quote": family_quote,
            },
        }
    ]
    proposal = PolicyExtractionProposal.model_validate(payload)

    result = validate_policy_extraction(
        proposal,
        policy_text=POLICY_TEXT,
        policy_effective_date=date(2026, 9, 1),
        training_courses=COURSES,
    )

    assert result.outcome == "unsupported"
    assert result.accepted_rules is None
