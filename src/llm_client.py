"""DeepSeek 客户端封装。

DeepSeek 兼容 OpenAI 接口,所以直接用 openai SDK 调。
这里封装两类调用:
  - chat(): 普通对话 / 结构化输出(用 response_format json_object)
  - react_step(): 单步 ReAct —— 让 LLM 在"思考"和"调用工具"之间做决策。

练习点:这是 Tool Use 与 ReAct 的底层引擎。其他模块靠它驱动决策。
"""
from __future__ import annotations

import json
from typing import Any, Callable

from openai import OpenAI

from config import cfg


class LLMClient:
    def __init__(self) -> None:
        self._client = OpenAI(
            api_key=cfg.deepseek_api_key,
            base_url="https://api.deepseek.com",  # DeepSeek 的 OpenAI 兼容端点
        )
        self._model = cfg.get("llm.model", "deepseek-chat")
        self._temperature = cfg.get("llm.temperature", 0.7)
        self._max_tokens = cfg.get("llm.max_tokens", 1500)

    def chat(
        self,
        messages: list[dict],
        json_mode: bool = False,
        temperature: float | None = None,
    ) -> str:
        """普通对话。json_mode=True 时强制返回合法 JSON(供画像/评分等结构化场景)。"""
        kwargs: dict[str, Any] = dict(
            model=self._model,
            messages=messages,
            temperature=self._temperature if temperature is None else temperature,
            max_tokens=self._max_tokens,
        )
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        resp = self._client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or ""

    def chat_json(self, system: str, user: str) -> dict:
        """便捷: 强制 JSON 输出并解析成 dict。失败抛异常,让上层决定重试/降级。"""
        raw = self.chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            json_mode=True,
        )
        return json.loads(raw)

    def react_step(
        self,
        system: str,
        history: list[dict],
        tools: list[dict],
        tool_impl: dict[str, Callable[..., Any]],
    ) -> dict:
        """单步 ReAct 决策。

        返回 {"thought": str, "tool": str|None, "args": dict, "result": Any}
        - 若 LLM 决定不调工具(tool=None),通常意味着它要直接给出文本回复。
        - 调用方据此循环:拿到结果回灌进 history,再走下一步,直到 tool=None。

        tools: OpenAI function-calling 格式的工具 schema 列表
        tool_impl: {工具名: 实际执行的 Python 函数}
        """
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "system", "content": system}, *history],
            tools=tools,
            tool_choice="auto",
            temperature=self._temperature,
            max_tokens=self._max_tokens,
        )
        msg = resp.choices[0].message

        if not msg.tool_calls:
            # 模型选择直接回复,不调工具
            return {"thought": msg.content or "", "tool": None, "args": {}, "result": None}

        call = msg.tool_calls[0]
        tool_name = call.function.name
        try:
            args = json.loads(call.function.arguments or "{}")
        except json.JSONDecodeError:
            args = {}

        if tool_name not in tool_impl:
            result = {"error": f"未知工具: {tool_name}"}
        else:
            try:
                result = tool_impl[tool_name](**args)
            except Exception as e:  # 工具执行失败要让 Agent 知道,而不是崩
                result = {"error": f"{type(e).__name__}: {e}"}

        return {"thought": msg.content or "", "tool": tool_name, "args": args, "result": result}


# 全局单例
llm = LLMClient()
