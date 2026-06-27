from pathlib import Path

import pytest
from pydantic import ValidationError

from app.schemas.settings import AutomationSettingsUpdate
from app.services.runtime_settings import load_automation_settings, save_automation_settings


def test_runtime_settings_save_and_load(tmp_path: Path) -> None:
    path = tmp_path / "automation_settings.json"

    saved = save_automation_settings(
        AutomationSettingsUpdate(
            resume_request_message="方便发一份你的简历过来吗？",
            chat_loop_batch_limit=12,
            max_daily_greetings=40,
            recommendation_top_n=6,
        ),
        path=path,
    )

    loaded = load_automation_settings(path)
    assert saved.chat_loop_batch_limit == 12
    assert loaded.max_daily_greetings == 40
    assert loaded.recommendation_top_n == 6


def test_runtime_settings_reject_invalid_ranges(tmp_path: Path) -> None:
    path = tmp_path / "automation_settings.json"

    with pytest.raises(ValidationError):
        save_automation_settings(
            {
                "chat_loop_min_gap_minutes": 30,
                "chat_loop_max_gap_minutes": 10,
            },
            path=path,
        )
