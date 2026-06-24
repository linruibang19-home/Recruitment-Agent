import pytest

from app.browser.session import _BrowserWorker
from app.workflows.engine import WORKFLOW_GRAPHS, WORKFLOW_NODES


@pytest.mark.parametrize("workflow_name", list(WORKFLOW_NODES))
def test_workflow_pauses_for_human_review(workflow_name: str) -> None:
    state = {
        "run_id": 1,
        "workflow_name": workflow_name,
        "status": "running",
        "current_node": WORKFLOW_NODES[workflow_name][0],
        "history": [],
        "payload": {},
    }
    graph = WORKFLOW_GRAPHS[workflow_name]
    for _ in WORKFLOW_NODES[workflow_name]:
        state = graph.invoke(state)
        if state["status"] == "waiting_review":
            break
    assert state["status"] == "waiting_review"
    assert state["current_node"] == "human_review"
    assert state["history"][-1]["status"] == "waiting_review"


def test_workflow_approval_continues_after_review() -> None:
    graph = WORKFLOW_GRAPHS["daily_recommendation"]
    state = {
        "run_id": 1,
        "workflow_name": "daily_recommendation",
        "status": "running",
        "current_node": "human_review",
        "history": [],
        "payload": {},
        "review_decision": "approved",
    }
    result = graph.invoke(state)
    assert result["status"] == "running"
    assert result["current_node"] == "notify"


def test_browser_worker_blocks_after_configured_failures(monkeypatch) -> None:
    worker = _BrowserWorker()
    monkeypatch.setattr(
        "app.browser.session.settings.stop_after_automation_failures",
        3,
    )
    for _ in range(3):
        worker._record_operation_failure(RuntimeError("page changed"))
    assert worker._state == "blocked"
    assert worker._consecutive_failures == 3
