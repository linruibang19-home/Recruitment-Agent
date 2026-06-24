from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


BrowserState = Literal["stopped", "starting", "ready", "login_required", "blocked", "error"]


class BrowserStatus(BaseModel):
    state: BrowserState
    running: bool
    current_url: str | None = None
    page_title: str | None = None
    detail: str | None = None


class ChatSummary(BaseModel):
    name: str
    preview: str | None = None
    unread_count: int = 0
    href: str | None = None
    raw_text: str


class AttachmentInfo(BaseModel):
    filename: str | None = None
    attachment_type: str
    preview_text: str | None = None
    href: str | None = None


class ChatDetail(BaseModel):
    candidate_name: str | None = None
    messages: list[str] = Field(default_factory=list)
    attachments: list[AttachmentInfo] = Field(default_factory=list)


class ChatScanRequest(BaseModel):
    limit: int = Field(default=10, ge=1, le=50)
    capture_screenshot: bool = True


class ChatOpenRequest(BaseModel):
    candidate_name: str = Field(min_length=1, max_length=100)
    capture_screenshot: bool = True


class ChatScanResult(BaseModel):
    scanned_at: datetime
    page_url: str
    conversations: list[ChatSummary]
    detail: ChatDetail | None = None
    screenshot_path: str | None = None


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action_type: str
    entity_type: str | None = None
    entity_id: int | None = None
    status: str
    detail: str | None = None
    screenshot_path: str | None = None
    payload: dict[str, Any]
    created_at: datetime
