from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.browser.session import BrowserSessionError, browser_session_manager
from app.db.repositories import audit_logs as audit_repo
from app.db.session import get_db
from app.schemas.automation import (
    AuditLogRead,
    BrowserStatus,
    ChatOpenRequest,
    ChatScanRequest,
    ChatScanResult,
)
from app.schemas.common import PageResponse

router = APIRouter(tags=["automation"])


def _record_failure(db: Session, action_type: str, exc: Exception) -> None:
    audit_repo.create_audit_log(
        db,
        action_type=action_type,
        status="failed",
        detail=str(exc),
        screenshot_path=getattr(exc, "screenshot_path", None),
        payload={"error_type": type(exc).__name__},
    )


@router.get("/automation/browser/status", response_model=BrowserStatus)
async def browser_status() -> BrowserStatus:
    return await browser_session_manager.status()


@router.post("/automation/browser/start", response_model=BrowserStatus)
async def start_browser(db: Session = Depends(get_db)) -> BrowserStatus:
    try:
        result = await browser_session_manager.start()
    except BrowserSessionError as exc:
        _record_failure(db, "browser_start", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    audit_repo.create_audit_log(
        db,
        action_type="browser_start",
        status="ok",
        detail=result.detail,
        payload={"state": result.state, "url": result.current_url},
    )
    return result


@router.post("/automation/browser/stop", response_model=BrowserStatus)
async def stop_browser(db: Session = Depends(get_db)) -> BrowserStatus:
    result = await browser_session_manager.stop()
    audit_repo.create_audit_log(
        db,
        action_type="browser_stop",
        status="ok",
        detail=result.detail,
    )
    return result


@router.post("/automation/chat/scan", response_model=ChatScanResult)
async def scan_chats(payload: ChatScanRequest, db: Session = Depends(get_db)) -> ChatScanResult:
    try:
        result = await browser_session_manager.scan_chats(payload.limit, payload.capture_screenshot)
        audit_repo.create_audit_log(
            db,
            action_type="chat_scan",
            status="ok",
            detail=f"读取 {len(result.conversations)} 个沟通会话",
            screenshot_path=result.screenshot_path,
            payload={
                "count": len(result.conversations),
                "limit": payload.limit,
                "url": result.page_url,
            },
        )
        return result
    except Exception as exc:
        _record_failure(db, "chat_scan", exc)
        status_code = 409 if isinstance(exc, BrowserSessionError) else 500
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.post("/automation/chat/open", response_model=ChatScanResult)
async def open_chat(payload: ChatOpenRequest, db: Session = Depends(get_db)) -> ChatScanResult:
    try:
        result = await browser_session_manager.open_chat(
            payload.candidate_name,
            payload.capture_screenshot,
        )
        detail = result.detail
        if detail is None:
            raise RuntimeError("聊天详情读取结果为空")
        audit_repo.create_audit_log(
            db,
            action_type="chat_open",
            status="ok",
            detail=f"读取候选人聊天：{payload.candidate_name}",
            screenshot_path=result.screenshot_path,
            payload={
                "candidate_name": payload.candidate_name,
                "message_count": len(detail.messages),
                "attachment_count": len(detail.attachments),
                "url": result.page_url,
            },
        )
        return result
    except Exception as exc:
        _record_failure(db, "chat_open", exc)
        status_code = 409 if isinstance(exc, BrowserSessionError) else 404 if isinstance(exc, ValueError) else 500
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.get("/audit-logs", response_model=PageResponse[AuditLogRead])
def list_audit_logs(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> PageResponse[AuditLogRead]:
    items, total = audit_repo.list_audit_logs(db, limit=limit, offset=offset)
    return PageResponse(items=items, total=total, limit=limit, offset=offset)
