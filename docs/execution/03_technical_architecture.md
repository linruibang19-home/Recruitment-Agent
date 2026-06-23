# 03 Technical Architecture

## 技术选型

后端：

- Python 3.12
- FastAPI
- SQLAlchemy 2.x
- Alembic
- PostgreSQL
- APScheduler
- Pydantic v2

前端：

- React
- Vite
- TypeScript
- TanStack Query
- shadcn/ui 或轻量组件体系

浏览器自动化：

- Playwright 作为主实现。
- browser-use 可作为探索或低优先级辅助，不作为核心点击链路。

Agent 和 LLM：

- LangGraph 用于状态机、checkpoint、人审节点和失败恢复。
- LangChain 可用于文档加载、Prompt 模板、向量检索等辅助能力。
- LLM 客户端使用 OpenAI-compatible 接口，支持 DeepSeek、Qwen、OpenAI 等。

简历解析：

- PyMuPDF: PDF 文本提取。
- OCR: PaddleOCR 或 Tesseract。
- 多模态 LLM: 作为 OCR 失败或版式复杂时的补充。

## 系统分层

```text
Frontend
  -> FastAPI API
    -> Application Services
      -> LangGraph Workflows
      -> Playwright Browser Worker
      -> Resume Parser
      -> LLM Services
      -> Scoring Service
    -> PostgreSQL
    -> Local File Storage
```

## 后端模块

建议目录：

```text
backend/
  app/
    api/
      routes/
    core/
      config.py
      logging.py
      security.py
    db/
      models.py
      session.py
      repositories/
    browser/
      session.py
      boss_chat.py
      boss_recommend.py
      selectors.py
    workflows/
      chat_resume_graph.py
      recommend_talent_graph.py
      daily_recommend_graph.py
    services/
      resume_parser.py
      ocr.py
      llm_client.py
      profiler.py
      scorer.py
      message_generator.py
      quota.py
      audit.py
    schemas/
    workers/
```

前端目录：

```text
frontend/
  src/
    pages/
      Dashboard.tsx
      Candidates.tsx
      CandidateDetail.tsx
      Jobs.tsx
      ActionQueue.tsx
      Automation.tsx
      AuditLogs.tsx
    components/
    api/
    lib/
```

## PostgreSQL 核心表

```text
jobs
candidates
candidate_profiles
resumes
interactions
scores
recommendations
action_queue
daily_quota
workflow_runs
audit_logs
automation_settings
```

## 浏览器自动化策略

原则：

1. Playwright 负责确定性页面操作。
2. 关键选择器集中维护在 `selectors.py`。
3. 每个页面动作都记录 audit log。
4. 每次失败保存截图和 HTML 片段。
5. 遇到验证码、登录失效、账号异常立即停止。

浏览器会话：

- 使用持久化 Chrome profile。
- 用户手动登录。
- 系统只复用登录态，不处理验证码绕过。

## LangGraph 节点设计

沟通页简历处理图：

```text
load_conversation
extract_candidate
detect_resume
request_resume_or_accept
fetch_resume
parse_resume
profile_candidate
score_candidate
decide_action
human_review_or_finish
```

推荐牛人触达图：

```text
load_recommend_page
apply_filters
extract_cards
dedupe
pre_score
quota_check
draft_greeting
human_review_or_send
record_result
```

每日推荐图：

```text
load_candidates
rank
generate_reasons
draft_interview_invites
save_report
notify
```

## API 草案

```text
GET    /api/health
GET    /api/jobs
POST   /api/jobs
GET    /api/candidates
GET    /api/candidates/{id}
GET    /api/recommendations/today
GET    /api/actions
POST   /api/actions/{id}/approve
POST   /api/actions/{id}/reject
POST   /api/automation/chat/scan
POST   /api/automation/recommend/run
POST   /api/automation/stop
GET    /api/audit-logs
```

## 配置策略

使用 `.env` 管理敏感配置，使用 `config.yaml` 或数据库表管理业务配置。

关键配置：

```yaml
automation:
  max_daily_greetings: 50
  max_hourly_greetings: 10
  auto_accept_resume: true
  auto_parse_resume: true
  auto_request_resume: false
  auto_invite_interview: false

risk_control:
  stop_on_captcha: true
  stop_on_login_required: true
  stop_on_send_failure_count: 3
```

