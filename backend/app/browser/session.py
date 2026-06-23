from dataclasses import dataclass

from app.core.config import settings


@dataclass(frozen=True)
class BrowserSessionConfig:
    base_url: str
    user_data_dir: str
    executable_path: str
    browser_channel: str
    headless: bool = False


def get_browser_session_config() -> BrowserSessionConfig:
    return BrowserSessionConfig(
        base_url=settings.boss_base_url,
        user_data_dir=settings.chrome_user_data_dir,
        executable_path=settings.chrome_executable_path,
        browser_channel=settings.playwright_browser_channel,
    )
