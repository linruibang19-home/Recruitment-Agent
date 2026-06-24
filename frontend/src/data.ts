import type { ActionItem, Candidate, Metric, PipelineStage, RunEvent } from "./types";

export const metrics: Metric[] = [
  { label: "今日待处理", value: "28", detail: "沟通页会话" },
  { label: "主动触达额度", value: "0 / 50", detail: "今日已使用" },
  { label: "已解析简历", value: "14", detail: "本周新增" },
  { label: "高分候选人", value: "6", detail: "80 分以上" }
];

export const pipeline: PipelineStage[] = [
  { label: "已发现", count: 42 },
  { label: "待简历", count: 18 },
  { label: "已解析", count: 14 },
  { label: "已评分", count: 12 },
  { label: "待约面", count: 4 }
];

export const candidates: Candidate[] = [
  {
    name: "傅俊溪",
    current_role: "Agent 应用开发实习生",
    education_level: "硕士",
    school: "湖南师范大学",
    status: "待约面",
    raw_card: { skills: ["Python", "RAG", "LangChain"] }
  },
  {
    name: "阮心一",
    current_role: "Agent 应用开发实习生",
    education_level: "本科",
    school: "软件工程",
    status: "待人工确认",
    raw_card: { skills: ["SpringBoot", "Python", "LLM"] }
  },
  {
    name: "吕添健",
    current_role: "后端开发实习生",
    education_level: "本科",
    school: "人工智能",
    status: "已评分",
    raw_card: { skills: ["Python", "FastAPI", "数据分析"] }
  }
];

export const actionQueue: ActionItem[] = [
  { title: "发送约面草稿", candidate: "傅俊溪", risk: "需确认", time: "10:30" },
  { title: "索要 PDF 简历", candidate: "颜锦鹏", risk: "低风险", time: "10:24" },
  { title: "复核 OCR 结果", candidate: "林女士", risk: "需确认", time: "昨天" }
];

export const runEvents: RunEvent[] = [
  { label: "浏览器会话", status: "ready", detail: "Playwright 只读扫描已接入" },
  { label: "PostgreSQL", status: "ready", detail: "数据层已连接" },
  { label: "LangGraph", status: "planned", detail: "Phase 8 接入工作流" }
];
