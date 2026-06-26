# Recruitment Agent Execution Docs

本目录用于归档项目执行文档。后续需求变更、架构调整、阶段计划、风险控制、数据库设计、接口设计都优先沉淀到这里，再按文档执行代码重构。

## 文档索引

- [01_requirements.md](01_requirements.md): 产品需求、范围边界、关键业务流程。
- [02_business_architecture.md](02_business_architecture.md): 招聘业务架构、候选人生命周期、Agent 工作流。
- [03_technical_architecture.md](03_technical_architecture.md): 技术栈、系统模块、服务边界、数据流。
- [04_delivery_plan.md](04_delivery_plan.md): 阶段计划、交付物、验收标准、执行顺序。
- [05_risk_control.md](05_risk_control.md): 平台风控、隐私合规、自动化边界、审计策略。
- [06_git_workflow.md](06_git_workflow.md): Git 管理、分支、提交、推送规范。
- [07_phase_status.md](07_phase_status.md): 阶段执行状态和自检记录。
- [08_database_setup.md](08_database_setup.md): PostgreSQL 初始化、迁移和连接检查。
- [09_resume_processing.md](09_resume_processing.md): PDF、OCR、画像、LLM 增强和岗位评分。
- [10_daily_recommendations.md](10_daily_recommendations.md): 每日 Top N、约面草稿和人工审核。
- [11_talent_outreach.md](11_talent_outreach.md): 推荐牛人读取、筛选、去重、草稿和额度。
- [12_langgraph_workflows.md](12_langgraph_workflows.md): LangGraph 状态机、checkpoint、人审恢复和运行查看器。
- [13_operations_and_security.md](13_operations_and_security.md): 本地启停、测试、数据删除、脱敏和故障恢复。
- [14_chrome_extension_bridge.md](14_chrome_extension_bridge.md): 普通 Chrome 扩展、任务桥接和真实数据入库。
- [15_ai_ocr_llm.md](15_ai_ocr_llm.md): OCR、LLM 健康检查、DeepSeek 配置和本地验证说明。

## 执行原则

1. 先文档后实现：每个阶段开始前明确目标、范围和验收标准。
2. 小步提交：完成一个可验证阶段后提交并推送。
3. 可观测优先：所有自动化动作都要有日志、截图或数据库记录。
4. 人工确认优先：涉及发消息、约面、薪资、拒绝等动作默认先进入待确认队列。
5. 合规自动化：限频、去重、异常停机，不做绕过验证码或平台限制的逻辑。
