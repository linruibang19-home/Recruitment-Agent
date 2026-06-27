from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.schemas.settings import AutomationSettingsRead, AutomationSettingsUpdate


CONFIG_PATH = Path(__file__).resolve().parents[3] / "data" / "runtime" / "automation_settings.json"


def default_automation_settings() -> AutomationSettingsRead:
    return AutomationSettingsRead(
        resume_request_message="方便发一份你的简历过来吗？",
        chat_loop_batch_limit=settings.chat_loop_batch_limit,
        chat_loop_min_gap_minutes=settings.chat_loop_min_gap_minutes,
        chat_loop_max_gap_minutes=settings.chat_loop_max_gap_minutes,
        chat_loop_min_delay_ms=settings.chat_loop_min_delay_ms,
        chat_loop_max_delay_ms=settings.chat_loop_max_delay_ms,
        max_daily_greetings=settings.max_daily_greetings,
        recommendation_hour=settings.recommendation_hour,
        recommendation_top_n=settings.recommendation_top_n,
        interview_invite_score_threshold=settings.interview_invite_score_threshold,
    )


def load_automation_settings(path: Path | None = None) -> AutomationSettingsRead:
    config_path = path or CONFIG_PATH
    defaults = default_automation_settings()
    if not config_path.exists():
        return defaults
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return defaults
    if not isinstance(raw, dict):
        return defaults
    return AutomationSettingsRead.model_validate({**defaults.model_dump(), **raw})


def save_automation_settings(
    update: AutomationSettingsUpdate | dict[str, Any],
    path: Path | None = None,
) -> AutomationSettingsRead:
    config_path = path or CONFIG_PATH
    current = load_automation_settings(config_path)
    update_data = (
        update.model_dump(exclude_none=True) if isinstance(update, AutomationSettingsUpdate) else update
    )
    next_settings = AutomationSettingsRead.model_validate(
        {**current.model_dump(), **update_data}
    )
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(next_settings.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return next_settings
