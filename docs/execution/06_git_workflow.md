# 06 Git Workflow

## 远程仓库

远程仓库：

```text
https://github.com/linruibang19-home/Recruitment-Agent.git
```

主分支：

```text
main
```

## 本地仓库初始化策略

当前本地目录最初不是 Git 仓库。初始化后应：

1. `git init`
2. `git remote add origin https://github.com/linruibang19-home/Recruitment-Agent.git`
3. `git fetch origin main`
4. 基于远程 `main` 建立本地 `main`
5. 添加当前项目文件
6. 提交 Phase 0 文档基线
7. 推送到远程

如果远程只有初始化 README，本地可以在同步远程历史后把当前项目作为后续提交加入。

## 提交规范

提交信息使用简短英文前缀：

```text
docs: add execution planning docs
chore: initialize project structure
feat: add postgres models
feat: add chat page scanner
fix: handle resume parsing failure
refactor: migrate workflow to langgraph
test: add scoring service tests
```

## 阶段提交要求

每个 Phase 完成后必须：

1. 检查 `git status`。
2. 确认没有 `.env`、数据库、简历、截图、缓存文件。
3. 运行该阶段可用的验证命令。
4. 提交。
5. 推送。
6. 在最终回复中说明提交 hash 和推送状态。

## 分支策略

MVP 阶段可以直接使用 `main`，但每个阶段提交必须清晰。

当项目进入多人协作或 PR 流程后，使用阶段分支：

```text
phase-1-architecture
phase-2-postgres
phase-3-dashboard
phase-4-chat-scanner
```

## 禁止提交

禁止提交：

- `.env`
- 数据库文件
- 简历文件
- 截图
- 浏览器 profile
- `__pycache__`
- `.venv`
- 日志文件

