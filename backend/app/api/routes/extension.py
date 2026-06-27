from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ExtensionCommand
from app.db.session import get_db
from app.schemas.extension import (
    ExtensionCommandControl,
    ExtensionCommandControlRead,
    ExtensionCommandCreate,
    ExtensionCommandFailure,
    ExtensionCommandRead,
    ExtensionCommandResult,
    ExtensionCompleteRead,
    ExtensionHeartbeat,
    ExtensionStatusRead,
)
from app.services import extension_service

router = APIRouter(prefix="/extension", tags=["extension"])


@router.post("/heartbeat", status_code=status.HTTP_204_NO_CONTENT)
def heartbeat(payload: ExtensionHeartbeat, db: Session = Depends(get_db)) -> None:
    extension_service.record_heartbeat(db, payload)


@router.get("/status", response_model=ExtensionStatusRead)
def extension_status(db: Session = Depends(get_db)) -> ExtensionStatusRead:
    session = extension_service.latest_session(db)
    commands = list(
        db.scalars(
            select(ExtensionCommand).order_by(ExtensionCommand.created_at.desc()).limit(8)
        )
    )
    return ExtensionStatusRead(
        connected=extension_service.is_connected(session),
        extension_id=session.extension_id if session else None,
        status=session.status if session else "offline",
        page_url=session.page_url if session else None,
        page_title=session.page_title if session else None,
        page_type=session.page_type if session else None,
        last_seen_at=session.last_seen_at if session else None,
        recent_commands=commands,
    )


@router.post(
    "/commands",
    response_model=ExtensionCommandRead,
    status_code=status.HTTP_201_CREATED,
)
def queue_command(
    payload: ExtensionCommandCreate, db: Session = Depends(get_db)
) -> ExtensionCommand:
    session = extension_service.latest_session(db)
    if not extension_service.is_connected(session):
        raise HTTPException(status_code=409, detail="Chrome 扩展未连接，请先加载扩展并打开 BOSS 页面")
    return extension_service.create_command(
        db, command_type=payload.command_type, payload=payload.payload
    )


@router.get("/commands/next", response_model=ExtensionCommandRead | None)
def next_command(
    extension_id: str = Query(min_length=8, max_length=100),
    db: Session = Depends(get_db),
) -> ExtensionCommand | None:
    return extension_service.claim_next_command(db, extension_id)


@router.get("/commands/{command_id}/control", response_model=ExtensionCommandControlRead)
def command_control(command_id: int, db: Session = Depends(get_db)) -> ExtensionCommandControlRead:
    return ExtensionCommandControlRead(
        command_id=command_id,
        control=extension_service.command_control(db, command_id),
    )


@router.post("/commands/{command_id}/control", response_model=ExtensionCommandRead)
def update_command_control(
    command_id: int,
    payload: ExtensionCommandControl,
    db: Session = Depends(get_db),
) -> ExtensionCommand:
    try:
        return extension_service.update_command_control(db, command_id, payload.control)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/commands/stop-all")
def stop_all_commands(db: Session = Depends(get_db)) -> dict[str, int]:
    return extension_service.stop_pending_commands(db)


def _get_running_command(db: Session, command_id: int) -> ExtensionCommand:
    command = db.get(ExtensionCommand, command_id)
    if command is None:
        raise HTTPException(status_code=404, detail="扩展任务不存在")
    if command.status != "running":
        raise HTTPException(status_code=409, detail=f"扩展任务当前状态为 {command.status}")
    return command


@router.post("/commands/{command_id}/complete", response_model=ExtensionCompleteRead)
def complete_command(
    command_id: int,
    payload: ExtensionCommandResult,
    db: Session = Depends(get_db),
) -> ExtensionCompleteRead:
    command = _get_running_command(db, command_id)
    if command.extension_id != payload.extension_id:
        raise HTTPException(status_code=409, detail="扩展任务归属不匹配")
    try:
        candidate_id, attachment_urls, attachment_uploads = extension_service.complete_command(
            db, command, payload.result
        )
    except Exception as exc:
        db.rollback()
        extension_service.fail_command(
            db,
            command,
            extension_id=payload.extension_id,
            error_message=f"{type(exc).__name__}: {exc}",
        )
        raise HTTPException(status_code=422, detail=f"采集结果处理失败：{exc}") from exc
    return ExtensionCompleteRead(
        command=command,
        candidate_id=candidate_id,
        attachment_urls=attachment_urls,
        attachment_uploads=attachment_uploads,
    )


@router.post("/commands/{command_id}/fail", response_model=ExtensionCommandRead)
def fail_command(
    command_id: int,
    payload: ExtensionCommandFailure,
    db: Session = Depends(get_db),
) -> ExtensionCommand:
    command = _get_running_command(db, command_id)
    return extension_service.fail_command(
        db,
        command,
        extension_id=payload.extension_id,
        error_message=payload.error_message,
    )
