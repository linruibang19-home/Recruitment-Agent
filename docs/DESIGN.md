# 招聘 Agent 设计文档

> 这份文档既讲架构,也讲**每个模块在帮你练哪种 Agent 能力**。
> 你练手时对着这份文档看代码,就能清楚"这块在练什么"。

## 0. 一句话定位

一个**后台常驻的招聘自动化 Agent**:每天在 Boss 直聘上,以拟人化节奏筛选候选人、个性化打招呼、监听回复、解析简历、生成画像与评分、自主跟进直到约上面试。

**重要**:它不是一个一次性跑完的流水线,而是「定时唤醒 + 长期记忆 + 自主决策」的驻留型 Agent。

---

## 1. 为什么不用 LangGraph / Agent 框架

(已在对话里讨论过,这里记录结论)

- 真实形态是**驻留循环**,不是一次性 StateGraph。用图套 `while True` 比直接写循环更绕。
- browser-use 本身已是黑盒,再加一层框架,排查问题时要分清"是框架错了 / 浏览器错了 / LLM 错了",归因变难。
- 决策复杂度还没到需要状态机。MVP 阶段:browser-use + async Python + 轻量调度 + DeepSeek SDK,代码尽量扁、可读、可改。
- **练手目标**:自己手撸工具调用、ReAct、异常自适应,比套框架学到的东西多一个数量级。

未来如果膨胀到"多 Agent 协作",再考虑上框架。

---

## 2. 架构总览

```
                ┌──────────────────────────────────────┐
                │           scheduler.py (主调度)        │
                │  定时唤醒: 每日筛选窗口 / 每30分钟巡检  │
                └───────────────┬──────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
  ┌──────────┐          ┌──────────────┐        ┌──────────────┐
  │ daily_   │          │   watcher    │        │  followup    │
  │  run()   │          │   loop()     │        │  loop()      │
  └────┬─────┘          └──────┬───────┘        └──────┬───────┘
       │                       │                       │
       ▼                       ▼                       ▼
  screener → greeter     message_router           followuper
                              │
            ┌─────────────────┼─────────────────┐
            ▼                 ▼                 ▼
       resume_parser     reply_agent        faq_lookup
            │                 │
            ▼                 ▼
        profiler         scorer  →  obsidian_sync
```

所有模块共享:
- `browser_session`:浏览器登录态与操作(阶段 1)
- `db`:候选人 / 对话 / 简历 / 状态(数据层)
- `llm_client`:DeepSeek 封装,带 function calling
- `tools/`:供 LLM 调用的工具函数(阶段体现 Tool Use 能力)

---

## 3. 阶段 → 模块 → 练什么 Agent 能力

### 阶段 1:会话管理 — `src/browser_session.py`

- 职责:打开 Boss、自检登录态、过期则通知扫码、提供所有页面操作的统一入口。
- 练的 Agent 能力:**异常自适应**(感知"未登录/被风控/session 过期" → 诊断类型 → 决定"通知人 / 等待 / 重试")。
- 关键点:任何浏览器异常都要先 `classify_error()` 再决定动作,不要直接崩溃。

### 阶段 2:智能筛选 & 批量打招呼 — `src/screener.py` + `src/greeter.py`

- 职责:按筛选条件拉候选人 → LLM 评估匹配度 → 排序 → 拟人化节奏打招呼。
- 练的 Agent 能力:
  - **Tool Use**:把"打开搜索页""点打招呼""读取候选人卡片"包装成 tools,LLM 评估时按需调用。
  - **配额与优先级调度**:80 个额度如何分配(高匹配优先、深度跟进优先),这是带约束的决策。
  - **拟人化**:对数正态分布的间隔、随机浏览干扰动作 —— 反风控的核心。
- 招呼语:LLM 逐个生成,**绝不模板复用**(模板化是最明显的机器人指纹)。

### 阶段 3:监听回复 & 索取简历 — `src/watcher.py` + `src/reply_agent.py`

- 职责:每 30 分钟巡检消息页,对新回复做**意图理解 + 自主分支**。
- 练的 Agent 能力(**本项目最练手的地方**):
  - **ReAct(Reason + Act)**:对方说"你们公司多少人?"→ Agent 先推理意图 → 决定"调 FAQ 查询"还是"标记需人工"。
  - **开放性对话处理**:真实回复无法穷举 if-else,必须靠 LLM 理解 + 工具组合。
  - **失败换策略**:2 天没回复 → 跟进;再没回复 → 放弃但入库。

### 阶段 4:PDF 解析 & 画像 — `src/resume_parser.py` + `src/profiler.py`

- 职责:下载 PDF → PyMuPDF 抽文本 → LLM 生成结构化画像。
- 练的 Agent 能力:**结构化输出约束**(用 JSON Schema / function calling 强制 LLM 输出可解析的结构化数据)。这是 Agent 工程的高频痛点。

### 阶段 5:评分 & 入库 — `src/scorer.py` + `src/obsidian_sync.py`

- 职责:多维加权评分 → 写 SQLite → 同步 Obsidian Markdown 笔记。
- 练的 Agent 能力:**自评输出质量**(画像生成后,Agent 对自己产出的画像打分 + 给理由)。同时留口子,未来可把"录用/拒绝结果"回灌来调整权重(轻量自我演进)。

### 阶段 6:自动对话 & 约面试 — `src/followuper.py`

- 职责:对高分候选人主动深度沟通、约面。
- 练的 Agent 能力:**长程多轮对话**(状态跨轮次保持:记得对方问过什么、承诺过什么时间)。

---

## 4. 数据模型(SQLite)

简表(详见 `src/db.py`):

- `candidates`:候选人主表(Boss ID、画像 JSON、评分、状态)。
- `interactions`:每一次互动(打招呼 / 回复 / 跟进,带时间戳与原始内容)。**完整审计链。**
- `resumes`:简历文件路径 + 解析状态。
- `faq`:FAQ 库(可被 reply_agent 检索,可自我增长)。
- `daily_quota`:每日打招呼计数(防超额)。

状态机(候选人 status):
`new → greeted → replied → resume_received → scored → (interview_scheduled | rejected | talent_pool)`

---

## 5. 反风控策略(全自动能活下来的关键)

| 维度 | 做法 |
|------|------|
| 额度 | 80/天,不贴 150 上限 |
| 时段 | 分散到 3 个 greet_window,不一次跑完 |
| 间隔 | 对数正态分布,8% 概率长停顿 |
| 浏览 | 25% 概率插入无意义干扰动作 |
| 招呼语 | LLM 逐个生成,无模板复用 |
| 刹车 | 检测到验证码/按钮异常/账号提示 → 立即停手 + 通知人,**绝不硬刚** |

刹车机制在 `src/safety.py`,所有浏览器操作经过它。

---

## 6. 目录结构

```
recruitment_agent/
├── config.yaml              # 你日常主编辑这个
├── .env.example             # API key 模板
├── requirements.txt
├── README.md                # 怎么装、怎么跑
├── docs/DESIGN.md           # 本文件
├── data/                    # 运行时数据(db/简历/画像/日志)
├── src/
│   ├── config.py            # 读 config.yaml + .env
│   ├── db.py                # SQLite 表与访问层
│   ├── llm_client.py        # DeepSeek 封装(含 function calling)
│   ├── browser_session.py   # 阶段1: 登录态与浏览器操作
│   ├── safety.py            # 反风控 + 刹车
│   ├── humanize.py          # 拟人化时序(对数正态间隔/干扰动作)
│   ├── screener.py          # 阶段2: 筛选 + 评估
│   ├── greeter.py           # 阶段2: 打招呼 + 配额
│   ├── watcher.py           # 阶段3: 巡检
│   ├── reply_agent.py       # 阶段3: ReAct 回复
│   ├── faq.py               # FAQ 检索与增长
│   ├── resume_parser.py     # 阶段4: PDF→文本
│   ├── profiler.py          # 阶段4: LLM 画像
│   ├── scorer.py            # 阶段5: 多维评分
│   ├── obsidian_sync.py     # 阶段5: 写 Obsidian
│   ├── followuper.py        # 阶段6: 高分跟进 + 约面
│   ├── scheduler.py         # 主调度(APScheduler)
│   └── cli.py               # 命令行入口
└── tools/
    └── boss_tools.py        # 供 LLM function calling 的工具定义
```

---

## 7. 关于"练 Agent 能力"的阅读路线

建议按这个顺序读代码,每一站对应一层能力:

1. `llm_client.py` + `tools/boss_tools.py` → **Tool Use**(让 LLM 调函数)
2. `reply_agent.py` → **ReAct 多步决策**(最练手)
3. `browser_session.py` + `safety.py` → **异常自适应**
4. `screener.py` + `greeter.py` → **配额与优先级调度**
5. `profiler.py` + `scorer.py` → **结构化输出 + 自评**
6. `faq.py` → **长期记忆 / 自我演进雏形**

每读一个模块,回看本文件第 3 节对应段落,你就知道在练什么。
