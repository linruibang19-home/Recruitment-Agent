# 07 Phase Status

## Phase 1 Status

状态：完成基础骨架实现，等待 Phase 2 PostgreSQL 数据层。

完成内容：

- 移除旧 CLI 原型代码。
- 新增 `backend/` FastAPI 应用骨架。
- 新增 `/api/health` 健康检查。
- 新增 `frontend/` React + Vite 控制台首屏。
- 新增根级 `requirements.txt` 和 `backend/requirements.txt`。
- 更新 `.env.example`、`config.example.yaml`、`README.md`。
- 增加 `.gitattributes`，稳定跨平台文本换行。

自检结果：

- `python -m compileall -q backend`: 通过。
- `from app.main import app`: 通过。
- `GET /api/health`: 200。
- `npm run build`: 通过。
- Playwright + 本机 Chrome 截图：桌面和移动端通过人工视觉检查。

环境备注：

- Python Playwright 自带 Chromium 下载超时，截图自检改用本机 Chrome 可执行文件。
- 已尝试 `PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright`，但当前 Playwright 版本所需的 Chrome for Testing 资源在镜像上返回 404。
- 后续自动化优先使用本机 Chrome：通过 `CHROME_EXECUTABLE_PATH` 和 `PLAYWRIGHT_BROWSER_CHANNEL=chrome` 配置。
- 全局 Python 环境存在部分历史包冲突提示，后续开发建议使用项目虚拟环境。

下一阶段：

- Phase 2: PostgreSQL 数据层。
- 建立 SQLAlchemy models、Alembic migrations、数据库初始化说明和基础 CRUD API。

## Phase 2 Status

状态：代码实现完成，本机数据库实连待 `.env` 设置正确 PostgreSQL 密码后执行迁移。

完成内容：

- 新增 SQLAlchemy 2.x 数据模型。
- 新增 Alembic 配置和初始迁移。
- 新增 PostgreSQL 初始化文档。
- 新增岗位 `jobs` 基础 CRUD API。
- 新增候选人 `candidates` 基础 CRUD API。
- 新增 `/api/health/database` 数据库健康检查。

核心表：

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

自检结果：

- `python -m compileall -q backend`: 通过。
- `from app.main import app`: 通过。
- Alembic 离线 SQL 生成：通过。
- SQLAlchemy metadata 表数量：11。
- `/api/health`: 通过。
- `/api/health/database`: 当前返回 `error`，原因是本机 PostgreSQL 的 `postgres/postgres` 默认密码不匹配。

数据库连接备注：

- PostgreSQL 16 服务已检测为运行中。
- `psql` 已安装在 `C:\Program Files\PostgreSQL\16\bin\psql.exe`。
- 需要在 `.env` 中把 `DATABASE_URL` 改成你的本机真实 PostgreSQL 用户和密码，然后运行：

```powershell
cd backend
python -m alembic -c alembic.ini upgrade head
```
