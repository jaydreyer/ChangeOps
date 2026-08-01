import uuid
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from changeops.ai.policy_extractor import ConfiguredExtractionModel
from changeops.services.policy_analysis_service import (
    apply_answered_clarification,
    create_assessment_for_run,
    evaluate_run_extraction,
    extract_for_run,
    fail_run_from_exception,
    finalize_run,
    load_run_route,
    persist_material_clarification,
)

GraphRoute = Literal[
    "extract",
    "evaluate",
    "clarify",
    "apply_clarification",
    "assessment",
    "retry",
    "pause",
    "terminal",
    "fail",
]


class PolicyAnalysisGraphState(TypedDict, total=False):
    run_id: str
    latest_extraction_attempt_id: str | None
    clarification_id: str | None
    assessment_id: str | None
    retry_count: int
    failure_code: str | None
    route: GraphRoute


def execute_policy_analysis(
    session: Session,
    run_id: uuid.UUID,
    configured_model: ConfiguredExtractionModel,
) -> None:
    graph = _build_graph(session, configured_model)
    try:
        graph.invoke({"run_id": str(run_id)})
    except Exception as error:
        fail_run_from_exception(
            session,
            run_id,
            f"{type(error).__name__}: {error}",
        )


def _build_graph(
    session: Session,
    configured_model: ConfiguredExtractionModel,
):
    def load(state: PolicyAnalysisGraphState) -> PolicyAnalysisGraphState:
        route = load_run_route(session, uuid.UUID(state["run_id"]))
        session.rollback()
        return {"route": route}

    def extract(state: PolicyAnalysisGraphState) -> PolicyAnalysisGraphState:
        attempt = extract_for_run(session, uuid.UUID(state["run_id"]), configured_model)
        return {
            "latest_extraction_attempt_id": str(attempt.id),
            "route": "evaluate",
        }

    def evaluate(state: PolicyAnalysisGraphState) -> PolicyAnalysisGraphState:
        decision = evaluate_run_extraction(session, uuid.UUID(state["run_id"]))
        route_by_decision: dict[str, GraphRoute] = {
            "accepted": "assessment",
            "unsupported": "terminal",
            "clarify": "clarify",
            "retry": "retry",
            "fail": "terminal",
        }
        return {
            "route": route_by_decision[decision.route],
            "failure_code": decision.failure_code,
        }

    def clarify(state: PolicyAnalysisGraphState) -> PolicyAnalysisGraphState:
        clarification = persist_material_clarification(session, uuid.UUID(state["run_id"]))
        return {"clarification_id": str(clarification.id), "route": "pause"}

    def apply_clarification(state: PolicyAnalysisGraphState) -> PolicyAnalysisGraphState:
        attempt = apply_answered_clarification(session, uuid.UUID(state["run_id"]))
        return {
            "latest_extraction_attempt_id": str(attempt.id),
            "route": "assessment",
        }

    def create_assessment(state: PolicyAnalysisGraphState) -> PolicyAnalysisGraphState:
        assessment_id = create_assessment_for_run(session, uuid.UUID(state["run_id"]))
        return {"assessment_id": str(assessment_id), "route": "terminal"}

    def finalize(state: PolicyAnalysisGraphState) -> PolicyAnalysisGraphState:
        finalize_run(session, uuid.UUID(state["run_id"]))
        return {"route": "terminal"}

    workflow = StateGraph(PolicyAnalysisGraphState)
    workflow.add_node("load", load)
    workflow.add_node("extract", extract)
    workflow.add_node("evaluate", evaluate)
    workflow.add_node("clarify", clarify)
    workflow.add_node("apply_clarification", apply_clarification)
    workflow.add_node("create_assessment", create_assessment)
    workflow.add_node("finalize", finalize)
    workflow.add_edge(START, "load")
    workflow.add_conditional_edges(
        "load",
        lambda state: state["route"],
        {
            "extract": "extract",
            "evaluate": "evaluate",
            "apply_clarification": "apply_clarification",
            "pause": END,
            "terminal": END,
        },
    )
    workflow.add_edge("extract", "evaluate")
    workflow.add_conditional_edges(
        "evaluate",
        lambda state: state["route"],
        {
            "assessment": "create_assessment",
            "clarify": "clarify",
            "retry": "extract",
            "terminal": END,
        },
    )
    workflow.add_edge("clarify", END)
    workflow.add_conditional_edges(
        "apply_clarification",
        lambda state: state["route"],
        {"assessment": "create_assessment"},
    )
    workflow.add_edge("create_assessment", "finalize")
    workflow.add_edge("finalize", END)
    return workflow.compile()
