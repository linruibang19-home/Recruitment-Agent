"""阶段5b: 把候选人画像同步成 Obsidian Markdown 笔记。

如果 config.yaml 里配了 obsidian_vault,就在那里生成笔记;
否则写到本地 data/profiles/。笔记带双链与标签,方便你在 Obsidian 里浏览管理。
"""
from __future__ import annotations

from pathlib import Path

from config import cfg
from db import get_candidate


def sync_candidate(boss_id: str) -> Path | None:
    cand = get_candidate(boss_id)
    if not cand or not cand.get("profile_json"):
        return None

    profile = cand["profile_json"]
    vault = cfg.get("storage.obsidian_vault", "")
    base = Path(vault) if vault else cfg.path("profiles_dir")
    base.mkdir(parents=True, exist_ok=True)

    name = cand.get("name") or boss_id
    safe = "".join(c for c in name if c.isalnum() or c in "_-") or boss_id
    md_path = base / f"{safe}_{boss_id[-6:]}.md"

    tags = ["#候选人", f"#{cand.get('status', 'unknown')}"]
    body = _render(name, cand, profile, tags)
    md_path.write_text(body, encoding="utf-8")
    return md_path


def _render(name: str, cand: dict, profile: dict, tags: list[str]) -> str:
    basic = profile.get("basic", {})
    matrix = profile.get("skill_matrix", {})

    def bullet(items):
        return [f"- {x}" for x in items] or ["- (无)"]

    skill_lines = bullet([f"{k}: {'★' * int(v)}" for k, v in matrix.items()])

    lines = [
        f"# {name}",
        "",
        f"- 岗位: {cand.get('title', '')} @ {cand.get('company', '')}",
        f"- 评分: **{cand.get('score', 0)}** / 100",
        f"- 状态: `{cand.get('status', '')}`",
        f"- 城市: {basic.get('city', '')}  经验: {basic.get('years_exp', '')}年",
        f"- 资历: {profile.get('seniority', '')}  行业契合: {profile.get('industry_fit', '')}",
        "",
        "## 技能矩阵",
        *skill_lines,
        "",
        "## 亮点",
        *bullet(profile.get("highlights", [])),
        "",
        "## 风险点",
        *bullet(profile.get("risks", [])),
        "",
        "## 面试重点",
        *bullet(profile.get("interview_focus", [])),
        "",
        "---",
        " ".join(tags),
    ]
    return "\n".join(lines)
