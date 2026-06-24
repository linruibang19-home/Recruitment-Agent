# Recommended Talent Outreach Drafts

## 安全边界

Phase 7 仅实现：

- 打开并读取 BOSS 推荐牛人页面。
- 本地筛选和去重。
- 候选人入库。
- 生成索要 PDF 简历的打招呼草稿。
- 每日额度预留。
- 人工通过或拒绝。

不实现：

- 自动点击“打招呼”。
- 自动填写或发送消息。
- 绕过验证码、平台限制或账号异常提示。
- 通过随机动作规避平台检测。

## 流程

```text
手工登录 BOSS
  -> 打开推荐牛人页
  -> 读取卡片
  -> 本地条件筛选
  -> BOSS UID 去重
  -> 保存候选人
  -> 检查每日额度
  -> 生成索要简历草稿
  -> 进入待确认队列
```

## 筛选字段

- 岗位
- 城市
- 学历
- 经验
- 求职意向
- 薪资关键词
- 岗位关键词

筛选对已读取卡片在本地执行，避免依赖平台筛选弹窗的易变 DOM。

## 去重

优先使用推荐卡片链接中的 BOSS UID。无法取得 UID 时，使用卡片文本摘要生成稳定指纹。

同一候选人和岗位只保留一条 `request_resume_greeting` 动作。

## 额度

```text
MAX_DAILY_GREETINGS=50
MAX_HOURLY_GREETINGS=10
```

额度组成：

- `used_count`: 真实发送成功数量。当前阶段始终为 0。
- `pending_count`: 待确认草稿。
- `approved_count`: 已通过但未发送草稿。
- `available_count`: 每日上限减去以上占用。

草稿达到每日上限后不再创建新草稿。

## API

- `GET /api/quota/greetings`
- `POST /api/automation/recommend/scan`
- `GET /api/actions`
- `POST /api/actions/{id}/approve`
- `POST /api/actions/{id}/reject`
