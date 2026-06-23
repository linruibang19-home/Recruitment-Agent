"""拟人化时序:让 Agent 的操作节奏像真人,而不是均匀的机器人。

练习点:反风控不是"加个随机 sleep",而是用真实人类行为的统计分布
(对数正态的停顿、偶尔的长思考、穿插的无意义动作)来抹平机器指纹。
"""
from __future__ import annotations

import math
import random
import time

from config import cfg


def _lognormal(mean: float, sigma: float) -> float:
    """从对数正态分布采样,给定算术均值与 sigma。"""
    # 求 mu 使 exp(mu + sigma^2/2) = mean
    mu = math.log(max(mean, 1e-3)) - (sigma ** 2) / 2
    return random.lognormvariate(mu, sigma)


def human_pause(action: str = "greet") -> float:
    """返回本次操作前应等待的秒数(不直接 sleep,便于测试与组合)。"""
    h = cfg.get("boss.humanize", {})
    if action == "greet":
        mean = h.get("greet_interval_mean_sec", 45)
        sigma = h.get("greet_interval_sigma", 0.6)
        wait = _lognormal(mean, sigma)
        if random.random() < h.get("long_pause_prob", 0.08):
            lo, hi = h.get("long_pause_range_sec", [120, 240])
            wait += random.uniform(lo, hi)
        return min(wait, 600.0)  # 上限保护,避免单次睡太久
    # 默认短停顿(翻页、点击之间)
    return random.uniform(1.5, 4.0)


def should_distract() -> bool:
    """是否插入一个无意义但像人的浏览动作。"""
    return random.random() < cfg.get("boss.humanize.distraction_prob", 0.25)


def random_distraction() -> str:
    """随机挑一个干扰动作(由 browser_session 解释执行)。"""
    actions = cfg.get("boss.humanize.browse_distractions",
                      ["scroll_list", "open_profile", "go_back", "hover_card"])
    return random.choice(actions)


def in_greet_window(now: time.struct_time | None = None) -> bool:
    """当前时间是否落在配置的打招呼时段内。"""
    import datetime
    now = now or time.localtime()
    hhmm = now.tm_hour * 100 + now.tm_min
    for window in cfg.get("boss.greet_windows", []):
        try:
            start_s, end_s = window.split("-")
            s = int(start_s.replace(":", ""))
            e = int(end_s.replace(":", ""))
            if s <= hhmm <= e:
                return True
        except ValueError:
            continue
    return False
