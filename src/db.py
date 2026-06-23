"""SQLite 数据访问层。

练习点:Agent 需要"长期记忆"。这里把候选人的完整生命周期
(打招呼→回复→简历→评分→面试)落库,形成可审计的链路。
后续 ReAct 决策、自我演进都依赖这张记忆。
"""
from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from typing import Any, Iterator

from config import cfg

SCHEMA = """
CREATE TABLE IF NOT EXISTS candidates (
    boss_id        TEXT PRIMARY KEY,
    name           TEXT,
    title          TEXT,
    company        TEXT,
    card_json      TEXT,           -- 原始候选人卡片
    profile_json   TEXT,           -- LLM 生成的画像
    score          REAL,
    status         TEXT NOT NULL DEFAULT 'new',
    -- new|greeted|replied|resume_received|scored|interview_scheduled|rejected|talent_pool
    skill_match    REAL,
    created_at     REAL NOT NULL,
    updated_at     REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS interactions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    boss_id        TEXT NOT NULL,
    direction      TEXT NOT NULL,  -- out(我发出)|in(对方来)
    kind           TEXT NOT NULL,  -- greet|reply|followup|resume_share|faq|system
    content        TEXT,
    ts             REAL NOT NULL,
    FOREIGN KEY (boss_id) REFERENCES candidates(boss_id)
);
CREATE INDEX IF NOT EXISTS idx_interactions_boss ON interactions(boss_id);
CREATE INDEX IF NOT EXISTS idx_interactions_ts   ON interactions(ts);

CREATE TABLE IF NOT EXISTS resumes (
    boss_id        TEXT PRIMARY KEY,
    file_path      TEXT,
    parsed_text    TEXT,
    parse_status   TEXT,           -- pending|ok|failed
    created_at     REAL NOT NULL,
    FOREIGN KEY (boss_id) REFERENCES candidates(boss_id)
);

CREATE TABLE IF NOT EXISTS faq (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    question       TEXT UNIQUE,
    answer         TEXT,
    hit_count      INTEGER NOT NULL DEFAULT 0,
    created_at     REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS daily_quota (
    day            TEXT PRIMARY KEY,   -- YYYY-MM-DD
    greeted        INTEGER NOT NULL DEFAULT 0,
    limit_override INTEGER              -- 某天想临时改上限可填这里
);
"""


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    db_path = cfg.path("db_path")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)


# ---------------- 候选人 ----------------

def upsert_candidate(
    boss_id: str,
    name: str | None = None,
    title: str | None = None,
    company: str | None = None,
    card_json: dict | None = None,
    skill_match: float | None = None,
    status: str = "new",
) -> None:
    now = time.time()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO candidates
                (boss_id, name, title, company, card_json, skill_match, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(boss_id) DO UPDATE SET
                name=excluded.name, title=excluded.title, company=excluded.company,
                card_json=excluded.card_json, skill_match=excluded.skill_match,
                status=excluded.status, updated_at=excluded.updated_at
            """,
            (
                boss_id, name, title, company,
                json.dumps(card_json, ensure_ascii=False) if card_json else None,
                skill_match, status, now, now,
            ),
        )


def set_profile(boss_id: str, profile: dict, score: float) -> None:
    now = time.time()
    with get_conn() as conn:
        conn.execute(
            "UPDATE candidates SET profile_json=?, score=?, status='scored', updated_at=? WHERE boss_id=?",
            (json.dumps(profile, ensure_ascii=False), score, now, boss_id),
        )


def get_candidate(boss_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM candidates WHERE boss_id=?", (boss_id,)).fetchone()
        return _row_to_dict(row)


def list_by_status(status: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM candidates WHERE status=? ORDER BY score DESC NULLS LAST", (status,)
        ).fetchall()
        return [_row_to_dict(r) for r in rows]


# ---------------- 互动 ----------------

def log_interaction(
    boss_id: str, direction: str, kind: str, content: str | None
) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO interactions (boss_id, direction, kind, content, ts) VALUES (?, ?, ?, ?, ?)",
            (boss_id, direction, kind, content, time.time()),
        )


def interaction_history(boss_id: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM interactions WHERE boss_id=? ORDER BY ts ASC", (boss_id,)
        ).fetchall()
        return [_row_to_dict(r) for r in rows]


# ---------------- 简历 ----------------

def save_resume(boss_id: str, file_path: str, parsed_text: str | None, status: str) -> None:
    now = time.time()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO resumes (boss_id, file_path, parsed_text, parse_status, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(boss_id) DO UPDATE SET
                file_path=excluded.file_path, parsed_text=excluded.parsed_text,
                parse_status=excluded.parse_status, created_at=excluded.created_at
            """,
            (boss_id, file_path, parsed_text, status, now),
        )
        conn.execute(
            "UPDATE candidates SET status='resume_received', updated_at=? WHERE boss_id=?",
            (now, boss_id),
        )


# ---------------- FAQ ----------------

def faq_answer(question: str) -> str | None:
    """简单模糊匹配。生产可换向量检索,这里留口子。命中则计数 +1。"""
    q_lower = question.lower()
    with get_conn() as conn:
        rows = conn.execute("SELECT id, question, answer FROM faq").fetchall()
        for r in rows:
            if r["question"].lower() in q_lower or q_lower in r["question"].lower():
                conn.execute("UPDATE faq SET hit_count = hit_count + 1 WHERE id=?", (r["id"],))
                return r["answer"]
    return None


def faq_add(question: str, answer: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO faq (question, answer, created_at) VALUES (?, ?, ?)",
            (question, answer, time.time()),
        )


# ---------------- 配额 ----------------

def daily_greeted() -> tuple[str, int]:
    """返回 (今天日期字符串, 今天已打招呼数)。"""
    import datetime
    day = datetime.date.today().isoformat()
    with get_conn() as conn:
        row = conn.execute("SELECT greeted, limit_override FROM daily_quota WHERE day=?", (day,)).fetchone()
        greeted = row["greeted"] if row else 0
    return day, greeted


def daily_limit() -> int:
    import datetime
    day = datetime.date.today().isoformat()
    with get_conn() as conn:
        row = conn.execute("SELECT limit_override FROM daily_quota WHERE day=?", (day,)).fetchone()
    base = cfg.get("boss.daily_greet_limit", 80)
    return row["limit_override"] if (row and row["limit_override"] is not None) else base


def increment_quota() -> int:
    import datetime
    day = datetime.date.today().isoformat()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO daily_quota (day, greeted) VALUES (?, 1) "
            "ON CONFLICT(day) DO UPDATE SET greeted = greeted + 1",
            (day,),
        )
        row = conn.execute("SELECT greeted FROM daily_quota WHERE day=?", (day,)).fetchone()
    return row["greeted"]


def _row_to_dict(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    d = dict(row)
    # 顺手把 JSON 字段解码,调用方更方便
    for k in ("card_json", "profile_json"):
        if d.get(k):
            try:
                d[k] = json.loads(d[k])
            except json.JSONDecodeError:
                pass
    return d


# 模块 import 时确保库存在
init_db()
