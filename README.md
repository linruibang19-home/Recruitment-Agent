# Recruitment Agent

一个本地运行的招聘 Agent 控制台，用于辅助 BOSS 直聘企业端候选人沟通、简历收集、简历解析、候选人画像、岗位匹配评分和每日推荐。

当前处于 Phase 1：基础架构重构。旧 CLI 原型已移除，项目正在迁移到 `FastAPI + React + PostgreSQL + Playwright + LangGraph` 架构。

## 文档

执行文档位于 [docs/execution](docs/execution/README.md)。

关键文档：

- [需求范围](docs/execution/01_requirements.md)
- [业务架构](docs/execution/02_business_architecture.md)
- [技术架构](docs/execution/03_technical_architecture.md)
- [阶段计划](docs/execution/04_delivery_plan.md)
- [风控策略](docs/execution/05_risk_control.md)
- [Git 工作流](docs/execution/06_git_workflow.md)

## 项目结构

```text
backend/        FastAPI 后端
frontend/       React + Vite 前端
docs/execution/ 项目执行文档
data/           本地运行数据，默认不进入 Git
```

## 后端启动

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

健康检查：

```text
http://127.0.0.1:8000/api/health
```

## 前端启动

```bash
cd frontend
npm install
npm run dev
```

默认地址：

```text
http://127.0.0.1:5173
```

## 环境变量

复制 `.env.example` 为 `.env` 并按本机环境修改。`.env` 不会进入 Git。

```bash
copy .env.example .env
```

Playwright 可以使用自带 Chromium，也可以使用本机 Chrome。当前推荐使用本机 Chrome：

```text
CHROME_EXECUTABLE_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe
PLAYWRIGHT_BROWSER_CHANNEL=chrome
```

## 数据库

数据库初始化和迁移说明见 [docs/execution/08_database_setup.md](docs/execution/08_database_setup.md)。

核心命令：

```bash
cd backend
python -m alembic -c alembic.ini upgrade head
```

## 当前阶段边界

当前已完成 Phase 1 基础架构和 Phase 2 数据层代码。数据库实连需要 `.env` 中的 `DATABASE_URL` 与本机 PostgreSQL 密码一致。

Phase 1 已交付：

- 后端健康检查接口
- 前端控制台首屏
- 基础配置结构
- Git 和文档治理

Phase 2 已交付：

- SQLAlchemy 数据模型
- Alembic 初始迁移
- 岗位和候选人基础 CRUD API
- 数据库健康检查

BOSS 页面自动化、简历解析、评分推荐和 LangGraph 工作流将在后续阶段按文档推进。
