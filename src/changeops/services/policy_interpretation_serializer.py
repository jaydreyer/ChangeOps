from changeops.ai.policy_interpreter import PROMPT_VERSION
from changeops.db.models import ImpactAssessment, PolicyAnalysisRun, PolicyExtractionAttempt
from changeops.domain.policy_interpretation import (
    INTERPRETATION_SCHEMA_VERSION,
    InterpretationAction,
    InterpretationEvidence,
    InterpretationFinding,
    InterpretationImpact,
    PolicyInterpretationInput,
)
from changeops.services.assessment_serializer import serialize_assessment


def build_policy_interpretation_input(
    assessment: ImpactAssessment,
    run: PolicyAnalysisRun,
    accepted_attempt: PolicyExtractionAttempt,
) -> PolicyInterpretationInput:
    response = serialize_assessment(assessment)
    clarifications = tuple(
        {
            "clarification_id": str(item.id),
            "question_code": item.question_code,
            "question_text": item.question_text,
            "answer": item.answer,
            "answer_provenance": item.answer_provenance,
        }
        for item in sorted(run.clarifications, key=lambda item: (item.question_code, str(item.id)))
        if item.status == "answered"
    )
    impacts = tuple(
        InterpretationImpact(
            id=item.id,
            assessment_id=assessment.id,
            domain=item.domain,
            object_type=item.object_type,
            source_key=item.source_key,
            display_name=item.display_name,
            classification=item.classification,
            explanation=item.explanation,
            reason_code=item.reason_code,
            evidence_keys=tuple(sorted(evidence.evidence_key for evidence in item.evidence)),
            relationship_path=tuple(
                {
                    "sequence": element.sequence,
                    "object_type": element.object_type,
                    "stable_key": element.stable_key,
                    "display_label": element.display_label,
                    "relationship_to_next": element.relationship_to_next,
                }
                for element in sorted(item.path_elements, key=lambda element: element.sequence)
            ),
        )
        for item in sorted(assessment.enterprise_impacts, key=lambda item: item.sort_key)
    )
    return PolicyInterpretationInput(
        policy_change_id=assessment.policy_change_id,
        policy_text=run.policy_text_snapshot,
        policy_analysis_run_id=run.id,
        accepted_extraction_attempt_id=accepted_attempt.id,
        accepted_rules=accepted_attempt.accepted_rules or {},
        accepted_source_provenance=tuple(
            sorted(run.accepted_rule_provenance, key=lambda item: str(item.get("field_path", "")))
        ),
        answered_clarifications=clarifications,
        impact_assessment_id=assessment.id,
        assessment_summary=response.summary.model_dump(mode="json"),
        impacts=impacts,
        findings=tuple(
            InterpretationFinding(
                id=item.id,
                rule_code=item.rule_code,
                finding_type=item.finding_type,
                severity=item.severity,
                explanation=item.explanation,
                evidence_keys=tuple(
                    sorted(evidence_item.evidence_key for evidence_item in item.evidence)
                ),
            )
            for item in sorted(
                assessment.findings,
                key=lambda item: (item.rule_code, str(item.id)),
            )
        ),
        evidence=tuple(
            InterpretationEvidence(
                id=item.id,
                evidence_key=item.evidence_key,
                evidence_type=item.evidence_type,
                source_type=item.source_type,
                source_id=item.source_id,
                label=item.label,
                snapshot=item.snapshot,
            )
            for item in sorted(assessment.evidence, key=lambda item: item.evidence_key)
        ),
        proposed_actions=tuple(
            InterpretationAction(
                id=item.id,
                enterprise_impact_id=item.enterprise_impact_id,
                action_type=item.action_type,
                target_type=item.target_type,
                target_identifier=item.target_identifier,
                description=item.description,
                due_date=item.due_date,
            )
            for item in sorted(
                assessment.proposed_actions,
                key=lambda item: (item.action_type, item.target_identifier, str(item.id)),
            )
        ),
        unresolved_questions=tuple(
            {"sequence": item.sequence, "question": item.question}
            for item in sorted(assessment.unresolved_questions, key=lambda item: item.sequence)
        ),
        prompt_version=PROMPT_VERSION,
        schema_version=INTERPRETATION_SCHEMA_VERSION,
    )
