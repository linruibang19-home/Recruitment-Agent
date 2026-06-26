# Recruitment Agent

本地运行的招聘 Agent 控制台，用于辅助 BOSS 直聘企业端候选人沟通、简历收集、简历解析、候选人画像、岗位匹配评分和每日推荐。

当前架构：`FastAPI + React + PostgreSQL + Chrome Extension + LangGraph`。

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
browser-extension/ 普通 Chrome 登录态的只读采集扩展
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

BOSS 页面采集使用项目自带的 Chrome 扩展，不再依赖 Playwright 控制登录页面。
安装方式见 [browser-extension/README.md](browser-extension/README.md)。

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
- Phase 8: LangGraph 工作流和人审闭环
- Phase 9: 稳定性、审计、安全和本地运行
- Phase 10: 普通 Chrome 扩展桥接、真实页面采集和数据入库

Phase 10 补充能力：

- 沟通采集支持 `scan_chat_details` 批量任务：扩展会在当前 BOSS 沟通页逐个打开左侧可见会话，读取聊天详情和附件卡片。
- 批量读取结果会按候选人入库，未发现简历时生成索要简历待确认草稿，发现 PDF 附件时自动回传到简历解析流程。
- 扩展仍不填写输入框、不点击发送；所有求简历、约面试、打招呼动作只进入待确认队列。

Phase 9 已交付：

- 审计日志手机号、邮箱、身份证号、微信号和路径脱敏
- 候选人及其简历、画像、评分和沟通记录删除
- 浏览器连续失败 3 次安全停机
- 自动化健康检查
- 后端核心测试套件
- Windows 一键启动、停止和状态脚本

使用步骤：

```powershell
.\scripts\start.ps1
.\scripts\status.ps1
.\scripts\stop.ps1
```

首次使用时在 `chrome://extensions` 加载项目的 `browser-extension` 文件夹，然后打开并登录
BOSS 直聘。控制台“沟通采集”页面会显示扩展连接状态。

开发测试：

```powershell
cd backend
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

自动发送仍然关闭，批准仅推进工作流并更新草稿状态。
