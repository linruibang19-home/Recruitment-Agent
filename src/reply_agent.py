"""阶段3b: 回复 Agent —— 本项目最练手的模块。

用 ReAct(Reason + Act)处理候选人的开放性回复。流程:
  1. 理解对方意图(问公司信息? 拒绝? 要薪资? 发简历图片?)
  2. 决定调用哪个工具(查FAQ / 索取简历 / 标记需人工)
  3. 若调用了工具,把结果回灌进 history,再走下一步
  4. 直到不再调工具 → 输出最终回复

练习点:
  - ReAct 多步决策(LLM 自己决定调哪个工具、传什么参)
  - 开放性对话处理(无法穷举 if-else)
  - 失败换策略(查不到 FAQ → 标记人工)
"""
from __future__ import annotations

import json

from db import log_interaction
from llm_client import llm
from config import PROJECT_ROOT
import sys
# tools 包与 src 同级,运行时把项目根加入 path 以便统一 import
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from tools import boss_tools

REACT_SYSTEM = """你是一个招聘助理 Agent,正在 Boss 直聘上处理候选人发来的消息。

可用工具:
- lookup_faq(question): 在本地 FAQ 库查常见问题答案(公司规模/出差/福利等)。返回 {answer} 或 None。
- request_resume(pitch): 请求对方发送 PDF 简历。
- mark_human_required(reason): 当前问题无法自动处理(如薪资谈判、加微信等敏感/复杂场景),标记需要人工。

你的决策原则(Reason + Act):
1. 先判断对方意图。
2. 能查 FAQ 就查;查到了基于答案回复;查不到或属于敏感场景 → mark_human_required。
3. 对方表示愿意继续但还没发简历 → 礼貌 request_resume。
4. 最终给出一条要发给对方的回复文本(在 thought 里说明)。

每一步: 先简短说明你的判断(thought),再选择一个工具或直接给出回复。
最多走 3 步,避免无限循环。"""


def handle_reply(session, boss_id: str, incoming: str) -> dict:
    """处理一条新回复。返回 {needs_human, replied}。

    通过 react_step 循环,直到 LLM 不再调工具。
    """
    tool_impl = boss_tools.build_tool_impl(session, boss_id)
    history = [
        {"role": "user", "content": f"候选人({boss_id})发来消息: {incoming}"}
    ]

    final_reply = None
    needs_human = False

    for step in range(3):  # 最多 3 步 ReAct
        decision = llm.react_step(
            system=REACT_SYSTEM,
            history=history,
            tools=boss_tools.TOOL_SCHEMAS,
            tool_impl=tool_impl,
        )

        if decision["tool"] is None:
            # 模型给出最终回复
            final_reply = decision["thought"]
            break

        # 把这一步的工具调用与结果回灌进 history,供下一步推理
        if decision["tool"] == "mark_human_required":
            needs_human = True
            final_reply = decision["thought"] or "(已标记需人工回复)"
            break

        history.append({"role": "assistant", "content": json.dumps(decision, ensure_ascii=False)})
        history.append({
            "role": "user",
            "content": f"工具 {decision['tool']} 返回: {json.dumps(decision['result'], ensure_ascii=False)}。请基于此继续。",
        })

    if final_reply and not needs_human:
        session.send_message(final_reply)
        log_interaction(boss_id, "out", "reply", final_reply)
    if needs_human:
        log_interaction(boss_id, "out", "system", f"[需人工] {final_reply}")

    return {"needs_human": needs_human, "replied": bool(final_reply and not needs_human)}
