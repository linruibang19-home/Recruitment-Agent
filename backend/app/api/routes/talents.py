from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.browser.session import BrowserSessionError, browser_session_manager
from app.db.repositories import audit_logs as audit_repo
from app.db.repositories import talents as talent_repo
from app.db.session import get_db
from app.schemas.talents import GreetingQuotaRead, TalentFilter, TalentScanResult
from app.schemas.workflows import WorkflowStartRequest
from app.services.quota import greeting_quota_status
from app.services.talent_service import filter_talent_cards, greeting_message
from app.services.workflow_service import start_workflow_safely

router = APIRouter(tags=["talents"])


@router.get("/quota/greetings", response_model=GreetingQuotaRead)
def get_greeting_quota(db: Session = Depends(get_db)) -> GreetingQuotaRead:
    result = greeting_quota_status(db)
    db.commit()
    return result


@router.post("/automation/recommend/scan", response_model=TalentScanResult)
async def scan_recommended_talents(
    payload: TalentFilter,
    db: Session = Depends(get_db),
) -> TalentScanResult:
    job = talent_repo.get_job(db, payload.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.is_active:
        raise HTTPException(status_code=409, detail="岗位已停用")

    try:
        cards, page_url, screenshot_path = await browser_session_manager.scan_talents(
            payload.limit,
            payload.capture_screenshot,
        )
    except BrowserSessionError as exc:
        audit_repo.create_audit_log(
            db,
            action_type="talent_scan",
            status="failed",
            detail=str(exc),
            screenshot_path=getattr(exc, "screenshot_path", None),
            payload={"job_id": payload.job_id},
        )
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    if not payload.required_keywords:
        payload.required_keywords = list(job.keywords)
    matched_cards = filter_talent_cards(cards, payload)
    quota = greeting_quota_status(db)
    available = quota.available_count
    duplicate_count = 0
    drafted_count = 0
    drafted_actions = []

    for card, matched_keywords in matched_cards:
        candidate, _ = talent_repo.upsert_talent_candidate(db, card)
        existing = talent_repo.get_existing_greeting(
            db,
            candidate_id=candidate.id,
            job_id=job.id,
        )
        if existing:
            duplicate_count += 1
            continue
        if drafted_count >= available:
            continue
        action = talent_repo.create_greeting_draft(
            db,
            candidate=candidate,
            job=job,
            draft_message=greeting_message(card, job),
            matched_keywords=matched_keywords,
        )
        drafted_actions.append(action)
        drafted_count += 1

    db.commit()
    for action in drafted_actions:
        start_workflow_safely(
            db,
            WorkflowStartRequest(
                workflow_name="recommend_talent",
                candidate_id=action.candidate_id,
                job_id=action.job_id,
                action_id=action.id,
                payload={
                    "source": "boss_recommend",
                    "auto_send": False,
                    "idempotency_key": f"greeting-action:{action.id}",
                },
            ),
        )
    audit_repo.create_audit_log(
        db,
        action_type="talent_scan",
        status="ok",
        detail=f"读取 {len(cards)} 张牛人卡片，生成 {drafted_count} 条草稿",
        screenshot_path=screenshot_path,
        payload={
            "job_id": job.id,
            "total_read": len(cards),
            "matched_count": len(matched_cards),
            "duplicate_count": duplicate_count,
            "drafted_count": drafted_count,
            "quota_available_before": available,
            "page_url": page_url,
        },
    )
    return TalentScanResult(
        scanned_at=datetime.now(timezone.utc),
        page_url=page_url,
        total_read=len(cards),
        matched_count=len(matched_cards),
        duplicate_count=duplicate_count,
        drafted_count=drafted_count,
        cards=[card for card, _ in matched_cards],
        screenshot_path=screenshot_path,
    )
