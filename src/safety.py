"""安全与反风控:异常分类 + 刹车机制。

练习点:Agent 区别于普通脚本的本质 —— 遇到异常不崩溃,而是
"感知 → 诊断 → 决定动作(重试/降级/停手通知人)"。
所有浏览器动作都应经过这里包装。
"""
from __future__ import annotations

import enum
from dataclasses import dataclass

from config import cfg


class RiskLevel(enum.Enum):
    SAFE = "safe"              # 正常
    TRANSIENT = "transient"    # 偶发(网络/加载),可重试
    RATE_LIMIT = "rate_limit"  # 限流,需要更长停顿
    BLOCKED = "blocked"        # 被风控(验证码/账号异常),必须停手通知人


@dataclass
class Diagnosis:
    level: RiskLevel
    detail: str
    should_stop: bool          # 是否立即停止整个流程
    should_notify: bool        # 是否推送人工介入


# 风控信号关键词(出现在页面文本/URL/报错里)
_BLOCK_SIGNALS = ["验证", "滑块", "安全验证", "异常", "请扫码", "登录失效", "captcha"]
_RATE_SIGNALS = ["频繁", "稍后再试", "操作太快"]


def classify(page_text: str = "", error: str = "") -> Diagnosis:
    """诊断当前页面或异常属于哪种风险等级。"""
    blob = f"{page_text} {error}".lower()

    for sig in _BLOCK_SIGNALS:
        if sig.lower() in blob:
            return Diagnosis(
                level=RiskLevel.BLOCKED,
                detail=f"命中风控信号: {sig}",
                should_stop=True,
                should_notify=True,
            )
    for sig in _RATE_SIGNALS:
        if sig.lower() in blob:
            return Diagnosis(
                level=RiskLevel.RATE_LIMIT,
                detail=f"命中限流信号: {sig}",
                should_stop=False,
                should_notify=False,
            )
    if error:
        return Diagnosis(
            level=RiskLevel.TRANSIENT,
            detail=f"偶发异常: {error[:120]}",
            should_stop=False,
            should_notify=False,
        )
    return Diagnosis(level=RiskLevel.SAFE, detail="ok", should_stop=False, should_notify=False)


class SafetyStop(Exception):
    """命中风控,流程必须中止。由 scheduler 捕获后决定是否通知人。"""


def guard(page_text_fn=None):
    """装饰器:把一个浏览器动作包起来,异常时分类,风控则抛 SafetyStop。

    page_text_fn: 可选,返回当前页面文本以供风控检测。
    """
    def deco(fn):
        def wrapper(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except SafetyStop:
                raise
            except Exception as e:
                page_text = ""
                if page_text_fn:
                    try:
                        page_text = page_text_fn()
                    except Exception:
                        pass
                diag = classify(page_text=page_text, error=str(e))
                if diag.should_stop:
                    raise SafetyStop(diag.detail) from e
                # 偶发/限流:返回诊断,让上层决定重试策略
                return {"__diagnosis__": diag}
        return wrapper
    return deco


def notify_human(reason: str) -> None:
    """推送人工介入通知。没配 webhook 就只写日志。"""
    import datetime
    from pathlib import Path
    log_dir = cfg.path("logs_dir")
    log_file = log_dir / "human_required.log"
    ts = datetime.datetime.now().isoformat(timespec="seconds")
    line = f"[{ts}] {reason}\n"
    with log_file.open("a", encoding="utf-8") as f:
        f.write(line)

    webhook = cfg.get("notify.webhook_url", "")
    if webhook and cfg.get("notify.on_human_required", True):
        try:
            import urllib.request, json
            data = json.dumps({"text": f"[招聘Agent] 需要人工: {reason}"}).encode("utf-8")
            req = urllib.request.Request(webhook, data=data,
                                         headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=5)
        except Exception as e:
            # 推送失败不影响主流程,记日志即可
            with log_file.open("a", encoding="utf-8") as f:
                f.write(f"  (推送失败: {e})\n")
