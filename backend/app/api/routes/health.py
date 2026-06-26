from datetime import datetime, timezone

from fastapi import APIRouter

from app.core.config import settings
from app.db.session import check_database_connection
from app.browser.session import browser_session_manager
from app.services.ocr import DEFAULT_TESSDATA_DIR, find_tesseract

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict:
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.app_env,
        "phase": "phase-9-hardening",
        "database_configured": bool(settings.database_url),
        "boss_base_url": settings.boss_base_url,
        "time": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health/database")
def database_health_check() -> dict:
    try:
        check_database_connection()
    except Exception as exc:
        return {
            "status": "error",
            "database_configured": bool(settings.database_url),
            "detail": f"{type(exc).__name__}: {exc}",
        }
    return {"status": "ok", "database_configured": True}


@router.get("/health/automation")
async def automation_health_check() -> dict:
    status = await browser_session_manager.status()
    return {
        "status": "error" if status.state in {"blocked", "error"} else "ok",
        "browser": status.model_dump(),
        "write_actions_enabled": False,
        "human_review_required": True,
    }


@router.get("/health/ai")
def ai_health_check() -> dict:
    tesseract_path = find_tesseract()
    tessdata_dir = settings.tessdata_dir or DEFAULT_TESSDATA_DIR
    return {
        "status": "ok" if tesseract_path else "warning",
        "ocr": {
            "provider": "tesseract",
            "available": bool(tesseract_path),
            "executable": tesseract_path,
            "tessdata_dir": tessdata_dir,
            "languages": "chi_sim+eng",
        },
        "llm": {
            "provider": settings.llm_provider,
            "enabled": settings.llm_enabled,
            "configured": bool(settings.deepseek_api_key),
            "model": settings.llm_model,
            "base_url": settings.llm_base_url,
        },
    }
