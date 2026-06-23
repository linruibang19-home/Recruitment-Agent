from datetime import datetime, timezone

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict:
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.app_env,
        "phase": "phase-1-foundation",
        "database_configured": bool(settings.database_url),
        "boss_base_url": settings.boss_base_url,
        "time": datetime.now(timezone.utc).isoformat(),
    }

