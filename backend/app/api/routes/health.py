from datetime import datetime, timezone

from fastapi import APIRouter

from app.core.config import settings
from app.db.session import check_database_connection

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict:
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.app_env,
        "phase": "phase-5-resume-scoring",
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
