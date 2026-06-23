# 08 Database Setup

## 目标

Phase 2 使用本机 PostgreSQL 作为长期数据存储。数据库连接由 `.env` 中的 `DATABASE_URL` 控制。

默认示例：

```text
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/recruitment_agent
```

如果你安装 PostgreSQL 时设置的 `postgres` 密码不是 `postgres`，需要修改 `.env`。

## 创建数据库

在 PowerShell 中执行：

```powershell
psql -U postgres -h localhost -p 5432 -c "CREATE DATABASE recruitment_agent;"
```

如果提示密码错误，说明 `.env` 中也需要改成你本机真实密码：

```text
DATABASE_URL=postgresql+psycopg://postgres:<你的密码>@localhost:5432/recruitment_agent
```

如果数据库已存在，会看到 `database already exists` 类似提示，可以忽略或跳过创建。

## 执行迁移

```powershell
cd backend
python -m alembic -c alembic.ini upgrade head
```

## 检查连接

启动后端：

```powershell
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

访问：

```text
http://127.0.0.1:8000/api/health/database
```

成功时返回：

```json
{"status":"ok","database_configured":true}
```

## 当前核心表

- `jobs`
- `candidates`
- `candidate_profiles`
- `resumes`
- `interactions`
- `scores`
- `recommendations`
- `action_queue`
- `daily_quota`
- `workflow_runs`
- `audit_logs`

## 设计原则

- 使用 `bigint identity` 作为内部主键。
- BOSS 外部 ID 使用 `boss_uid` 单独唯一约束。
- 常用筛选字段使用普通列，不把所有内容塞进 JSONB。
- LLM 原始结构化输出、技能、亮点、风险等保留 JSONB。
- 所有外键列都建索引或组合索引。
- 高频查询使用组合索引，例如 `status + updated_at`、`job_id + total_score`。

