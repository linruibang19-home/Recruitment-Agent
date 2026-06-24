from __future__ import annotations

import re
from datetime import date
from typing import Any

from app.services.llm_client import enrich_profile_with_llm


SKILLS = (
    "Python", "Java", "C++", "C#", "Go", "Rust", "JavaScript", "TypeScript",
    "React", "Vue", "Spring", "Spring Boot", "FastAPI", "Django", "Flask",
    "MySQL", "PostgreSQL", "Redis", "MongoDB", "Docker", "Kubernetes", "Git",
    "Linux", "PyTorch", "TensorFlow", "LangChain", "LangGraph", "RAG", "LLM",
    "NLP", "OCR", "OpenCV", "数据分析", "机器学习", "深度学习",
)
EDUCATION_LEVELS = ("博士", "硕士", "本科", "大专", "高中")
SCHOOL_RE = re.compile(r"([\u4e00-\u9fa5A-Za-z·]{2,30}(?:大学|学院))")
MAJOR_PATTERNS = (
    re.compile(r"(?:专业|主修)[:：]+[\s]*([\u4e00-\u9fa5A-Za-z0-9+\-]{2,30})"),
    re.compile(r"([\u4e00-\u9fa5A-Za-z0-9+\-]{2,30})专业"),
    re.compile(r"([\u4e00-\u9fa5]{2,20}(?:工程|科学|技术|管理|设计|数学|物理|语言))\s*(?:专业)?"),
)
YEAR_RE = re.compile(r"(19\d{2}|20\d{2})")
PROJECT_LINE_RE = re.compile(r"(项目|课设|系统|平台|应用|网站|模型|算法)", re.IGNORECASE)


def _first_match(patterns: tuple[re.Pattern[str], ...], text: str) -> str | None:
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return match.group(1).strip(" ：:")
    return None


def _extract_projects(lines: list[str]) -> list[str]:
    projects: list[str] = []
    for index, line in enumerate(lines):
        if PROJECT_LINE_RE.search(line) and 5 <= len(line) <= 100:
            detail = " ".join(lines[index:index + 2])
            if detail not in projects:
                projects.append(detail[:220])
        if len(projects) >= 6:
            break
    return projects


def generate_candidate_profile(text: str) -> tuple[dict[str, Any], str]:
    clean_text = re.sub(r"[ \t]+", " ", text)
    clean_text = re.sub(r"(?<=\d)\s+(?=\d)", "", clean_text)
    lines = [line.strip() for line in clean_text.splitlines() if line.strip()]
    lower_text = clean_text.lower()
    skills = [skill for skill in SKILLS if skill.lower() in lower_text]
    education_level = next((level for level in EDUCATION_LEVELS if level in clean_text), None)
    school_match = SCHOOL_RE.search(clean_text)
    school = school_match.group(1) if school_match else None
    major = _first_match(MAJOR_PATTERNS, clean_text)
    years = [int(year) for year in YEAR_RE.findall(clean_text)]
    graduation_candidates = [year for year in years if 1980 <= year <= date.today().year + 8]
    graduation_year = max(graduation_candidates) if graduation_candidates else None
    projects = _extract_projects(lines)

    work_year_match = re.search(r"(\d+(?:\.\d+)?)\s*年(?:工作|开发|从业)经验", clean_text)
    work_experience = float(work_year_match.group(1)) if work_year_match else 0
    campus_signals = ("应届", "在校", "实习", "校招")
    candidate_type = "校招" if any(signal in clean_text for signal in campus_signals) else "社招"
    if graduation_year and graduation_year >= date.today().year - 1 and work_experience <= 1:
        candidate_type = "校招"

    highlights: list[str] = []
    if len(skills) >= 5:
        highlights.append(f"技能覆盖较完整，识别到 {len(skills)} 项技术能力")
    if projects:
        highlights.append(f"简历包含 {len(projects)} 段项目或实践描述")
    if education_level in ("硕士", "博士"):
        highlights.append(f"学历背景为{education_level}")

    risks: list[str] = []
    if not school:
        risks.append("未明确识别学校")
    if not major:
        risks.append("未明确识别专业")
    if not skills:
        risks.append("未识别到明确技能关键词")
    if not projects:
        risks.append("项目经历信息不足")

    summary_parts = [part for part in (education_level, school, major, candidate_type) if part]
    if skills:
        summary_parts.append(f"技能：{'、'.join(skills[:8])}")
    fallback: dict[str, Any] = {
        "education_level": education_level,
        "school": school,
        "major": major,
        "graduation_year": graduation_year,
        "candidate_type": candidate_type,
        "skills": skills,
        "projects": projects,
        "work_experience": work_experience,
        "highlights": highlights,
        "risks": risks,
        "profile_summary": "；".join(summary_parts) or "简历信息不足，建议人工复核",
    }
    return enrich_profile_with_llm(clean_text, fallback)
