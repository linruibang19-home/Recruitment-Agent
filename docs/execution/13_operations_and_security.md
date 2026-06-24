# Operations And Security

## 一键运行

在项目根目录执行：

```powershell
.\scripts\start.ps1
```

脚本会：

- 检查 8000 和 5173 端口。
- 后台启动 FastAPI 和 Vite。
- 将日志写入 `data/logs`。
- 将进程信息写入 `data/runtime/services.json`。

查看状态：

```powershell
.\scripts\status.ps1
```

停止服务：

```powershell
.\scripts\stop.ps1
```

停止脚本按 PID 文件关闭前后端进程树，不会按进程名批量结束其他程序。

## 故障恢复

1. 执行 `scripts/status.ps1` 检查进程和端口。
2. 查看 `data/logs/backend.err.log` 和 `frontend.err.log`。
3. 执行 `scripts/stop.ps1`。
4. 确认 PostgreSQL 服务运行。
5. 执行 `scripts/start.ps1`。
6. 检查 `/api/health/database` 和 `/api/health/automation`。

浏览器出现验证码、登录失效、账号异常或连续失败时，系统停止扫描。必须人工处理页面后停止并重新启动浏览器会话。

## 数据脱敏

写入审计日志前自动处理：

- 手机号
- 邮箱
- 身份证号
- 微信号
- 本地绝对路径

项目内截图路径保存为 `data/screenshots/...` 相对路径。聊天候选人姓名和原始简历文件名不写入审计详情。

发送到外部 LLM 的简历文本复用同一脱敏策略。`LLM_ENABLED=false` 时不会调用外部模型。

## 候选人删除

API：

```text
DELETE /api/candidates/{id}?confirm=true
```

删除范围：

- 候选人基础资料
- 简历数据库记录和受控目录内文件
- 候选人画像
- 岗位评分
- 推荐记录
- 沟通记录

动作队列保留审计状态，但候选人外键置空。删除动作本身写入审计日志。

## 自动化测试

安装测试依赖：

```powershell
cd backend
python -m pip install -r requirements-dev.txt
```

运行：

```powershell
python -m pytest -q
```

覆盖：

- 敏感信息脱敏
- 文件路径边界
- 推荐牛人筛选
- 招呼语边界
- 三类 LangGraph 人工暂停
- 审核后恢复
- 连续失败安全停机

## Chrome 插件

Codex Chrome 插件依赖两部分：

1. Codex 客户端中的 `chrome` 插件。
2. Chrome Profile 中启用的 Codex Chrome Extension 和本机通信组件。

如果插件无法连接：

1. 在 Codex 插件管理中卸载并重新安装 `chrome`。
2. 检查 [Codex Chrome Extension](https://chromewebstore.google.com/detail/codex/hehggadaopoacecdllhhajmbjkdcmajg) 已安装并启用。
3. 完全重启 Codex 客户端和 Chrome。
