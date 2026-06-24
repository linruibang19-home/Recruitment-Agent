from __future__ import annotations

import re
from pathlib import Path
from typing import Any


PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
ID_CARD_RE = re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)")
WECHAT_RE = re.compile(
    r"((?:微信|wx|wechat)\s*[:：]?\s*)[A-Za-z][-_A-Za-z0-9]{5,19}",
    re.IGNORECASE,
)
WINDOWS_PATH_RE = re.compile(r"[A-Za-z]:\\(?:[^\\\s]+\\)*[^\\\s]*")


def redact_text(value: str | None) -> str | None:
    if value is None:
        return None
    redacted = PHONE_RE.sub("[手机号]", value)
    redacted = EMAIL_RE.sub("[邮箱]", redacted)
    redacted = ID_CARD_RE.sub("[身份证号]", redacted)
    redacted = WECHAT_RE.sub(r"\1[微信号]", redacted)
    return WINDOWS_PATH_RE.sub("[本地路径]", redacted)


def redact_data(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, dict):
        return {str(key): redact_data(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_data(item) for item in value]
    if isinstance(value, tuple):
        return [redact_data(item) for item in value]
    return value


def is_within_directory(path: Path, directory: Path) -> bool:
    try:
        path.resolve().relative_to(directory.resolve())
        return True
    except ValueError:
        return False
