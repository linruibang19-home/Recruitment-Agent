from pydantic import BaseModel, Field, model_validator


class AutomationSettingsRead(BaseModel):
    resume_request_message: str = Field(min_length=2, max_length=200)
    chat_loop_batch_limit: int = Field(ge=1, le=20)
    chat_loop_min_gap_minutes: int = Field(ge=1, le=120)
    chat_loop_max_gap_minutes: int = Field(ge=1, le=180)
    chat_loop_min_delay_ms: int = Field(ge=500, le=10000)
    chat_loop_max_delay_ms: int = Field(ge=500, le=20000)
    max_daily_greetings: int = Field(ge=1, le=150)
    recommendation_hour: int = Field(ge=0, le=23)
    recommendation_top_n: int = Field(ge=1, le=20)
    interview_invite_score_threshold: int = Field(ge=0, le=100)

    @model_validator(mode="after")
    def validate_ranges(self) -> "AutomationSettingsRead":
        if self.chat_loop_min_gap_minutes > self.chat_loop_max_gap_minutes:
            raise ValueError("最小批次间隔不能大于最大批次间隔")
        if self.chat_loop_min_delay_ms > self.chat_loop_max_delay_ms:
            raise ValueError("最小单人间隔不能大于最大单人间隔")
        return self


class AutomationSettingsUpdate(BaseModel):
    resume_request_message: str | None = Field(default=None, min_length=2, max_length=200)
    chat_loop_batch_limit: int | None = Field(default=None, ge=1, le=20)
    chat_loop_min_gap_minutes: int | None = Field(default=None, ge=1, le=120)
    chat_loop_max_gap_minutes: int | None = Field(default=None, ge=1, le=180)
    chat_loop_min_delay_ms: int | None = Field(default=None, ge=500, le=10000)
    chat_loop_max_delay_ms: int | None = Field(default=None, ge=500, le=20000)
    max_daily_greetings: int | None = Field(default=None, ge=1, le=150)
    recommendation_hour: int | None = Field(default=None, ge=0, le=23)
    recommendation_top_n: int | None = Field(default=None, ge=1, le=20)
    interview_invite_score_threshold: int | None = Field(default=None, ge=0, le=100)
