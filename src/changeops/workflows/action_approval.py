import uuid
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from changeops.services.action_approval_service import (
    evaluate_action_approval_run,
    get_action_approval_run,
    initialize_action_approval_run,
    record_action_approval_failure,
)

ApprovalGraphRoute = Literal["initialize", "evaluate", "terminal"]


class ActionApprovalGraphState(TypedDict, total=False):
    approval_run_id: str
    pending_count: int
    route: ApprovalGraphRoute
    trigger_type: str
    trigger_reference: str | None
    actor_identity: str | None


def execute_action_approval(
    session: Session,
    run_id: uuid.UUID,
    *,
    trigger_type: str,
    trigger_reference: str | None = None,
    actor_identity: str | None = None,
) -> None:
    graph = _build_graph(session)
    try:
        graph.invoke(
            {
                "approval_run_id": str(run_id),
                "trigger_type": trigger_type,
                "trigger_reference": trigger_reference,
                "actor_identity": actor_identity,
            }
        )
    except Exception as error:
        record_action_approval_failure(
            session,
            run_id,
            error,
            phase="initialize" if trigger_type == "run_created" else "resume",
        )


def _build_graph(session: Session):
    def load(state: ActionApprovalGraphState) -> ActionApprovalGraphState:
        run = get_action_approval_run(session, uuid.UUID(state["approval_run_id"]))
        if run.status == "initializing":
            route: ApprovalGraphRoute = (
                "initialize" if run.current_step == "create_reviews" else "evaluate"
            )
        elif run.status == "awaiting_decisions":
            route = "evaluate"
        else:
            route = "terminal"
        session.rollback()
        return {"route": route}

    def initialize(state: ActionApprovalGraphState) -> ActionApprovalGraphState:
        progress = initialize_action_approval_run(
            session,
            uuid.UUID(state["approval_run_id"]),
        )
        return {
            "pending_count": progress.pending,
            "route": "evaluate",
            "trigger_type": "initialized",
        }

    def evaluate(state: ActionApprovalGraphState) -> ActionApprovalGraphState:
        progress = evaluate_action_approval_run(
            session,
            uuid.UUID(state["approval_run_id"]),
            trigger_type=state["trigger_type"],
            trigger_reference=state.get("trigger_reference"),
            actor_identity=state.get("actor_identity"),
        )
        return {"pending_count": progress.pending, "route": "terminal"}

    workflow = StateGraph(ActionApprovalGraphState)
    workflow.add_node("load", load)
    workflow.add_node("initialize_reviews", initialize)
    workflow.add_node("evaluate_reviews", evaluate)
    workflow.add_edge(START, "load")
    workflow.add_conditional_edges(
        "load",
        lambda state: state["route"],
        {
            "initialize": "initialize_reviews",
            "evaluate": "evaluate_reviews",
            "terminal": END,
        },
    )
    workflow.add_edge("initialize_reviews", "evaluate_reviews")
    workflow.add_edge("evaluate_reviews", END)
    return workflow.compile()
