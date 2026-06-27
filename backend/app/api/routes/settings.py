from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.settings import AutomationSettingsRead, AutomationSettingsUpdate
from app.services.quota import get_or_create_greeting_quota
from app.services.runtime_settings import load_automation_settings, save_automation_settings

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/automation", response_model=AutomationSettingsRead)
def get_automation_settings() -> AutomationSettingsRead:
    return load_automation_settings()


@router.put("/automation", response_model=AutomationSettingsRead)
def update_automation_settings(
    payload: AutomationSettingsUpdate,
    db: Session = Depends(get_db),
) -> AutomationSettingsRead:
    updated = save_automation_settings(payload)
    quota = get_or_create_greeting_quota(db, date.today())
    quota.max_count = updated.max_daily_greetings
    db.add(quota)
    db.commit()
    return updated
