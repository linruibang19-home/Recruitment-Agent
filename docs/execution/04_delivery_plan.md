# 04 Delivery Plan

## 里程碑总览

项目按阶段推进。每个阶段必须满足验收标准后再提交和推送。

```text
Phase 0: 项目治理和执行文档
Phase 1: 基础架构重构
Phase 2: PostgreSQL 数据层
Phase 3: 可视化控制台 MVP
Phase 4: BOSS 沟通页读取和简历处理
Phase 5: 简历解析、画像和评分
Phase 6: 每日推荐和约面草稿
Phase 7: 推荐牛人筛选和主动触达
Phase 8: LangGraph 工作流和人审闭环
Phase 9: 稳定性、审计、安全和打包
```

## Phase 0: 项目治理和执行文档

目标：

- 建立执行文档目录。
- 明确业务架构、技术架构、阶段计划、风险控制。
- 初始化 Git 管理并连接远程仓库。
- 修复 `.gitignore`，避免提交 `.env`、数据库、缓存、简历文件。

交付物：

- `docs/execution/README.md`
- `docs/execution/01_requirements.md`
- `docs/execution/02_business_architecture.md`
- `docs/execution/03_technical_architecture.md`
- `docs/execution/04_delivery_plan.md`
- `docs/execution/05_risk_control.md`
- `docs/execution/06_git_workflow.md`

验收标准：

- 文档可读且覆盖当前需求。
- 本地 Git 仓库初始化。
- 远程 origin 指向 `https://github.com/linruibang19-home/Recruitment-Agent.git`。
- 工作区无敏感文件被纳入版本管理。

## Phase 1: 基础架构重构

目标：

- 清理旧 CLI 骨架，建立新项目结构。
- 创建 FastAPI 后端和 React 前端。
- 建立统一配置、日志、错误处理。

交付物：

- `backend/`
- `frontend/`
- `docker-compose.yml` 或本地启动脚本
- `README.md` 新版启动说明

验收标准：

- 后端 `/api/health` 正常。
- 前端页面可打开。
- 后端能读取配置。
- 不依赖旧代码也能启动基础服务。

## Phase 2: PostgreSQL 数据层

目标：

- 接入本地 PostgreSQL。
- 建立核心表和迁移。
- 实现基础 repository。

交付物：

- SQLAlchemy models
- Alembic migrations
- 数据库初始化说明
- 基础 CRUD API

验收标准：

- 能创建和查询岗位、候选人、交互记录。
- 迁移可重复执行。
- `.env.example` 包含数据库配置模板。

## Phase 3: 可视化控制台 MVP

目标：

- 提供可视化页面查看候选人、岗位、动作队列和日志。

交付物：

- Dashboard
- Candidates
- Candidate Detail
- Jobs
- Action Queue
- Audit Logs

验收标准：

- 前端能展示数据库数据。
- 支持新建/编辑岗位配置。
- 支持查看待确认动作。

## Phase 4: BOSS 沟通页读取和简历处理

目标：

- 使用 Playwright 复用登录态。
- 读取沟通页会话列表。
- 打开聊天详情。
- 识别候选人信息、消息和附件。

交付物：

- Browser session manager
- Chat page extractor
- Attachment detector
- 失败截图和审计日志

验收标准：

- 能在人工登录后读取沟通列表。
- 能打开指定候选人聊天。
- 能识别 PDF 附件卡片。
- 不发送任何消息也能完成扫描。

## Phase 5: 简历解析、画像和评分

目标：

- PDF 文本提取。
- OCR 降级。
- LLM 结构化解析。
- 候选人画像和岗位评分。

交付物：

- Resume parser
- OCR service
- Profile generator
- Scoring service
- Candidate detail 展示画像和评分

验收标准：

- 能解析至少 5 份不同格式简历。
- 能结构化输出学历、学校、专业、毕业年份、技能、项目经历。
- 能给出总分、维度分和评分理由。

## Phase 6: 每日推荐和约面草稿

目标：

- 每天自动生成优秀候选人推荐。
- 给出推荐理由和约面草稿。

交付物：

- Daily recommendation job
- Recommendation UI
- Interview invite draft generator

验收标准：

- 能按岗位输出 Top N。
- 推荐理由可解释。
- 约面话术默认进入待确认队列。

## Phase 7: 推荐牛人筛选和主动触达

目标：

- 自动配置推荐牛人筛选条件。
- 读取推荐卡片。
- 根据每日 50 次上限控制触达。

交付物：

- Recommend page automation
- Quota service
- Greeting draft service
- Send queue

验收标准：

- 能读取推荐牛人卡片。
- 能按配置筛选和去重。
- 能生成打招呼草稿。
- 自动发送默认关闭；开启时受每日 50 次硬限制。

## Phase 8: LangGraph 工作流和人审闭环

目标：

- 将候选人处理流程迁移到 LangGraph。
- 支持 checkpoint、失败恢复和人审节点。

交付物：

- Chat resume graph
- Recommend talent graph
- Daily recommendation graph
- Workflow run viewer

验收标准：

- 每个候选人的处理状态可追踪。
- 人审动作能恢复工作流。
- 异常不会导致重复发送消息。

## Phase 9: 稳定性、审计、安全和打包

目标：

- 提升可靠性和长期运行能力。

交付物：

- 审计日志完善
- 敏感数据脱敏策略
- 自动化异常停机
- 测试用例
- 本地部署说明

验收标准：

- 核心服务有测试覆盖。
- 敏感文件不进入 Git。
- 验证码、登录失效、账号异常会停机。
- 有完整启动、停止、恢复说明。

