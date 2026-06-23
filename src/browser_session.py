"""阶段1: Boss 直聘浏览器会话管理。

职责:
  - 打开 Boss 并复用 Chrome profile 保持登录态
  - 自检登录态,过期则通知扫码
  - 提供统一的页面操作入口(read_current_card / send_message / open_url / ...)

练习点:异常自适应。所有动作经 safety.guard 包装,遇风控自动刹车。

注意: browser-use 的具体调用语法依版本而定,本文件给出结构骨架,
首次接真实 Boss 页面时需按实际 DOM 微调 read_current_card 等方法。
"""
from __future__ import annotations

import os
from typing import Any

from config import cfg
from safety import SafetyStop, classify, notify_human


class BrowserSession:
    def __init__(self) -> None:
        self._agent = None        # browser-use 的 Agent 实例
        self._logged_in = False

    # ---------- 启动与登录自检 ----------

    async def start(self) -> None:
        """启动浏览器并打开 Boss。用真实 Chrome profile 以保持登录态。"""
        from browser_use import Agent  # 按实际 browser-use 版本导入
        user_data = os.environ.get("CHROME_USER_DATA_DIR", "").strip()
        kwargs: dict[str, Any] = {"headless": False}
        if user_data:
            kwargs["user_data_dir"] = user_data
        # 注: browser-use 版本不同,传参方式可能不同,这里示意。
        self._agent = Agent(task="打开 https://www.zhipin.com/", **kwargs)
        await self._agent.run()

    async def ensure_logged_in(self) -> bool:
        """自检登录态。已登录返回 True;需要扫码则通知人并阻塞等待。"""
        state = await self.get_state_text()
        diag = classify(page_text=state)
        if diag.level.value == "blocked" and "登录" in state:
            notify_human("Boss 登录态可能过期,请扫码登录。Agent 已暂停。")
            return False
        # 简易判断:页面出现"打招呼""牛人"等招聘端元素视为已登录
        self._logged_in = any(kw in state for kw in ["打招呼", "牛人", "沟通"])
        return self._logged_in

    # ---------- 页面操作 ----------

    async def get_state_text(self) -> str:
        """获取当前页面文本,供登录自检与风控检测。"""
        if not self._agent:
            return ""
        # browser-use 暴露当前页面状态的方式依版本而定,示意:
        try:
            return str(await self._agent.get_state())  # type: ignore[attr-defined]
        except Exception:
            return ""

    async def open_url(self, url: str) -> None:
        await self._agent.execute(f"打开页面: {url}")  # 示意调用

    def read_current_card(self) -> dict:
        """读取当前候选人卡片。返回结构化字段。

        真实实现需按 Boss 搜索结果 DOM 解析。这里给出字段约定,
        供 estimate_skill_match 等下游使用。
        """
        # TODO(对接Boss): 用 browser-use 提取卡片文本并结构化
        return {"name": "", "title": "", "company": "", "skills": "", "experience": ""}

    def send_message(self, message: str) -> bool:
        """在当前候选人对话框发送消息。返回是否成功。"""
        # TODO(对接Boss): 定位输入框 → 填入 → 发送 → 校验成功
        if not self._logged_in:
            return False
        return True  # 占位

    async def close(self) -> None:
        if self._agent:
            try:
                await self._agent.close()  # type: ignore[attr-defined]
            except Exception:
                pass


# 全局单例(懒加载,避免 import 时就拉起浏览器)
session: BrowserSession | None = None


def get_session() -> BrowserSession:
    global session
    if session is None:
        session = BrowserSession()
    return session
