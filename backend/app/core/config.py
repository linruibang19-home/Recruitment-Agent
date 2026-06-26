from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Recruitment Agent"
    app_env: str = "local"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/recruitment_agent"
    )
    boss_base_url: str = "https://www.zhipin.com"
    chrome_user_data_dir: str = ""
    chrome_executable_path: str = ""
    playwright_browser_channel: str = "chrome"
    browser_headless: bool = False
    browser_scan_limit: int = 20
    screenshot_dir: str = ""
    resume_dir: str = ""
    tessdata_dir: str = ""
    max_resume_size_mb: int = 10
    llm_enabled: bool = False
    llm_provider: str = "deepseek"
    llm_model: str = "deepseek-v4-flash"
    llm_base_url: str = "https://api.deepseek.com"
    deepseek_api_key: str = ""
    recommendation_top_n: int = 5
    interview_invite_score_threshold: int = 70
    recommendation_hour: int = 9
    max_daily_greetings: int = 50
    max_hourly_greetings: int = 10
    stop_after_automation_failures: int = 3
    cors_origins: list[str] = ["http://127.0.0.1:5173", "http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
