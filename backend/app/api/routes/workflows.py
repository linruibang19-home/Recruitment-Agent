from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.models import WorkflowRun
from app.db.session import get_db
from app.schemas.common import PageResponse
from app.schemas.workflows import WorkflowReviewRequest, WorkflowRunRead, WorkflowStartRequest
from app.services.workflow_service import (
    WorkflowServiceError,
    list_workflow_runs,
    retry_workflow,
    review_workflow,
    start_workflow,
    workflow_read,
)

router = APIRouter(prefix="/workflows", tags=["workflows"])


def _get_run(db: Session, run_id: int) -> WorkflowRun:
    run = db.get(WorkflowRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    return run


@router.get("", response_model=PageResponse[WorkflowRunRead])
def get_workflow_runs(
    workflow_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> PageResponse[WorkflowRunRead]:
    items, total = list_workflow_runs(
        db,
        status=workflow_status,
        limit=limit,
        offset=offset,
    )
    return PageResponse(
        items=[workflow_read(db, item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{run_id}", response_model=WorkflowRunRead)
def get_workflow_run(run_id: int, db: Session = Depends(get_db)) -> WorkflowRunRead:
    return workflow_read(db, _get_run(db, run_id))


@router.post("", response_model=WorkflowRunRead, status_code=status.HTTP_201_CREATED)
def create_workflow(
    payload: WorkflowStartRequest,
    db: Session = Depends(get_db),
) -> WorkflowRunRead:
    try:
        return workflow_read(db, start_workflow(db, payload))
    except WorkflowServiceError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{run_id}/review", response_model=WorkflowRunRead)
def decide_workflow(
    run_id: int,
    payload: WorkflowReviewRequest,
    db: Session = Depends(get_db),
) -> WorkflowRunRead:
    try:
        run = review_workflow(
            db,
            _get_run(db, run_id),
            decision=payload.decision,
            note=payload.note,
        )
        return workflow_read(db, run)
    except WorkflowServiceError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{run_id}/retry", response_model=WorkflowRunRead)
def retry_failed_workflow(run_id: int, db: Session = Depends(get_db)) -> WorkflowRunRead:
    try:
        return workflow_read(db, retry_workflow(db, _get_run(db, run_id)))
    except WorkflowServiceError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
