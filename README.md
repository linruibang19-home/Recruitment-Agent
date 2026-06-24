# Recruitment Agent

本地运行的招聘 Agent 控制台，用于辅助 BOSS 直聘企业端候选人沟通、简历收集、简历解析、候选人画像、岗位匹配评分和每日推荐。

当前架构：`FastAPI + React + PostgreSQL + Playwright + LangGraph`。

## 文档

执行文档位于 [docs/execution](docs/execution/README.md)。

关键文档：

- [需求范围](docs/execution/01_requirements.md)
- [业务架构](docs/execution/02_business_architecture.md)
- [技术架构](docs/execution/03_technical_architecture.md)
- [阶段计划](docs/execution/04_delivery_plan.md)
- [风控策略](docs/execution/05_risk_control.md)
- [Git 工作流](docs/execution/06_git_workflow.md)
- [数据库初始化](docs/execution/08_database_setup.md)

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
http://127.0.0.1:8000/api/health/database
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

数据库连接示例：

```text
DATABASE_URL=postgresql+psycopg://postgres:<password>@localhost:5432/recruitment_agent
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

如果密码包含 `#`，需要写成 `%23`。

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

## 当前阶段

已完成：

- Phase 1: 基础架构重构
- Phase 2: PostgreSQL 数据层
- Phase 3: 前端控制台接入真实 API
- Phase 4: BOSS 沟通页只读扫描和附件识别
- Phase 5: 简历解析、候选人画像和岗位评分
- Phase 6: 每日推荐和约面草稿
- Phase 7: 推荐牛人筛选和触达草稿

Phase 7 已交付：

- 推荐牛人页面只读卡片采集
- 城市、学历、经验、意向、薪资和关键词筛选
- BOSS UID 候选人去重
- 索要 PDF 简历草稿
- 每日 50 条硬额度
- 草稿进入人工确认队列

使用步骤：

1. 进入“沟通采集”启动浏览器并手工登录。
2. 进入“推荐牛人”，设置筛选条件。
3. 点击“扫描并生成草稿”。
4. 进入“待确认”审核索要简历草稿。

自动发送仍然关闭，通过草稿不会向 BOSS 发送消息。

后续阶段：

- Phase 8: LangGraph 工作流和人审闭环
