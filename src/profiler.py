"""阶段4b: LLM 简历画像生成。

练习点: 结构化输出约束。用 json_mode 强制 LLM 输出可解析的 JSON 画像,
而不是自由文本。这是 Agent 工程的高频痛点。
"""
from __future__ import annotations

from db import set_profile
from llm_client import llm

PROFILE_SYSTEM = """你是资深招聘分析师。给定一份简历文本,输出严格 JSON 画像。
字段:
{
  "basic": {"name":"", "phone":"", "email":"", "city":"", "years_exp":0},
  "skill_matrix": {"技能名": 1-5熟练度},
  "seniority": "初级|中级|资深|专家",
  "industry_fit": 0.0-1.0,        // 与目标行业契合度
  "highlights": ["亮点1", "..."],
  "risks": ["风险点1", "..."],
  "interview_focus": ["建议面试重点1", "..."]
}
只输出 JSON,不要解释。无法判断的字段留空或填默认值。"""


def generate_profile(boss_id: str, resume_text: str) -> dict:
    """生成画像并存库。返回画像 dict。"""
    profile = llm.chat_json(
        system=PROFILE_SYSTEM,
        user=f"目标岗位: {_target_role()}\n\n简历文本:\n{resume_text[:6000]}",
    )
    # 评分在 scorer 单独算,这里先占位 0,scorer 会更新
    set_profile(boss_id, profile, score=0.0)
    return profile


def _target_role() -> str:
    from config import cfg
    s = cfg.get("screening", {})
    return f"{s.get('job_title')} | {s.get('experience')} | {s.get('city')}"
