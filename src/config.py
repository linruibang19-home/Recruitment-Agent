"""配置加载:合并 config.yaml + .env,提供全局单例。

练习点:Agent 工程里"配置"要和"密钥"分离 —— 结构化配置走 yaml,
密钥走环境变量,绝不写进版本库。
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

# 项目根目录 = 本文件上两级 (src/ 的父目录)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.yaml"


class Config:
    """只读配置对象。模块通过 `from config import cfg` 拿到全局实例。"""

    def __init__(self, raw: dict[str, Any]):
        self._raw = raw

    # 通用取值,支持点号路径: cfg.get("scoring.weights.skill_match")
    def get(self, dotted: str, default: Any = None) -> Any:
        node: Any = self._raw
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    @property
    def deepseek_api_key(self) -> str:
        # 从环境变量取,缺了就在这里炸,而不是等到调用时才报错。
        key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
        if not key:
            raise RuntimeError(
                "DEEPSEEK_API_KEY 未设置。请复制 .env.example 为 .env 并填入 key。"
            )
        return key

    @property
    def project_root(self) -> Path:
        return PROJECT_ROOT

    def path(self, dotted: str) -> Path:
        """把 storage 里的相对路径转成绝对 Path,并确保目录存在。"""
        rel = self.get(f"storage.{dotted}")
        if not rel:
            raise KeyError(f"storage.{dotted} 未配置")
        p = (PROJECT_ROOT / rel).resolve()
        if dotted.endswith("_dir"):
            p.mkdir(parents=True, exist_ok=True)
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
        return p


def load_config() -> Config:
    load_dotenv(PROJECT_ROOT / ".env")
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"找不到配置文件: {CONFIG_PATH}")
    with CONFIG_PATH.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return Config(raw)


# 全局单例: import 即用
cfg = load_config()
