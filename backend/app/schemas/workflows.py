from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


WorkflowName = Literal["chat_resume", "recommend_talent", "daily_recommendation"]


class WorkflowStartRequest(BaseModel):
    workflow_name: WorkflowName
    candidate_id: int | None = None
    job_id: int | None = None
    action_id: int | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class WorkflowReviewRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    note: str | None = Field(default=None, max_length=500)


class WorkflowStepRead(BaseModel):
    node: str
    status: str
    at: datetime
    candidate_id: int | None = None
    job_id: int | None = None
    action_id: int | None = None


class WorkflowRunRead(BaseModel):
    id: int
    workflow_name: str
    status: str
    current_node: str | None = None
    candidate_id: int | None = None
    candidate_name: str | None = None
    job_id: int | None = None
    job_title: str | None = None
    action_id: int | None = None
    review_note: str | None = None
    history: list[WorkflowStepRead] = Field(default_factory=list)
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
