from __future__ import annotations

import json
import re
from typing import Any
from urllib import request

from app.core.config import settings


def _redact_personal_data(text: str) -> str:
    text = re.sub(r"1[3-9]\d{9}", "[手机号]", text)
    return re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[邮箱]", text)


def enrich_profile_with_llm(text: str, fallback: dict[str, Any]) -> tuple[dict[str, Any], str]:
    if not settings.llm_enabled or not settings.deepseek_api_key:
        return fallback, "rule_based"

    prompt = (
        "从以下中文简历中提取结构化信息。只返回 JSON，不要解释。"
        "字段：education_level, school, major, graduation_year, candidate_type, "
        "skills, projects, work_experience, highlights, risks, profile_summary。"
        "缺失值使用 null 或空数组，不推测敏感属性。\n\n"
        f"{_redact_personal_data(text[:18000])}"
    )
    payload = json.dumps(
        {
            "model": settings.llm_model,
            "messages": [
                {"role": "system", "content": "你是招聘简历结构化解析器。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
    ).encode("utf-8")
    http_request = request.Request(
        f"{settings.llm_base_url.rstrip('/')}/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {settings.deepseek_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(http_request, timeout=45) as response:
            body = json.loads(response.read().decode("utf-8"))
        content = body["choices"][0]["message"]["content"]
        parsed = json.loads(content)
    except Exception:
        return fallback, "rule_based_fallback"

    merged = dict(fallback)
    for key, value in parsed.items():
        if value not in (None, "", []):
            merged[key] = value
    return merged, settings.llm_provider
