from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph


class WorkflowState(TypedDict, total=False):
    run_id: int
    workflow_name: str
    current_node: str
    status: str
    candidate_id: int | None
    job_id: int | None
    action_id: int | None
    payload: dict[str, Any]
    history: list[dict[str, Any]]
    review_decision: str | None
    review_note: str | None


WORKFLOW_NODES: dict[str, list[str]] = {
    "chat_resume": [
        "load_conversation",
        "extract_candidate",
        "detect_resume",
        "parse_resume",
        "profile_candidate",
        "score_candidate",
        "decide_action",
        "human_review",
        "record_result",
    ],
    "recommend_talent": [
        "load_recommend_page",
        "apply_filters",
        "extract_cards",
        "dedupe",
        "pre_score",
        "quota_check",
        "draft_greeting",
        "human_review",
        "record_result",
    ],
    "daily_recommendation": [
        "load_candidates",
        "rank",
        "generate_reasons",
        "draft_interview_invites",
        "save_report",
        "human_review",
        "notify",
    ],
}


def _step_entry(
    node_name: str,
    state: WorkflowState,
    *,
    status: str = "completed",
) -> dict[str, Any]:
    return {
        "node": node_name,
        "status": status,
        "at": datetime.now(timezone.utc).isoformat(),
        "candidate_id": state.get("candidate_id"),
        "job_id": state.get("job_id"),
        "action_id": state.get("action_id"),
    }


def _build_step_node(node_name: str, next_node: str | None):
    def run(state: WorkflowState) -> WorkflowState:
        if node_name == "human_review":
            decision = state.get("review_decision")
            if decision not in {"approved", "rejected"}:
                return {
                    **state,
                    "status": "waiting_review",
                    "current_node": node_name,
                    "history": [
                        *(state.get("history") or []),
                        _step_entry(node_name, state, status="waiting_review"),
                    ],
                }
        history = [*(state.get("history") or []), _step_entry(node_name, state)]
        if node_name == "human_review":
            decision = state.get("review_decision")
            if decision == "rejected":
                return {
                    **state,
                    "status": "rejected",
                    "current_node": node_name,
                    "history": history,
                }
        return {
            **state,
            "status": "completed" if next_node is None else "running",
            "current_node": next_node or node_name,
            "history": history,
        }

    return run


def build_step_graph(workflow_name: str):
    nodes = WORKFLOW_NODES[workflow_name]
    graph = StateGraph(WorkflowState)
    graph.add_node("dispatch", lambda state: state)
    graph.add_edge(START, "dispatch")
    graph.add_conditional_edges(
        "dispatch",
        lambda state: state["current_node"],
        {node_name: node_name for node_name in nodes},
    )
    for index, node_name in enumerate(nodes):
        next_node = nodes[index + 1] if index + 1 < len(nodes) else None
        graph.add_node(node_name, _build_step_node(node_name, next_node))
        graph.add_edge(node_name, END)
    return graph.compile()


WORKFLOW_GRAPHS = {
    workflow_name: build_step_graph(workflow_name) for workflow_name in WORKFLOW_NODES
}
