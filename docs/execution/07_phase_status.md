# 07 Phase Status

## Phase 10 Status

状态：完成。

截至 2026-06-26，默认采集入口已切换为普通 Chrome 扩展桥接。Playwright 浏览器会话保留为
历史兼容代码，不再作为前端默认采集路径。

完成内容：

- Manifest V3 项目扩展及安装说明。
- 扩展心跳与 PostgreSQL 持久化任务队列。
- 沟通列表、当前聊天、附件和推荐牛人页面解析。
- 沟通页批量读取：扩展可逐个打开左侧可见会话，读取聊天详情和附件卡片。
- 沟通页批量索要简历：每批最多处理 20 个未读/红点会话，仅发送固定索要简历话术。
- 批量索要简历会跳过已有简历附件、已索要过简历或候选人已表达简历已发送的会话。
- 批量索要简历回传发送数、已有简历跳过数、已索要跳过数和失败数，便于测试和审计。
- 扩展长任务支持暂停、继续和停止控制。
- 候选人、消息去重入库和索要简历草稿。
- PDF 直链接入既有解析、OCR、画像和评分流程。
- 无直链附件简历支持点击预览并提取预览文本，进入文本简历处理、画像和评分流程。
- 前端扩展状态、任务提交和任务记录。
- DOM 解析自动化测试与真实数据库闭环验证。
- `PYTHONPATH=backend pytest tests -q`: 19 项通过。
- `npm run build`: 通过。
- `python -m alembic -c alembic.ini upgrade head`: 已升级到 `20260627_0004`。

### AI / OCR 补充验收

- 新增 `/api/health/ai`，可查看本机 OCR 和 LLM 配置状态，不返回 API key 内容。
- OCR 使用本地 Tesseract，默认语言为 `chi_sim+eng`，扫描型 PDF 会走 OCR 兜底。
- DeepSeek LLM 已改用 `deepseek-v4-flash`，默认 Base URL 为 `https://api.deepseek.com`。
- 本地实测 DeepSeek 调用成功，简历画像增强返回 `parser=deepseek`。
- 本地实测图片型 PDF 触发 OCR，返回 `ocr_used=true` 并提取到文本。
- 前端系统设置新增 AI 能力状态卡，展示 OCR 可用性、OCR 语言和 LLM 模型状态。

### 自动循环与审计补充验收

- 新增沟通页自动循环控制：显式启动后才会按随机间隔创建批量索要简历任务。
- 自动循环每批最多处理 20 个未读/红点会话，并在有同类任务排队或运行时不创建新批次。
- 自动循环检测每日主动触达额度，额度为 0 时自动停止并写入审计日志。
- 扩展任务实际发送索要简历话术后，会按 `sent_count` 写入当天 `daily_quota.used_count`。
- 新增 `/api/automation/chat-loop/status`、`/start`、`/pause` 三个循环控制接口。
- 审计日志新增分页、状态筛选和单条详情接口，前端支持点击日志查看 payload、截图路径和关联实体。
- 前端沟通采集页新增自动循环状态卡；审计日志页新增分页列表、详情面板和刷新筛选工具栏。
- 新增一键停止全部未完成扩展任务接口，停止时同步暂停自动循环，避免遗留队列继续执行。
- 工作流页关闭手动启动入口，改为只读监控、人工确认和失败恢复，避免数据库候选人与当前 BOSS 聊天页脱节。
- Chrome 扩展读取会话前会尝试关闭 BOSS 资料/简历弹层，并对左侧会话列表去重，降低重复处理同一候选人的概率。

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

### Phase 4 Frontend Refinement

- 桌面侧栏在常见笔记本宽度下保持模块名称可见。
- 导航名称调整为招聘业务术语：工作台、岗位管理、候选人库、待确认、沟通采集、审计日志。
- 左下角状态占位改为可点击的“系统设置”入口。
- 新增系统设置页，展示运行环境、自动化安全策略和本地数据目录。
- 各模块使用独立页面标题和说明，不再统一显示阶段性开发文案。
- 收紧字号、阴影、间距和面板密度，降低原型感。
- 候选人表在 1134px 宽度下无需横向滚动。

## Phase 5 Status

状态：完成简历解析、候选人画像和岗位评分。

完成内容：

- 新增 PDF 上传、文件类型校验和 10 MB 大小限制。
- 使用 PyMuPDF 提取原生文本。
- 原生文本不足时使用 Tesseract OCR，支持中文和英文模型。
- 新增本地规则结构化解析器。
- 新增可配置 DeepSeek LLM 增强，默认关闭并对手机号、邮箱脱敏。
- 提取学历、学校、专业、毕业年份、候选类型、技能、项目和工作年限。
- 候选人画像、亮点、风险和摘要写入 PostgreSQL。
- 新增 100 分制岗位评分及五个维度理由。
- 新增候选人详情、简历上传、岗位选择、画像和评分前端页面。
- 简历处理成功和失败均写入审计日志。

新增 API：

- `GET /api/candidates/{candidate_id}/detail`
- `POST /api/candidates/{candidate_id}/resumes`
- `POST /api/candidates/{candidate_id}/scores/{job_id}`

自检结果：

- `python -m compileall -q backend`: 通过。
- `npm run build`: 通过。
- 5 份不同格式文本型 PDF 解析：通过。
- 五份简历均提取学校、专业、技能和项目经历：通过。
- 五份简历岗位评分及维度理由：通过。
- 扫描图片型 PDF 中文 OCR：通过。
- OCR 结果识别学校、专业、毕业年份和技能：通过。
- 前端 PDF 上传、解析、评分和详情展示：通过。
- Playwright 桌面和移动端检查：通过。
- 移动端无整页横向溢出。
- 浏览器控制台错误和警告：无。

环境备注：

- 本机已安装 Tesseract 5.4。
- 中文、英文和方向模型位于 `data/tessdata/`，不会进入 Git。
- LLM 默认关闭；当前验收使用本地规则解析器，不依赖外部 API。

下一阶段：

- Phase 6: 每日候选人推荐和约面草稿。
- 按岗位生成 Top N、推荐理由、风险说明和待确认约面话术。

## Phase 6 Status

状态：完成每日推荐、约面草稿和人工审核闭环。

完成内容：

- 按启用岗位读取已评分候选人并生成 Top N。
- 推荐结果包含总分、推荐理由、亮点和风险。
- 达到阈值的候选人生成约面草稿。
- 草稿以高风险动作进入 PostgreSQL 待确认队列。
- 支持人工通过和拒绝，审核不触发发送。
- 同日重复生成不会重复创建草稿。
- 同日已拒绝草稿不会被重新创建。
- 新增 APScheduler 每日 09:00 定时任务，使用 Asia/Shanghai 时区。
- 新增前端“每日推荐”和真实“待确认”页面。

新增 API：

- `GET /api/recommendations/today`
- `POST /api/recommendations/generate`
- `GET /api/actions`
- `POST /api/actions/{action_id}/approve`
- `POST /api/actions/{action_id}/reject`

自检结果：

- `python -m compileall -q backend`: 通过。
- `npm run build`: 通过。
- 三名候选人按 92、78、60 分正确取 Top 2：通过。
- 重复生成不重复创建约面草稿：通过。
- 低于 70 分不生成约面草稿：通过。
- 拒绝草稿后同日不重新创建：通过。
- 人工通过和拒绝状态更新：通过。
- 前端推荐生成、排名展示和审核交互：通过。
- Playwright 桌面和移动端检查：通过。
- 移动端无整页横向溢出。
- 浏览器控制台错误和警告：无。

下一阶段：

- Phase 7: 推荐牛人筛选、卡片读取、打招呼草稿和每日额度。
- 自动发送继续保持关闭，触达动作进入待确认队列。

## Phase 7 Status

状态：完成推荐牛人只读采集、筛选、去重、草稿和额度。

完成内容：

- Playwright 打开并读取 BOSS 推荐牛人页面。
- 新增推荐卡片提取器。
- 支持城市、学历、经验、求职意向、薪资和岗位关键词本地筛选。
- 使用 BOSS UID 或卡片指纹去重。
- 匹配候选人写入候选人库，来源标记为 `boss_recommend`。
- 生成索要 PDF 简历草稿，动作类型为 `request_resume_greeting`。
- 草稿全部进入待确认队列，`auto_send=false`。
- 新增每日 50 条额度，待确认和已通过草稿会预留额度。
- 自动发送和平台页面写操作保持关闭。
- 新增前端“推荐牛人”筛选与结果页面。

新增 API：

- `GET /api/quota/greetings`
- `POST /api/automation/recommend/scan`

自检结果：

- `python -m compileall -q backend`: 通过。
- `npm run build`: 通过。
- 推荐卡片静态 DOM 提取：通过。
- 城市、学历、经验和关键词筛选：通过。
- 每日上限设为 2 时最多生成 2 条草稿：通过。
- 重复扫描不重复创建草稿：通过。
- 草稿全部标记 `auto_send=false`：通过。
- 额度待确认、已通过和可用数量计算：通过。
- 真实 Chrome 访问时检测到 BOSS 用户验证页面并安全停机：通过。

下一阶段：

- Phase 8: LangGraph 工作流和人工审核闭环。
- 增加 checkpoint、失败恢复、流程运行记录和可视化。

## Phase 8 Status

状态：完成 LangGraph 工作流、PostgreSQL checkpoint 和人工审核闭环。

完成内容：

- 新增沟通页简历处理、推荐牛人触达、每日推荐三个 LangGraph。
- 每个节点执行后将状态、当前节点和历史轨迹写入 `workflow_runs`。
- 服务重启后可从数据库中的 `current_node` 恢复。
- `human_review` 节点暂停，支持批准继续和拒绝结束。
- 失败任务记录异常并支持从当前节点重试。
- 简历解析、推荐牛人草稿和每日推荐自动创建对应工作流。
- 新增“工作流”前端页面，查看运行记录、节点轨迹和审核状态。
- 审核通过只更新草稿和流程状态，不执行 BOSS 页面发送。

新增 API：

- `GET /api/workflows`
- `GET /api/workflows/{id}`
- `POST /api/workflows`
- `POST /api/workflows/{id}/review`
- `POST /api/workflows/{id}/retry`

自检结果：

- 三类图均可运行至人工确认节点。
- 人工批准后继续到完成状态。
- 人工拒绝后进入拒绝状态。
- 工作流状态和节点轨迹可从 PostgreSQL 读取。
- 后端编译和前端生产构建通过。
- 自动发送保持关闭。

下一阶段：

- Phase 9: 稳定性、审计、安全和本地打包。
- 补充核心自动化测试、敏感数据脱敏、运行恢复手册和发布检查。

## Phase 9 Status

状态：完成稳定性、安全、自动化测试和本地运行交付。

完成内容：

- 审计日志递归脱敏手机号、邮箱、身份证号、微信号和本地绝对路径。
- 审计截图保存项目内相对路径，不暴露用户目录。
- 候选人删除接口要求显式确认，并级联删除业务数据。
- 删除候选人时清理受控目录内的本地简历文件。
- 浏览器操作连续失败 3 次后进入 `blocked`，等待人工检查。
- 新增数据库、浏览器和写操作安全状态健康检查。
- 新增 PowerShell 启动、停止、状态脚本，停止时清理前后端进程树。
- 新增安全、筛选、LangGraph 和异常停机自动化测试。
- 前端候选人详情新增删除入口和二次确认。
- 系统设置展示连续失败计数和审计脱敏策略。

新增 API：

- `DELETE /api/candidates/{id}?confirm=true`
- `GET /api/health/automation`

自检结果：

- `python -m pytest -q`: 11 项通过。
- 后端编译和前端生产构建通过。
- 候选人删除确认、删除和 404 回查通过。
- 启停脚本释放并恢复 8000、5173 端口。
- 自动化健康接口确认外部写操作关闭。

外部工具状态：

- Codex Chrome 插件包已安装。
- 当前 Chrome Profile 缺少 Codex Chrome Extension，native host 也未注册。
- 需要从 Codex 插件管理重装 `chrome` 插件后再复测扩展连接。
