"""供 LLM function calling 调用的工具:schema 定义 + 实现绑定。

练习点:Tool Use。LLM 不直接操作浏览器/数据库,而是通过这些声明好的工具
来感知和行动。改这里就能扩展 Agent 的能力边界。
"""
from __future__ import annotations

# OpenAI function-calling 风格的 schema
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "read_candidate_card",
            "description": "读取当前 Boss 候选人卡片的详细信息(姓名/职位/公司/技能/经验)。",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "estimate_skill_match",
            "description": "根据候选人技能与岗位 JD,估算技能匹配度(0-1)。",
            "parameters": {
                "type": "object",
                "properties": {
                    "candidate_skills": {"type": "string"},
                    "job_requirements": {"type": "string"},
                },
                "required": ["candidate_skills", "job_requirements"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_greeting",
            "description": "给当前候选人发送一条打招呼消息。会自动计入每日配额。",
            "parameters": {
                "type": "object",
                "properties": {"message": {"type": "string", "description": "个性化招呼语"}},
                "required": ["message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_faq",
            "description": "在本地 FAQ 库里检索候选人问题的答案。返回答案或 None。",
            "parameters": {
                "type": "object",
                "properties": {"question": {"type": "string"}},
                "required": ["question"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mark_human_required",
            "description": "标记当前对话需要人工介入(无法自动处理或风险高)。",
            "parameters": {
                "type": "object",
                "properties": {"reason": {"type": "string"}},
                "required": ["reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "request_resume",
            "description": "向候选人索取 PDF 简历。",
            "parameters": {
                "type": "object",
                "properties": {"pitch": {"type": "string", "description": "索取简历的说辞"}},
                "required": ["pitch"],
            },
        },
    },
]


def build_tool_impl(session, candidate_boss_id: str) -> dict:
    """把工具 schema 绑定到具体的 Python 实现。

    session: browser_session 实例(负责真实浏览器动作)
    candidate_boss_id: 当前上下文处理的候选人

    返回 {工具名: 可调用函数},供 llm.react_step 的 tool_impl 使用。
    """

    def read_candidate_card():
        return session.read_current_card()

    def estimate_skill_match(candidate_skills: str, job_requirements: str):
        # 简易估算:关键词重合度。生产可换 embedding。
        cand = set(candidate_skills.lower().replace(",", " ").split())
        req = set(job_requirements.lower().replace(",", " ").split())
        if not req:
            return {"match": 0.0}
        return {"match": round(len(cand & req) / len(req), 3)}

    def send_greeting(message: str):
        # 配额检查交给 greeter 层;这里只做真实发送
        ok = session.send_message(message)
        return {"sent": ok, "message": message}

    def lookup_faq(question: str):
        from db import faq_answer
        ans = faq_answer(question)
        return {"answer": ans}  # None 表示未命中

    def mark_human_required(reason: str):
        from db import log_interaction
        log_interaction(candidate_boss_id, "out", "system", f"[需人工] {reason}")
        return {"marked": True}

    def request_resume(pitch: str):
        ok = session.send_message(pitch)
        from db import log_interaction
        log_interaction(candidate_boss_id, "out", "resume_share", pitch)
        return {"sent": ok}

    return {
        "read_candidate_card": read_candidate_card,
        "estimate_skill_match": estimate_skill_match,
        "send_greeting": send_greeting,
        "lookup_faq": lookup_faq,
        "mark_human_required": mark_human_required,
        "request_resume": request_resume,
    }
