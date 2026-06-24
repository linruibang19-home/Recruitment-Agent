# Daily Recommendations and Interview Drafts

## 流程

```text
读取启用岗位
  -> 加载岗位下已评分候选人
  -> 按总分降序取 Top N
  -> 组合推荐理由、亮点和风险
  -> 保存当日推荐
  -> 高分候选人生成约面草稿
  -> 草稿进入待确认队列
  -> 人工通过或拒绝
```

## 推荐规则

- 默认每个岗位 Top 5。
- 排序使用候选人对该岗位的最新总分。
- 推荐理由包含总分、画像亮点、风险和评分理由。
- 同一岗位、候选人、日期只保留一条推荐。
- 重复生成会替换当日排名，不会重复创建同日约面草稿。

配置：

```text
RECOMMENDATION_TOP_N=5
INTERVIEW_INVITE_SCORE_THRESHOLD=70
RECOMMENDATION_HOUR=9
```

## 约面草稿

达到阈值的候选人会创建：

```text
action_type=interview_invite
status=pending
risk_level=high
```

草稿必须人工确认：

- `approve` 仅更新为 `approved`，不会发送。
- `reject` 更新为 `rejected`，同日重新生成推荐时不会重新创建。
- 真正发送功能仍未开放。

## 定时任务

APScheduler 每天按 `Asia/Shanghai` 时区运行，默认 09:00。

定时任务和手动生成使用同一个幂等服务。执行结果写入 `audit_logs`。

## API

- `GET /api/recommendations/today`
- `POST /api/recommendations/generate`
- `GET /api/actions`
- `POST /api/actions/{id}/approve`
- `POST /api/actions/{id}/reject`
