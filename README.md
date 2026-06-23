# Boss 直聘招聘 Agent

一个后台常驻的招聘自动化 Agent:每日以拟人化节奏在 Boss 直聘上筛选候选人、个性化打招呼、监听回复、解析简历、生成画像与评分、自主跟进直到约上面试。

> 这套代码同时是**学习 Agent 开发**的练手项目。每个模块练哪种 Agent 能力,见 [`docs/DESIGN.md`](docs/DESIGN.md) 第 3 节。

## 快速开始

### 1. 装依赖

```bash
cd D:/Dev/Intership/HermesAgent-project/recruitment_agent
python -m venv .venv
.venv/Scripts/activate          # Windows bash
pip install -r requirements.txt
```

### 2. 配置

```bash
cp .env.example .env
# 编辑 .env,填入 DEEPSEEK_API_KEY
```

主配置在 [`config.yaml`](config.yaml):筛选条件、额度(默认 80/天)、招呼时段、评分权重、Obsidian vault 路径。日常你主要改这一个文件。

### 3. 初始化数据库

```bash
cd src
python -c "import db; print('db ok')"
```

### 4. 运行

```bash
# 在 src/ 目录下:
python cli.py run          # 启动常驻调度器(推荐)
python cli.py daily        # 只跑一次每日打招呼
python cli.py watch        # 只跑一次巡检
python cli.py top 10       # 看评分 Top 10
python cli.py show <boss_id>
python cli.py faq add "公司多少人" "我们 200 人左右,AI 方向"
```

> ⚠️ **首次运行需要扫码登录 Boss**。建议在 `.env` 配 `CHROME_USER_DATA_DIR` 指向你常用的 Chrome profile,以保持登录态。

## 目录结构

见 [`docs/DESIGN.md`](docs/DESIGN.md) 第 6 节。

## 还需要对接的部分(标 `TODO(对接Boss)`)

骨架已完整,但以下几处需要用真实 Boss 页面调试后填实现:

- `browser_session.read_current_card()`:解析候选人卡片 DOM
- `browser_session.send_message()`:定位输入框并发送
- `screener._fetch_candidate_cards()`:打开搜索页抓卡片列表
- `watcher._fetch_new_messages()`:从消息页抓新回复

这些是 browser-use 对接真实页面必经的调试环节,无法凭空写死(页面结构会变)。

## 封号风险须知

全自动打招呼有账号被封风险。本项目用 80/天上限 + 拟人化时序 + 风控刹车来降低风险,但**不保证不被封**。建议先用小号/测试账号验证一周,再上主力账号。详见 `docs/DESIGN.md` 第 5 节。
