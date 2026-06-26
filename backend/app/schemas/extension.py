from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


CommandType = Literal[
    "scan_chats",
    "scan_chat_details",
    "request_resumes_batch",
    "read_current_chat",
    "scan_talents",
]
CommandControl = Literal["running", "paused", "stopped"]


class ExtensionHeartbeat(BaseModel):
    extension_id: str = Field(min_length=8, max_length=100)
    page_url: str | None = None
    page_title: str | None = None
    page_type: str | None = None
    status: Literal["online", "unsupported_page", "error"] = "online"
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExtensionCommandCreate(BaseModel):
    command_type: CommandType
    payload: dict[str, Any] = Field(default_factory=dict)


class ExtensionCommandControl(BaseModel):
    control: CommandControl


class ExtensionCommandControlRead(BaseModel):
    command_id: int
    control: CommandControl = "running"


class ExtensionCommandResult(BaseModel):
    extension_id: str = Field(min_length=8, max_length=100)
    result: dict[str, Any] = Field(default_factory=dict)


class ExtensionCommandFailure(BaseModel):
    extension_id: str = Field(min_length=8, max_length=100)
    error_message: str = Field(min_length=1, max_length=2000)


class ExtensionCommandRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    extension_id: str | None = None
    command_type: CommandType
    status: str
    payload: dict[str, Any]
    result: dict[str, Any]
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    claimed_at: datetime | None = None
    completed_at: datetime | None = None


class ExtensionStatusRead(BaseModel):
    connected: bool
    extension_id: str | None = None
    status: str = "offline"
    page_url: str | None = None
    page_title: str | None = None
    page_type: str | None = None
    last_seen_at: datetime | None = None
    recent_commands: list[ExtensionCommandRead] = Field(default_factory=list)


class ExtensionCompleteRead(BaseModel):
    command: ExtensionCommandRead
    candidate_id: int | None = None
    attachment_urls: list[str] = Field(default_factory=list)
    attachment_uploads: list[dict[str, Any]] = Field(default_factory=list)
