# 02 Business Architecture

## 业务对象

核心对象：

- Job: 招聘岗位。
- Candidate: 候选人。
- Conversation: 与候选人的沟通记录。
- Resume: 候选人简历。
- CandidateProfile: LLM 生成的候选人画像。
- Score: 岗位匹配评分。
- Recommendation: 每日推荐结果。
- Action: 待执行或已执行动作。
- AuditLog: 自动化审计记录。

## 候选人生命周期

建议状态机：

```text
discovered
  -> greet_pending
  -> greeted
  -> replied
  -> resume_requested
  -> resume_permission_pending
  -> resume_received
  -> resume_parsed
  -> scored
  -> recommended
  -> interview_invite_pending
  -> interview_invited
```

异常和终态：

```text
human_required
rejected
talent_pool
duplicate
automation_failed
```

## 沟通页 Agent 工作流

```text
Start
  -> OpenChatPage
  -> ReadConversationList
  -> ForEachConversation
  -> OpenConversation
  -> ExtractCandidateHeader
  -> ExtractMessages
  -> DetectResumeStatus
  -> If NoResume: GenerateResumeRequest
  -> If ResumePermission: AcceptResumeAttachment
  -> If ResumeAttachment: PreviewOrDownloadResume
  -> ParseResume
  -> BuildCandidateProfile
  -> ScoreCandidate
  -> SaveCandidate
  -> DecideNextAction
  -> End
```

关键业务规则：

1. 同一个候选人只处理一次最新状态，避免重复发送。
2. 如果候选人已明确拒绝，进入 `rejected` 或 `talent_pool`。
3. 如果出现薪资谈判、加微信、合同承诺等敏感内容，进入 `human_required`。
4. 如果简历解析失败，保留原文件和截图，进入待人工复核。

## 推荐牛人 Agent 工作流

```text
Start
  -> OpenRecommendPage
  -> SelectJob
  -> ApplyFilters
  -> ReadTalentCards
  -> Deduplicate
  -> PreScoreByCard
  -> CheckDailyQuota
  -> GenerateGreeting
  -> QueueOrSendGreeting
  -> SaveInteraction
  -> End
```

关键业务规则：

1. 默认每日主动触达上限为 50。
2. 同一候选人、同一岗位不重复打招呼。
3. 打招呼目标是索要简历，不做复杂承诺。
4. 每小时设置子额度，避免集中发送。
5. 未命中岗位硬性要求的候选人不进入发送队列。

## 每日推荐 Agent 工作流

```text
Start
  -> LoadActiveJobs
  -> LoadScoredCandidates
  -> RankCandidates
  -> GenerateRecommendationReasons
  -> GenerateInterviewInviteDrafts
  -> SaveDailyReport
  -> NotifyUser
  -> End
```

推荐维度：

- 技能匹配
- 学历和学校
- 专业相关性
- 项目经历质量
- 实习/工作经历
- 沟通积极度
- 简历完整度
- 岗位意向匹配
- 风险点数量和严重程度

## 人工确认节点

必须人工确认：

- 约面试
- 薪资讨论
- 加微信/电话
- 拒绝候选人
- 候选人提出特殊条件
- LLM 置信度低于阈值
- 页面自动化异常后恢复

可配置为自动：

- 同意接收附件简历
- 解析已收到简历
- 为未发简历候选人生成索要简历草稿
- 低频发送索要简历消息

