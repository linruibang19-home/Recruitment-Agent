from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import ActionQueueItem, Candidate, Job, WorkflowRun
from app.db.repositories import audit_logs as audit_repo
from app.schemas.workflows import WorkflowRunRead, WorkflowStartRequest
from app.services.candidate_pipeline import refresh_candidate_pipeline_status
from app.workflows.engine import WORKFLOW_GRAPHS, WORKFLOW_NODES, WorkflowState


class WorkflowServiceError(RuntimeError):
    pass


def _validate_entities(db: Session, request: WorkflowStartRequest) -> None:
    if request.candidate_id is not None and not db.get(Candidate, request.candidate_id):
        raise WorkflowServiceError("Candidate not found")
    if request.job_id is not None and not db.get(Job, request.job_id):
        raise WorkflowServiceError("Job not found")
    if request.action_id is not None and not db.get(ActionQueueItem, request.action_id):
        raise WorkflowServiceError("Action not found")
    if request.workflow_name == "chat_resume" and request.candidate_id is None:
        raise WorkflowServiceError("chat_resume requires candidate_id")
    if request.workflow_name in {"recommend_talent", "daily_recommendation"} and request.job_id is None:
        raise WorkflowServiceError(f"{request.workflow_name} requires job_id")


def _state_from_run(run: WorkflowRun) -> WorkflowState:
    return {
        "run_id": run.id,
        "workflow_name": run.workflow_name,
        "status": run.status,
        "current_node": run.current_node or WORKFLOW_NODES[run.workflow_name][0],
        **(run.state_json or {}),
    }


def _save_state(db: Session, run: WorkflowRun, state: WorkflowState) -> None:
    run.status = state["status"]
    run.current_node = state.get("current_node")
    run.state_json = {
        "candidate_id": state.get("candidate_id"),
        "job_id": state.get("job_id"),
        "action_id": state.get("action_id"),
        "payload": state.get("payload") or {},
        "history": state.get("history") or [],
        "review_decision": state.get("review_decision"),
        "review_note": state.get("review_note"),
    }
    run.error_message = None
    db.commit()
    db.refresh(run)


def _advance_until_pause(db: Session, run: WorkflowRun) -> WorkflowRun:
    graph = WORKFLOW_GRAPHS[run.workflow_name]
    max_steps = len(WORKFLOW_NODES[run.workflow_name]) + 1
    for _ in range(max_steps):
        state = _state_from_run(run)
        if state["status"] in {"waiting_review", "completed", "rejected"}:
            break
        try:
            next_state = graph.invoke(state)
            _save_state(db, run, next_state)
        except Exception as exc:
            db.rollback()
            run = db.get(WorkflowRun, run.id)
            run.status = "failed"
            run.error_message = f"{type(exc).__name__}: {exc}"
            db.commit()
            db.refresh(run)
            audit_repo.create_audit_log(
                db,
                action_type="workflow_failed",
                status="failed",
                detail=run.error_message,
                payload={"workflow_run_id": run.id, "workflow_name": run.workflow_name},
            )
            break
    return run


def start_workflow(db: Session, request: WorkflowStartRequest) -> WorkflowRun:
    _validate_entities(db, request)
    idempotency_key = request.payload.get("idempotency_key")
    if idempotency_key:
        existing = db.scalar(
            select(WorkflowRun)
            .where(
                WorkflowRun.workflow_name == request.workflow_name,
                WorkflowRun.state_json["payload"]["idempotency_key"].astext
                == str(idempotency_key),
            )
            .order_by(WorkflowRun.created_at.desc())
        )
        if existing:
            return existing
    first_node = WORKFLOW_NODES[request.workflow_name][0]
    run = WorkflowRun(
        workflow_name=request.workflow_name,
        status="running",
        current_node=first_node,
        state_json={
            "candidate_id": request.candidate_id,
            "job_id": request.job_id,
            "action_id": request.action_id,
            "payload": request.payload,
            "history": [],
            "review_decision": None,
            "review_note": None,
        },
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    run = _advance_until_pause(db, run)
    audit_repo.create_audit_log(
        db,
        action_type="workflow_started",
        status="ok",
        detail=f"{request.workflow_name} workflow {run.id} started",
        payload={"workflow_run_id": run.id, "status": run.status},
    )
    return db.get(WorkflowRun, run.id)


def start_workflow_safely(db: Session, request: WorkflowStartRequest) -> WorkflowRun | None:
    try:
        return start_workflow(db, request)
    except Exception as exc:
        db.rollback()
        audit_repo.create_audit_log(
            db,
            action_type="workflow_create_failed",
            status="failed",
            detail=f"{type(exc).__name__}: {exc}",
            payload=request.model_dump(),
        )
        return None


def review_workflow(
    db: Session,
    run: WorkflowRun,
    *,
    decision: str,
    note: str | None,
) -> WorkflowRun:
    if run.status != "waiting_review" or run.current_node != "human_review":
        raise WorkflowServiceError("Only workflows waiting for review can be resumed")
    state = dict(run.state_json or {})
    action_id = state.get("action_id")
    if action_id is not None:
        action = db.get(ActionQueueItem, action_id)
        if not action:
            raise WorkflowServiceError("Action not found")
        if action.status == "pending":
            action.status = decision
            action.payload = {
                **(action.payload or {}),
                "review_note": note,
                "workflow_run_id": run.id,
                "reviewed_at": datetime.now(timezone.utc).isoformat(),
            }
            if action.candidate and action.action_type == "interview_invite":
                action.candidate.status = (
                    "interview_invite_pending" if decision == "approved" else "scored"
                )
                refresh_candidate_pipeline_status(db, action.candidate)
        elif action.status != decision:
            raise WorkflowServiceError(f"Action is already {action.status}")
    run.status = "running"
    run.state_json = {
        **state,
        "review_decision": decision,
        "review_note": note,
    }
    db.commit()
    db.refresh(run)
    run = _advance_until_pause(db, run)
    audit_repo.create_audit_log(
        db,
        action_type=f"workflow_{decision}",
        status="ok",
        detail=f"Workflow {run.id} review: {decision}",
        payload={"workflow_run_id": run.id, "action_id": action_id, "note": note},
    )
    return db.get(WorkflowRun, run.id)


def retry_workflow(db: Session, run: WorkflowRun) -> WorkflowRun:
    if run.status != "failed":
        raise WorkflowServiceError("Only failed workflows can be retried")
    run.status = "running"
    run.error_message = None
    db.commit()
    db.refresh(run)
    return _advance_until_pause(db, run)


def list_workflow_runs(
    db: Session,
    *,
    status: str | None,
    limit: int,
    offset: int,
) -> tuple[list[WorkflowRun], int]:
    stmt = select(WorkflowRun)
    count_stmt = select(func.count()).select_from(WorkflowRun)
    if status:
        stmt = stmt.where(WorkflowRun.status == status)
        count_stmt = count_stmt.where(WorkflowRun.status == status)
    total = db.scalar(count_stmt) or 0
    items = list(
        db.scalars(stmt.order_by(WorkflowRun.created_at.desc()).limit(limit).offset(offset))
    )
    return items, total


def workflow_read(db: Session, run: WorkflowRun) -> WorkflowRunRead:
    state: dict[str, Any] = run.state_json or {}
    candidate = db.get(Candidate, state.get("candidate_id")) if state.get("candidate_id") else None
    job = db.get(Job, state.get("job_id")) if state.get("job_id") else None
    return WorkflowRunRead(
        id=run.id,
        workflow_name=run.workflow_name,
        status=run.status,
        current_node=run.current_node,
        candidate_id=state.get("candidate_id"),
        candidate_name=candidate.name if candidate else None,
        job_id=state.get("job_id"),
        job_title=job.title if job else None,
        action_id=state.get("action_id"),
        review_note=state.get("review_note"),
        history=state.get("history") or [],
        error_message=run.error_message,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )
