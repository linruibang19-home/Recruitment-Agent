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

## Phase 3 Status

状态：完成前端控制台真实 API 接入。

完成内容：

- 前端新增 API client。
- Dashboard 并行读取 `/api/health/database`、`/api/jobs`、`/api/candidates`。
- 指标卡、候选人流程、自动化健康、候选人库切换为真实后端数据。
- 增加刷新按钮和失败兜底状态。
- 保留本地 fallback 数据，避免 API 不可用时页面空白。

自检结果：

- PostgreSQL 实连：通过。
- Alembic 迁移：通过。
- `/api/health/database`: `ok`。
- `/api/jobs`: 1 条烟测岗位。
- `/api/candidates`: 1 条烟测候选人。
- `npm run build`: 通过。
- Playwright + 本机 Chrome 桌面截图：通过。
- Playwright + 本机 Chrome 移动截图：通过。
- 刷新按钮交互：通过。
- 浏览器控制台错误：无。

环境备注：

- 当前 `.env` 已使用本机 PostgreSQL `postgres` 用户连接。
- 用户提供的 `root` 用户认证失败；实际可用的是 `postgres` 用户配合同一密码。
- 密码包含 `#`，在 `DATABASE_URL` 中必须写成 `%23`。

下一阶段：

- Phase 4: BOSS 沟通页读取和简历附件识别。
- 实现 Playwright 持久化浏览器会话、沟通页列表读取、聊天详情读取、附件卡片识别和审计截图。

## Phase 4 Status

状态：完成 BOSS 沟通页只读浏览器链路。

完成内容：

- 新增独立线程和 Windows Proactor 事件循环承载 Playwright，避免 Uvicorn 事件循环无法创建浏览器子进程。
- 新增持久化 Chrome profile，登录态保存在 `data/profiles/boss-chrome`。
- 新增浏览器启动、状态查询和停止 API。
- 新增沟通列表只读扫描、指定候选人聊天读取和 PDF 附件卡片识别。
- 新增成功/失败截图路径和 PostgreSQL 审计日志。
- 前端“自动化”页面接入真实浏览器状态、扫描结果和附件结果。
- 前端“审计日志”页面接入真实数据库记录。
- 登录、验证码、账号异常和访问限制出现时禁止继续扫描。
- 本阶段不填写输入框、不点击发送、不执行任何消息发送动作。

新增 API：

- `GET /api/automation/browser/status`
- `POST /api/automation/browser/start`
- `POST /api/automation/browser/stop`
- `POST /api/automation/chat/scan`
- `POST /api/automation/chat/open`
- `GET /api/audit-logs`

自检结果：

- `python -m compileall -q backend`: 通过。
- `npm run build`: 通过。
- 浏览器状态和审计 API：通过。
- 未启动浏览器时扫描返回 409：通过。
- 静态沟通页提取器识别 2 个会话、2 条消息和 1 个 PDF 附件：通过。
- 后端真实启动本机 Chrome 并打开 BOSS 沟通页：通过。
- 登录状态识别和浏览器正常停止：通过。
- Playwright 桌面和移动端渲染检查：通过。
- 自动化和审计导航交互：通过。
- 浏览器控制台错误和警告：无。

环境与边界：

- Browser 插件未安装，前端验收使用 Python Playwright 和本机 Chrome。
- BOSS 页面 DOM 可能随平台更新变化，选择器失配时应停止扫描并更新提取器。
- 完整真实会话和附件识别需要用户在独立 Chrome profile 中手工登录后再次验收。
- 截图、登录 profile 和后续简历文件均位于 `data/`，不会进入 Git。

下一阶段：

- Phase 5: 简历解析、候选人画像和岗位评分。
- 增加 PDF 文本提取、OCR 降级、结构化字段提取和可解释评分。
