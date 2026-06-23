"""命令行入口。

用法(在 src/ 目录下运行):
  python cli.py run        启动常驻调度器(每日打招呼 + 定时巡检)
  python cli.py watch      只跑一次巡检
  python cli.py daily      只跑一次每日打招呼流程
  python cli.py top [N]    看评分 Top N 候选人
  python cli.py show <id>  看某候选人画像
  python cli.py faq list   看 FAQ 库
  python cli.py faq add <问> <答>   往 FAQ 库加一条
"""
from __future__ import annotations

import asyncio
import sys


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]

    if cmd == "run":
        from scheduler import run
        run()
    elif cmd == "daily":
        from scheduler import daily_run
        asyncio.run(daily_run())
    elif cmd == "watch":
        from scheduler import watch_loop
        asyncio.run(watch_loop())
    elif cmd == "top":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        _print_top(n)
    elif cmd == "show":
        if len(sys.argv) < 3:
            print("用法: show <boss_id>"); return
        _print_candidate(sys.argv[2])
    elif cmd == "faq":
        _faq(sys.argv[2:])
    else:
        print(f"未知命令: {cmd}\n"); print(__doc__)


def _print_top(n: int) -> None:
    from db import get_conn
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT boss_id, name, title, company, score, status "
            "FROM candidates ORDER BY score DESC LIMIT ?", (n,)
        ).fetchall()
    if not rows:
        print("(暂无候选人)"); return
    for i, r in enumerate(rows, 1):
        print(f"{i}. {r['name']} | {r['score']} | {r['title']} @ {r['company']} | {r['status']}")


def _print_candidate(boss_id: str) -> None:
    from db import get_candidate
    import json
    c = get_candidate(boss_id)
    if not c:
        print("查无此人"); return
    print(json.dumps(c, ensure_ascii=False, indent=2))


def _faq(args: list[str]) -> None:
    from db import get_conn
    if not args or args[0] == "list":
        with get_conn() as conn:
            rows = conn.execute("SELECT question, answer, hit_count FROM faq").fetchall()
        for r in rows:
            print(f"[{r['hit_count']}] {r['question']} -> {r['answer']}")
    elif args[0] == "add" and len(args) >= 3:
        from db import faq_add
        faq_add(args[1], args[2])
        print("已添加")
    else:
        print("用法: faq list | faq add <问题> <答案>")


if __name__ == "__main__":
    main()
