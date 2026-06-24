# LangGraph Workflows

## 范围

Phase 8 提供三个可追踪工作流：

- `chat_resume`: 沟通页简历处理。
- `recommend_talent`: 推荐牛人筛选和触达草稿。
- `daily_recommendation`: 每日候选人推荐和约面草稿。

工作流负责状态编排、人工确认和恢复，不负责绕过平台限制，也不直接发送 BOSS 消息。

## Checkpoint

每执行一个 LangGraph 节点，系统都会更新 `workflow_runs`：

- `status`: `running`、`waiting_review`、`completed`、`rejected` 或 `failed`。
- `current_node`: 当前或下一个节点。
- `state_json`: 候选人、岗位、动作、业务参数和完整节点历史。
- `error_message`: 失败原因。

节点按单步方式推进并立即提交 PostgreSQL。因此服务或电脑重启后，状态不会依赖进程内存。

## 人工确认

三个流程在 `human_review` 节点暂停：

```text
running -> waiting_review -> approved -> completed
                         -> rejected -> rejected
```

当工作流关联 `action_queue` 草稿时：

- 批准会将草稿状态更新为 `approved`。
- 拒绝会将草稿状态更新为 `rejected`。
- 两种操作都不会执行平台页面发送。

重复审核会返回冲突，避免同一动作被重复推进。

自动创建流程使用业务幂等键：同一份简历、同一条触达草稿、同一天同一岗位只创建一个工作流。

## 失败恢复

节点异常时：

- 工作流进入 `failed`。
- 当前节点和已完成历史保留。
- 异常写入 `error_message` 和审计日志。
- `POST /api/workflows/{id}/retry` 从当前节点重新执行。

只有失败状态可重试，防止已完成流程被重复执行。

## 自动接入

以下业务成功后自动创建工作流：

- PDF 简历解析完成后创建 `chat_resume`。
- 推荐牛人草稿创建后为每条草稿创建 `recommend_talent`。
- 每日推荐生成后按岗位创建 `daily_recommendation`。

工作流创建异常会写入审计日志，但不会回滚已经成功的简历解析、草稿或推荐结果。

## API

- `GET /api/workflows`
- `GET /api/workflows/{id}`
- `POST /api/workflows`
- `POST /api/workflows/{id}/review`
- `POST /api/workflows/{id}/retry`

## 前端

“工作流”页面提供：

- 三类流程手工启动。
- 运行状态和当前节点。
- 最新流程节点轨迹。
- 人工批准、拒绝。
- 失败任务重试。
