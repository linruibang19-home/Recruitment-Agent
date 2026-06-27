import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  Award,
  Bot,
  BriefcaseBusiness,
  CheckCircle2,
  ClipboardList,
  Database,
  Trash2,
  Eye,
  FileText,
  FileUp,
  LayoutDashboard,
  ListChecks,
  RefreshCw,
  Search,
  ScanLine,
  Settings,
  ShieldCheck,
  ThumbsDown,
  ThumbsUp,
  Users,
  Workflow
} from "lucide-react";
import {
  controlExtensionCommand,
  decideAction,
  deleteCandidate,
  fetchAuditLog,
  fetchAuditLogs,
  fetchCandidateDetail,
  fetchDashboardData,
  generateRecommendations,
  pauseChatLoop,
  queueExtensionCommand,
  startChatLoop,
  stopAllExtensionCommands,
  retryWorkflow,
  reviewWorkflow,
  uploadResume,
  type DashboardData
} from "./api";
import { candidates as fallbackCandidates, runEvents } from "./data";
import { WorkflowView } from "./WorkflowView";
import type {
  ActionQueueEntry,
  AuditLog,
  Candidate,
  CandidateDetail,
  CandidatePipelineItem,
  ExtensionCommand,
  GreetingQuota,
  Job,
  Metric,
  PageResponse,
  PipelineStage,
  Recommendation,
  TalentScanResult
} from "./types";

type ViewId =
  | "dashboard"
  | "jobs"
  | "candidates"
  | "talents"
  | "recommendations"
  | "actions"
  | "automation"
  | "workflows"
  | "audit"
  | "settings";

const navItems: Array<{ id: ViewId; label: string; icon: typeof LayoutDashboard }> = [
  { id: "dashboard", label: "工作台", icon: LayoutDashboard },
  { id: "jobs", label: "岗位管理", icon: BriefcaseBusiness },
  { id: "candidates", label: "候选人库", icon: Users },
  { id: "talents", label: "推荐牛人", icon: Search },
  { id: "recommendations", label: "每日推荐", icon: Award },
  { id: "actions", label: "待确认", icon: ListChecks },
  { id: "automation", label: "BOSS 流程", icon: Bot },
  { id: "workflows", label: "工作流", icon: Workflow },
  { id: "audit", label: "审计日志", icon: ClipboardList },
  { id: "settings", label: "系统设置", icon: Settings }
];

const databaseTables = [
  { name: "jobs", description: "岗位配置、关键词和岗位状态" },
  { name: "candidates", description: "候选人主档、来源和处理状态" },
  { name: "candidate_profiles", description: "简历解析后的候选人画像" },
  { name: "resumes", description: "简历文件路径、解析文本和处理状态" },
  { name: "scores", description: "候选人与岗位的匹配评分" },
  { name: "recommendations", description: "每日推荐结果和推荐理由" },
  { name: "action_queue", description: "待确认的消息、约面和人工动作" },
  { name: "interactions", description: "沟通记录和平台会话摘要" },
  { name: "extension_commands", description: "Chrome 扩展采集任务" },
  { name: "extension_sessions", description: "扩展连接和当前页面状态" },
  { name: "daily_quota", description: "每日主动触达额度统计" },
  { name: "audit_logs", description: "自动化执行审计日志" },
  { name: "workflow_runs", description: "LangGraph 工作流运行记录" },
  { name: "alembic_version", description: "数据库迁移版本号" }
];

const viewMeta: Record<ViewId, { title: string; description: string }> = {
  dashboard: { title: "招聘工作台", description: "查看岗位、候选人和自动化服务的当前状态。" },
  jobs: { title: "岗位管理", description: "维护招聘岗位及候选人匹配条件。" },
  candidates: { title: "候选人库", description: "查看已采集候选人的基础资料和处理进度。" },
  talents: { title: "推荐牛人", description: "读取推荐卡片并生成索要简历草稿。" },
  recommendations: { title: "每日推荐", description: "按岗位查看高匹配候选人和约面建议。" },
  actions: { title: "待确认", description: "审核消息发送、约面等需要人工确认的操作。" },
  automation: { title: "BOSS 候选人流程", description: "从未读沟通到索要简历、解析评分和推荐确认的流程队列。" },
  workflows: { title: "工作流", description: "跟踪 LangGraph 节点、人工确认和失败恢复。" },
  audit: { title: "审计日志", description: "查询浏览器会话和采集任务的执行记录。" },
  settings: { title: "系统设置", description: "管理本地运行状态、采集策略、数据目录和数据库结构。" }
};

const AUDIT_PAGE_SIZE = 12;

function candidateEducation(candidate: Candidate): string {
  const parts = [candidate.education_level, candidate.school].filter(Boolean);
  return parts.length ? parts.join(" / ") : "暂未采集";
}

function candidateSkills(candidate: Candidate): string {
  const skills = candidate.raw_card?.skills;
  if (Array.isArray(skills) && skills.length > 0) {
    return skills.map(String).join(" / ");
  }
  return candidate.major ?? "等待解析";
}

function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    discovered: "已发现",
    resume_requested: "待简历",
    resume_parsed: "已解析",
    scored: "已评分",
    interview_invite_pending: "待约面"
  };
  return labels[status] ?? status;
}

function sourceLabel(source?: string | null): string {
  const labels: Record<string, string> = {
    manual: "手动录入",
    boss_chat: "BOSS 沟通",
    boss_recommend: "推荐牛人",
    imported: "导入"
  };
  return source ? labels[source] ?? source : "手动录入";
}

function splitInput(value: string): string[] {
  return value
    .split(/[,，、]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function buildPipeline(candidates: Candidate[]): PipelineStage[] {
  const count = (status: string) => candidates.filter((candidate) => candidate.status === status).length;
  return [
    { label: "已发现", count: candidates.length },
    { label: "待简历", count: count("resume_requested") },
    { label: "已解析", count: count("resume_parsed") },
    { label: "已评分", count: count("scored") },
    { label: "待约面", count: count("interview_invite_pending") }
  ];
}

function buildMetrics(data: DashboardData | null, candidates: Candidate[]): Metric[] {
  return [
    { label: "候选人", value: String(data?.candidates.total ?? candidates.length), detail: "PostgreSQL 实时数据" },
    { label: "岗位", value: String(data?.jobs.total ?? 0), detail: "已配置岗位" },
    {
      label: "主动触达额度",
      value: `${data?.greetingQuota.used_count ?? 0} / ${data?.greetingQuota.max_count ?? 50}`,
      detail: `草稿占用 ${(
        (data?.greetingQuota.pending_count ?? 0) +
        (data?.greetingQuota.approved_count ?? 0)
      )}`
    },
    {
      label: "数据库",
      value: data?.databaseStatus === "ok" ? "正常" : "离线",
      detail: "health/database"
    }
  ];
}

function auditActionLabel(actionType: string): string {
  const labels: Record<string, string> = {
    browser_start: "启动浏览器",
    browser_login: "打开 BOSS 登录窗口",
    browser_stop: "停止浏览器",
    chat_scan: "扫描沟通列表",
    chat_open: "读取聊天详情",
    resume_process: "解析简历",
    candidate_score: "候选人评分",
    daily_recommendation: "生成每日推荐",
    daily_recommendation_schedule: "定时每日推荐",
    action_approved: "通过待确认动作",
    action_rejected: "拒绝待确认动作",
    talent_scan: "扫描推荐牛人",
    candidate_deleted: "删除候选人数据",
    extension_chat_ingest: "扩展写入聊天",
    extension_talent_ingest: "扩展写入牛人",
    extension_command: "扩展任务失败",
    extension_resume_request_quota: "索要简历额度",
    chat_resume_loop: "沟通自动循环"
  };
  return labels[actionType] ?? actionType;
}

const pipelineStageLabels: Array<{
  key: "discovered" | "resume_requested" | "resume_received" | "parsed" | "scored" | "pending_review";
  label: string;
}> = [
  { key: "discovered", label: "已发现" },
  { key: "resume_requested", label: "已索要" },
  { key: "resume_received", label: "已收简历" },
  { key: "parsed", label: "已解析" },
  { key: "scored", label: "已评分" },
  { key: "pending_review", label: "待确认" }
];

function PipelineQueue({ items }: { items: CandidatePipelineItem[] }) {
  if (!items.length) {
    return <div className="empty-state">暂无候选人流程记录。先在 BOSS 沟通页执行扫描或读取。</div>;
  }
  return (
    <div className="pipeline-queue">
      {items.slice(0, 18).map((item) => (
        <article className={`pipeline-card stage-${item.stage}`} key={item.candidate_id}>
          <div className="pipeline-card-main">
            <span className="pipeline-stage">{item.stage_label}</span>
            <h3>{item.name ?? `候选人 #${item.candidate_id}`}</h3>
            <p>{item.next_action}</p>
          </div>
          <dl className="pipeline-card-meta">
            <div>
              <dt>消息</dt>
              <dd>{item.message_count}</dd>
            </div>
            <div>
              <dt>简历</dt>
              <dd>{item.resume_count}</dd>
            </div>
            <div>
              <dt>评分</dt>
              <dd>{item.best_score != null ? Math.round(item.best_score) : "-"}</dd>
            </div>
            <div>
              <dt>待确认</dt>
              <dd>{item.pending_action_count}</dd>
            </div>
          </dl>
          <time>{new Date(item.updated_at).toLocaleString("zh-CN")}</time>
        </article>
      ))}
    </div>
  );
}

const agentChain = ["沟通采集", "简历解析", "匹配评分", "推荐决策", "审计恢复"];

const EXTENSION_COMMAND_PAGE_SIZE = 5;

function extensionCommandLabel(commandType: ExtensionCommand["command_type"]): string {
  const labels: Record<ExtensionCommand["command_type"], string> = {
    scan_chats: "扫描沟通列表",
    scan_chat_details: "批量读取聊天",
    request_resumes_batch: "批量索要简历",
    read_current_chat: "读取当前聊天",
    scan_talents: "扫描推荐牛人"
  };
  return labels[commandType];
}

function ExtensionCommandDetails({ command }: { command: ExtensionCommand | null }) {
  if (!command) {
    return (
      <aside className="execution-detail-panel empty-detail">
        <ClipboardList size={22} />
        <p>点击左侧执行记录查看 payload、执行结果、错误信息和时间线。</p>
      </aside>
    );
  }

  return (
    <aside className="execution-detail-panel">
      <div className="execution-detail-header">
        <span className={command.status === "completed" ? "status-pill active" : "status-pill danger"}>
          {command.status}
        </span>
        <h3>#{command.id} {extensionCommandLabel(command.command_type)}</h3>
        <time>{new Date(command.created_at).toLocaleString("zh-CN")}</time>
      </div>
      <dl className="audit-detail-list">
        <div>
          <dt>创建时间</dt>
          <dd>{new Date(command.created_at).toLocaleString("zh-CN")}</dd>
        </div>
        <div>
          <dt>领取时间</dt>
          <dd>{command.claimed_at ? new Date(command.claimed_at).toLocaleString("zh-CN") : "未领取"}</dd>
        </div>
        <div>
          <dt>完成时间</dt>
          <dd>{command.completed_at ? new Date(command.completed_at).toLocaleString("zh-CN") : "未完成"}</dd>
        </div>
        <div>
          <dt>错误信息</dt>
          <dd>{command.error_message ?? "无"}</dd>
        </div>
      </dl>
      <div className="execution-json-grid">
        <div>
          <strong>任务参数</strong>
          <pre className="payload-view">{JSON.stringify(command.payload ?? {}, null, 2)}</pre>
        </div>
        <div>
          <strong>执行结果</strong>
          <pre className="payload-view">{JSON.stringify(command.result ?? {}, null, 2)}</pre>
        </div>
      </div>
    </aside>
  );
}

function CandidateTable({
  candidates,
  onSelect
}: {
  candidates: Candidate[];
  onSelect?: (candidate: Candidate) => void;
}) {
  return (
    <div className="candidate-table">
      <div className={onSelect ? "table-head candidate-action-head" : "table-head"}>
        <span>候选人</span>
        <span>学历/学校</span>
        <span>技能/专业</span>
        <span>来源</span>
        <span>状态</span>
        {onSelect && <span>操作</span>}
      </div>
      {candidates.map((candidate, index) => (
        <div
          className={onSelect ? "table-row candidate-action-row" : "table-row"}
          key={candidate.id ?? `${candidate.name}-${index}`}
        >
          <strong>{candidate.name ?? "未命名"}</strong>
          <span>{candidateEducation(candidate)}</span>
          <span className="skill-list">{candidateSkills(candidate)}</span>
          <span>{sourceLabel(candidate.source)}</span>
          <span>{statusLabel(candidate.status)}</span>
          {onSelect && (
            <button
              className="table-action"
              disabled={!candidate.id}
              onClick={() => onSelect(candidate)}
              type="button"
            >
              <Eye size={15} />
              <span>查看</span>
            </button>
          )}
        </div>
      ))}
    </div>
  );
}

function JobsTable({ jobs }: { jobs: Job[] }) {
  if (!jobs.length) {
    return <div className="empty-state">暂未配置岗位。</div>;
  }

  return (
    <div className="candidate-table">
      <div className="table-head jobs-head">
        <span>岗位</span>
        <span>城市</span>
        <span>关键词</span>
        <span>状态</span>
      </div>
      {jobs.map((job) => (
        <div className="table-row jobs-row" key={job.id}>
          <strong>{job.title}</strong>
          <span>{job.city ?? "不限"}</span>
          <span className="skill-list">{job.keywords.length ? job.keywords.join(" / ") : "未配置"}</span>
          <span>{job.is_active ? "启用" : "停用"}</span>
        </div>
      ))}
    </div>
  );
}

export function App() {
  const [activeView, setActiveView] = useState<ViewId>("dashboard");
  const [data, setData] = useState<DashboardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [automationBusy, setAutomationBusy] = useState<string | null>(null);
  const [automationNotice, setAutomationNotice] = useState<string | null>(null);
  const [candidateDetail, setCandidateDetail] = useState<CandidateDetail | null>(null);
  const [candidateDetailLoading, setCandidateDetailLoading] = useState(false);
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [selectedJobId, setSelectedJobId] = useState<number | null>(null);
  const [resumeBusy, setResumeBusy] = useState(false);
  const [candidateDeleteBusy, setCandidateDeleteBusy] = useState(false);
  const [resumeNotice, setResumeNotice] = useState<string | null>(null);
  const [recommendationJobId, setRecommendationJobId] = useState<number | null>(null);
  const [recommendationBusy, setRecommendationBusy] = useState(false);
  const [recommendationNotice, setRecommendationNotice] = useState<string | null>(null);
  const [actionBusyId, setActionBusyId] = useState<number | null>(null);
  const [actionNotice, setActionNotice] = useState<string | null>(null);
  const [talentJobId, setTalentJobId] = useState<number | null>(null);
  const [talentCity, setTalentCity] = useState("广州");
  const [talentEducation, setTalentEducation] = useState("本科");
  const [talentExperience, setTalentExperience] = useState("在校/应届");
  const [talentIntention, setTalentIntention] = useState("");
  const [talentSalary, setTalentSalary] = useState("");
  const [talentKeywords, setTalentKeywords] = useState("");
  const [talentBusy, setTalentBusy] = useState(false);
  const [talentNotice, setTalentNotice] = useState<string | null>(null);
  const [talentResult, setTalentResult] = useState<TalentScanResult | null>(null);
  const [workflowBusy, setWorkflowBusy] = useState<string | null>(null);
  const [workflowNotice, setWorkflowNotice] = useState<string | null>(null);
  const [chatLoopBusy, setChatLoopBusy] = useState<"start" | "pause" | null>(null);
  const [auditPage, setAuditPage] = useState(0);
  const [auditStatus, setAuditStatus] = useState("all");
  const [auditLogs, setAuditLogs] = useState<PageResponse<AuditLog> | null>(null);
  const [auditLoading, setAuditLoading] = useState(false);
  const [auditNotice, setAuditNotice] = useState<string | null>(null);
  const [selectedAuditLog, setSelectedAuditLog] = useState<AuditLog | null>(null);
  const [extensionCommandPage, setExtensionCommandPage] = useState(0);
  const [selectedExtensionCommandId, setSelectedExtensionCommandId] = useState<number | null>(null);

  const loadDashboard = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      setData(await fetchDashboardData());
    } catch (err) {
      setError(err instanceof Error ? err.message : "无法连接后端 API");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  const loadAuditLogs = useCallback(async () => {
    setAuditLoading(true);
    setAuditNotice(null);
    try {
      const page = await fetchAuditLogs(AUDIT_PAGE_SIZE, auditPage * AUDIT_PAGE_SIZE, auditStatus);
      setAuditLogs(page);
      setSelectedAuditLog((current) => (
        current && !page.items.some((item) => item.id === current.id) ? null : current
      ));
    } catch (err) {
      setAuditNotice(err instanceof Error ? err.message : "无法读取审计日志");
    } finally {
      setAuditLoading(false);
    }
  }, [auditPage, auditStatus]);

  useEffect(() => {
    if (activeView === "audit") {
      void loadAuditLogs();
    }
  }, [activeView, loadAuditLogs]);

  useEffect(() => {
    if (!selectedJobId && data?.jobs.items[0]) {
      setSelectedJobId(data.jobs.items[0].id);
    }
    if (!recommendationJobId && data?.jobs.items[0]) {
      setRecommendationJobId(data.jobs.items[0].id);
    }
    if (!talentJobId && data?.jobs.items[0]) {
      setTalentJobId(data.jobs.items[0].id);
      setTalentKeywords(data.jobs.items[0].keywords.join(", "));
    }
  }, [data?.jobs.items, recommendationJobId, selectedJobId, talentJobId]);

  const selectCandidate = useCallback(async (candidate: Candidate) => {
    if (!candidate.id) {
      return;
    }
    setCandidateDetailLoading(true);
    setResumeNotice(null);
    try {
      setCandidateDetail(await fetchCandidateDetail(candidate.id));
    } catch (err) {
      setResumeNotice(err instanceof Error ? err.message : "无法读取候选人详情");
    } finally {
      setCandidateDetailLoading(false);
    }
  }, []);

  const processResume = useCallback(async () => {
    const candidateId = candidateDetail?.candidate.id;
    if (!candidateId || !resumeFile) {
      setResumeNotice("请选择 PDF 简历");
      return;
    }
    setResumeBusy(true);
    setResumeNotice(null);
    try {
      const result = await uploadResume(candidateId, resumeFile, selectedJobId ?? undefined);
      setCandidateDetail(await fetchCandidateDetail(candidateId));
      setResumeFile(null);
      setResumeNotice(
        `解析完成：识别 ${result.profile.skills.length} 项技能${
          result.score ? `，岗位匹配 ${Number(result.score.total_score).toFixed(0)} 分` : ""
        }。`
      );
      await loadDashboard();
    } catch (err) {
      setResumeNotice(err instanceof Error ? err.message : "简历处理失败");
    } finally {
      setResumeBusy(false);
    }
  }, [candidateDetail?.candidate.id, loadDashboard, resumeFile, selectedJobId]);

  const removeCandidate = useCallback(async () => {
    const candidateId = candidateDetail?.candidate.id;
    if (!candidateId) {
      return;
    }
    const candidateName = candidateDetail.candidate.name ?? `候选人 #${candidateId}`;
    if (!window.confirm(`确认永久删除“${candidateName}”及其简历、画像、评分和沟通记录吗？`)) {
      return;
    }
    setCandidateDeleteBusy(true);
    setResumeNotice(null);
    try {
      const result = await deleteCandidate(candidateId);
      setCandidateDetail(null);
      setResumeFile(null);
      await loadDashboard();
      setResumeNotice(`候选人数据已删除，同时清理 ${result.deleted_resume_files} 个本地简历文件。`);
    } catch (err) {
      setResumeNotice(err instanceof Error ? err.message : "候选人删除失败");
    } finally {
      setCandidateDeleteBusy(false);
    }
  }, [candidateDetail, loadDashboard]);

  const runRecommendations = useCallback(async () => {
    setRecommendationBusy(true);
    setRecommendationNotice(null);
    try {
      const result = await generateRecommendations(recommendationJobId ?? undefined);
      await loadDashboard();
      setRecommendationNotice(
        `已生成 ${result.recommendations_created} 条推荐，新增 ${result.drafts_created} 条约面草稿。`
      );
    } catch (err) {
      setRecommendationNotice(err instanceof Error ? err.message : "生成推荐失败");
    } finally {
      setRecommendationBusy(false);
    }
  }, [loadDashboard, recommendationJobId]);

  const reviewAction = useCallback(async (
    actionId: number,
    decision: "approve" | "reject"
  ) => {
    setActionBusyId(actionId);
    setActionNotice(null);
    try {
      await decideAction(actionId, decision);
      await loadDashboard();
      setActionNotice(decision === "approve" ? "草稿已通过，仍未发送。" : "草稿已拒绝。");
    } catch (err) {
      setActionNotice(err instanceof Error ? err.message : "审核失败");
    } finally {
      setActionBusyId(null);
    }
  }, [loadDashboard]);

  const runTalentScan = useCallback(async () => {
    if (!talentJobId) {
      setTalentNotice("请选择岗位");
      return;
    }
    setTalentBusy(true);
    setTalentNotice(null);
    try {
      const command = await queueExtensionCommand("scan_talents", {
        job_id: talentJobId,
        city: talentCity.trim() || undefined,
        experience: splitInput(talentExperience),
        education: splitInput(talentEducation),
        intentions: splitInput(talentIntention),
        salary_keywords: splitInput(talentSalary),
        required_keywords: splitInput(talentKeywords),
        limit: 30,
        capture_screenshot: false
      });
      setTalentResult(null);
      await loadDashboard();
      setTalentNotice(`扫描任务 #${command.id} 已提交，请保持“推荐牛人”页面位于当前标签页。`);
    } catch (err) {
      setTalentNotice(err instanceof Error ? err.message : "推荐牛人扫描失败");
    } finally {
      setTalentBusy(false);
    }
  }, [
    loadDashboard,
    talentCity,
    talentEducation,
    talentExperience,
    talentIntention,
    talentJobId,
    talentKeywords,
    talentSalary
  ]);

  const decideWorkflow = useCallback(async (
    runId: number,
    decision: "approved" | "rejected"
  ) => {
    setWorkflowBusy(`review:${runId}`);
    setWorkflowNotice(null);
    try {
      const run = await reviewWorkflow(runId, decision);
      await loadDashboard();
      setWorkflowNotice(
        decision === "approved"
          ? `工作流 #${run.id} 已批准并继续，未执行平台发送。`
          : `工作流 #${run.id} 已拒绝并结束。`
      );
    } catch (err) {
      setWorkflowNotice(err instanceof Error ? err.message : "工作流审核失败");
    } finally {
      setWorkflowBusy(null);
    }
  }, [loadDashboard]);

  const rerunWorkflow = useCallback(async (runId: number) => {
    setWorkflowBusy(`retry:${runId}`);
    setWorkflowNotice(null);
    try {
      await retryWorkflow(runId);
      await loadDashboard();
      setWorkflowNotice(`工作流 #${runId} 已从失败节点恢复。`);
    } catch (err) {
      setWorkflowNotice(err instanceof Error ? err.message : "工作流重试失败");
    } finally {
      setWorkflowBusy(null);
    }
  }, [loadDashboard]);

  const runAutomationAction = useCallback(
    async (
      action:
        | "refresh"
        | "scan_chats"
        | "scan_chat_details"
        | "request_resumes_batch"
        | "read_current_chat"
    ) => {
      setAutomationBusy(action);
      setAutomationNotice(null);
      try {
        if (action === "refresh") {
          await loadDashboard();
          setAutomationNotice("已重新检测扩展连接状态。");
        } else {
          const command = await queueExtensionCommand(
            action,
            action === "request_resumes_batch"
              ? {
                  limit: 20,
                  delay_ms: 1800,
                  only_unread: true,
                  message: "方便发一份你的简历过来吗？"
                }
              : { limit: 30, delay_ms: 1400 }
          );
          setAutomationNotice(
            action === "scan_chats"
              ? `沟通列表扫描任务 #${command.id} 已提交。`
              : action === "scan_chat_details"
                ? `批量读取聊天任务 #${command.id} 已提交；扩展会逐个打开左侧会话并写入候选人库。`
                : action === "request_resumes_batch"
                  ? `批量索要简历任务 #${command.id} 已提交；本批最多处理 20 个未读会话，可暂停、继续或停止。`
                  : `当前聊天读取任务 #${command.id} 已提交，结果会写入候选人库并生成待确认草稿。`
          );
        }
        await loadDashboard();
      } catch (err) {
        setAutomationNotice(err instanceof Error ? err.message : "自动化操作失败");
      } finally {
        setAutomationBusy(null);
      }
    },
    [loadDashboard]
  );

  const activeExtensionCommand = useMemo(
    () => data?.extension.recent_commands.find((command) => ["queued", "running"].includes(command.status)) ?? null,
    [data?.extension.recent_commands]
  );

  const extensionCommands = data?.extension.recent_commands ?? [];
  const extensionCommandPageCount = Math.max(1, Math.ceil(extensionCommands.length / EXTENSION_COMMAND_PAGE_SIZE));
  const extensionCommandPageIndex = Math.min(extensionCommandPage, extensionCommandPageCount - 1);
  const pagedExtensionCommands = extensionCommands.slice(
    extensionCommandPageIndex * EXTENSION_COMMAND_PAGE_SIZE,
    extensionCommandPageIndex * EXTENSION_COMMAND_PAGE_SIZE + EXTENSION_COMMAND_PAGE_SIZE
  );
  const selectedExtensionCommand =
    pagedExtensionCommands.find((command) => command.id === selectedExtensionCommandId) ??
    pagedExtensionCommands[0] ??
    null;

  useEffect(() => {
    if (extensionCommandPage !== extensionCommandPageIndex) {
      setExtensionCommandPage(extensionCommandPageIndex);
    }
  }, [extensionCommandPage, extensionCommandPageIndex]);

  const controlAutomationCommand = useCallback(
    async (control: "running" | "paused" | "stopped") => {
      if (!activeExtensionCommand) {
        setAutomationNotice("当前没有可控制的扩展任务。");
        return;
      }
      setAutomationBusy(`control:${control}`);
      setAutomationNotice(null);
      try {
        await controlExtensionCommand(activeExtensionCommand.id, control);
        await loadDashboard();
        setAutomationNotice(
          control === "paused"
            ? `任务 #${activeExtensionCommand.id} 已暂停。`
            : control === "stopped"
              ? `任务 #${activeExtensionCommand.id} 已停止。`
              : `任务 #${activeExtensionCommand.id} 已继续。`
        );
      } catch (err) {
        setAutomationNotice(err instanceof Error ? err.message : "任务控制失败");
      } finally {
        setAutomationBusy(null);
      }
    },
    [activeExtensionCommand, loadDashboard]
  );

  const stopAllAutomationCommands = useCallback(async () => {
    setAutomationBusy("stop-all");
    setAutomationNotice(null);
    try {
      const result = await stopAllExtensionCommands();
      await pauseChatLoop();
      await loadDashboard();
      setAutomationNotice(`已停止 ${result.stopped_count} 个未完成扩展任务，并暂停自动循环。`);
    } catch (err) {
      setAutomationNotice(err instanceof Error ? err.message : "停止任务失败");
    } finally {
      setAutomationBusy(null);
    }
  }, [loadDashboard]);

  const controlChatLoop = useCallback(async (mode: "start" | "pause") => {
    setChatLoopBusy(mode);
    setAutomationNotice(null);
    try {
      await (mode === "start" ? startChatLoop() : pauseChatLoop());
      await loadDashboard();
      setAutomationNotice(
        mode === "start"
          ? "自动循环已启动：系统会按随机间隔创建每批最多 20 个未读会话的索要简历任务。"
          : "自动循环已暂停：不会再创建新的批量索要任务。"
      );
    } catch (err) {
      setAutomationNotice(err instanceof Error ? err.message : "自动循环控制失败");
    } finally {
      setChatLoopBusy(null);
    }
  }, [loadDashboard]);

  const openAuditLog = useCallback(async (entry: AuditLog) => {
    setAuditNotice(null);
    try {
      setSelectedAuditLog(await fetchAuditLog(entry.id));
    } catch (err) {
      setAuditNotice(err instanceof Error ? err.message : "无法读取日志详情");
    }
  }, []);

  const visibleCandidates = data?.candidates.items.length ? data.candidates.items : fallbackCandidates;
  const visibleJobs = data?.jobs.items ?? [];
  const metrics = useMemo(() => buildMetrics(data, visibleCandidates), [data, visibleCandidates]);
  const pipeline = useMemo(() => buildPipeline(visibleCandidates), [visibleCandidates]);
  const currentView = viewMeta[activeView];
  const healthEvents = useMemo(
    () => [
      {
        label: "Chrome 扩展",
        status: data?.extension.connected ? ("ready" as const) : ("warning" as const),
        detail: data?.extension.connected ? `已连接：${data.extension.page_title ?? "BOSS 页面"}` : "等待连接"
      },
      {
        label: "PostgreSQL",
        status: data?.databaseStatus === "ok" ? ("ready" as const) : ("warning" as const),
        detail: data?.databaseStatus === "ok" ? "已连接" : "等待连接"
      },
      ...runEvents.filter((event) => !["PostgreSQL", "浏览器会话", "Chrome 扩展"].includes(event.label))
    ],
    [data]
  );

  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="主导航">
        <div className="brand">
          <div className="brand-mark">招</div>
          <div>
            <strong>招聘工作台</strong>
            <span>候选人管理系统</span>
          </div>
        </div>

        <nav className="nav-list" aria-label="功能模块">
          <span className="nav-section-label">功能模块</span>
          {navItems.map((item) => (
            <button
              className={activeView === item.id ? "nav-item active" : "nav-item"}
              key={item.id}
              onClick={() => setActiveView(item.id)}
              type="button"
            >
              <item.icon size={18} />
              <span>{item.label}</span>
            </button>
          ))}
        </nav>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div>
            <h1>{currentView.title}</h1>
            <p>{currentView.description}</p>
          </div>
          <div className="topbar-actions">
            <div className={error ? "status-strip warning" : "status-strip"}>
              <span className="status-dot" />
              <span>{error ? "API 异常" : "API 正常"}</span>
              <strong>
                主动触达 {data?.greetingQuota.used_count ?? 0} / {data?.greetingQuota.max_count ?? 50}
              </strong>
            </div>
            <button className="refresh-button" onClick={loadDashboard} disabled={isLoading} type="button">
              <RefreshCw size={16} />
              <span>{isLoading ? "刷新中" : "刷新"}</span>
            </button>
          </div>
        </header>

        {error && (
          <section className="alert-panel" role="alert">
            后端 API 暂不可用：{error}
          </section>
        )}

        {activeView === "dashboard" && (
          <>
            <section className="metric-grid" aria-label="核心指标">
              {metrics.map((metric) => (
                <article className="metric-panel" key={metric.label}>
                  <span>{metric.label}</span>
                  <strong>{metric.value}</strong>
                  <small>{metric.detail}</small>
                </article>
              ))}
            </section>

            <section className="content-grid">
              <article className="panel wide">
                <div className="panel-header">
                  <div>
                    <h2>候选人流程</h2>
                    <p>按当前招聘状态汇总候选人数量。</p>
                  </div>
                  <Activity size={20} />
                </div>
                <div className="pipeline">
                  {pipeline.map((stage) => (
                    <div className="pipeline-step" key={stage.label}>
                      <span>{stage.label}</span>
                      <strong>{stage.count}</strong>
                    </div>
                  ))}
                </div>
              </article>

              <article className="panel">
                <div className="panel-header">
                  <div>
                    <h2>服务状态</h2>
                    <p>本地数据与浏览器采集服务。</p>
                  </div>
                  <CheckCircle2 size={20} />
                </div>
                <div className="event-list">
                  {healthEvents.map((event) => (
                    <div className="event-row" key={event.label}>
                      <span className={`event-state ${event.status}`} />
                      <div>
                        <strong>{event.label}</strong>
                        <small>{event.detail}</small>
                      </div>
                    </div>
                  ))}
                </div>
              </article>

              <article className="panel wide">
                <div className="panel-header">
                  <div>
                    <h2>候选人库</h2>
                    <p>{data ? "当前展示 PostgreSQL 中的真实记录。" : "API 不可用时展示本地兜底数据。"}</p>
                  </div>
                  <Users size={20} />
                </div>
                <CandidateTable candidates={visibleCandidates} />
              </article>

              <ActionQueuePanel
                actions={data?.actions.items.filter((item) => item.status === "pending").slice(0, 3) ?? []}
                busyId={actionBusyId}
                onDecision={(id, decision) => void reviewAction(id, decision)}
              />
              <RuntimePanel />
            </section>
          </>
        )}

        {activeView === "jobs" && (
          <section className="single-view">
            <article className="panel full">
              <div className="panel-header">
                <div>
                  <h2>岗位配置</h2>
                  <p>从后端 API 加载当前岗位配置。</p>
                </div>
                <BriefcaseBusiness size={20} />
              </div>
              <JobsTable jobs={visibleJobs} />
            </article>
          </section>
        )}

        {activeView === "candidates" && (
          <section className="single-view">
            {resumeNotice && !candidateDetail && (
              <div className="automation-notice">{resumeNotice}</div>
            )}
            <article className="panel full">
              <div className="panel-header">
                <div>
                  <h2>候选人库</h2>
                  <p>从 PostgreSQL 加载候选人记录。</p>
                </div>
                <Users size={20} />
              </div>
              <CandidateTable candidates={visibleCandidates} onSelect={(candidate) => void selectCandidate(candidate)} />
            </article>
            {candidateDetailLoading && <div className="loading-line">正在读取候选人详情...</div>}
            {candidateDetail && (
              <CandidateDetailPanel
                detail={candidateDetail}
                jobs={visibleJobs}
                selectedJobId={selectedJobId}
                resumeFile={resumeFile}
                resumeBusy={resumeBusy}
                deleteBusy={candidateDeleteBusy}
                notice={resumeNotice}
                onFileChange={setResumeFile}
                onJobChange={setSelectedJobId}
                onProcess={() => void processResume()}
                onDelete={() => void removeCandidate()}
              />
            )}
          </section>
        )}

        {activeView === "actions" && (
          <section className="single-view">
            {actionNotice && <div className="automation-notice">{actionNotice}</div>}
            <ActionQueuePanel
              actions={data?.actions.items ?? []}
              busyId={actionBusyId}
              full
              onDecision={(id, decision) => void reviewAction(id, decision)}
            />
          </section>
        )}

        {activeView === "recommendations" && (
          <RecommendationView
            busy={recommendationBusy}
            jobs={visibleJobs}
            notice={recommendationNotice}
            recommendations={data?.recommendations ?? []}
            selectedJobId={recommendationJobId}
            onGenerate={() => void runRecommendations()}
            onJobChange={setRecommendationJobId}
          />
        )}

        {activeView === "talents" && (
          <TalentView
            busy={talentBusy}
            city={talentCity}
            education={talentEducation}
            experience={talentExperience}
            intention={talentIntention}
            jobs={visibleJobs}
            keywords={talentKeywords}
            notice={talentNotice}
            quota={data?.greetingQuota}
            result={talentResult}
            salary={talentSalary}
            selectedJobId={talentJobId}
            onCityChange={setTalentCity}
            onEducationChange={setTalentEducation}
            onExperienceChange={setTalentExperience}
            onIntentionChange={setTalentIntention}
            onJobChange={(jobId) => {
              setTalentJobId(jobId);
              const job = visibleJobs.find((item) => item.id === jobId);
              if (job) {
                setTalentKeywords(job.keywords.join(", "));
              }
            }}
            onKeywordsChange={setTalentKeywords}
            onSalaryChange={setTalentSalary}
            onScan={() => void runTalentScan()}
          />
        )}

        {activeView === "automation" && (
          <section className="single-view">
            <article className="panel full">
              <div className="panel-header">
                <div>
                  <h2>候选人流程队列</h2>
                  <p>以候选人为主线推进：发现会话、索要简历、接收附件、解析评分、推荐确认。</p>
                </div>
                <Bot size={20} />
              </div>
              <div className="section-band section-band-primary">
                <div>
                  <span>业务流程层</span>
                  <strong>候选人状态由数据库驱动，不依赖当前 BOSS 页面停留在哪个聊天。</strong>
                </div>
                <small>流程队列会把“下一步该做什么”直接展示出来。</small>
              </div>
              <div className="agent-chain">
                {agentChain.map((agent, index) => (
                  <span key={agent}>
                    <strong>{index + 1}</strong>
                    {agent} Agent
                  </span>
                ))}
              </div>
              <div className="pipeline-stage-grid">
                {pipelineStageLabels.map((stage) => (
                  <div className="pipeline-stage-card" key={stage.key}>
                    <span>{stage.label}</span>
                    <strong>{data?.pipeline[stage.key] ?? 0}</strong>
                  </div>
                ))}
              </div>
              <PipelineQueue items={data?.pipeline.items ?? []} />
              <div className="section-band">
                <div>
                  <span>执行控制层</span>
                  <strong>控制 Chrome 扩展执行采集或固定索要简历话术。</strong>
                </div>
                <small>所有写入动作会进入底层执行记录和审计日志。</small>
              </div>
              <div className="automation-toolbar">
                <div className={`browser-state state-${data?.extension.connected ? "ready" : "stopped"}`}>
                  <span className="status-dot" />
                  <div>
                    <strong>{data?.extension.connected ? "扩展已连接" : "等待扩展连接"}</strong>
                    <small>
                      {data?.extension.page_title ??
                        "在 chrome://extensions 加载 browser-extension，并打开已登录的 BOSS 页面"}
                    </small>
                  </div>
                </div>
                <div className="automation-actions">
                  <button
                    className="secondary-button"
                    disabled={automationBusy !== null}
                    onClick={() => void runAutomationAction("refresh")}
                    type="button"
                  >
                    <RefreshCw size={16} />
                    <span>检测扩展</span>
                  </button>
                  <button
                    className="secondary-button"
                    disabled={automationBusy !== null || !data?.extension.connected}
                    onClick={() => void runAutomationAction("scan_chats")}
                    type="button"
                  >
                    <ScanLine size={16} />
                    <span>{automationBusy === "scan_chats" ? "提交中" : "扫描沟通列表"}</span>
                  </button>
                  <button
                    className="primary-button"
                    disabled={automationBusy !== null || !data?.extension.connected}
                    onClick={() => void runAutomationAction("scan_chat_details")}
                    type="button"
                  >
                    <Bot size={16} />
                    <span>{automationBusy === "scan_chat_details" ? "提交中" : "批量读取聊天"}</span>
                  </button>
                  <button
                    className="primary-button"
                    disabled={automationBusy !== null || !data?.extension.connected}
                    onClick={() => void runAutomationAction("request_resumes_batch")}
                    type="button"
                  >
                    <FileText size={16} />
                    <span>{automationBusy === "request_resumes_batch" ? "提交中" : "批量索要简历"}</span>
                  </button>
                  <button
                    className="secondary-button"
                    disabled={automationBusy !== null || !data?.extension.connected}
                    onClick={() => void runAutomationAction("read_current_chat")}
                    type="button"
                  >
                    <Eye size={16} />
                    <span>{automationBusy === "read_current_chat" ? "提交中" : "读取当前聊天"}</span>
                  </button>
                  <button
                    className="secondary-button"
                    disabled={automationBusy !== null || !activeExtensionCommand}
                    onClick={() => void controlAutomationCommand("paused")}
                    type="button"
                  >
                    <span>暂停</span>
                  </button>
                  <button
                    className="secondary-button"
                    disabled={automationBusy !== null || !activeExtensionCommand}
                    onClick={() => void controlAutomationCommand("running")}
                    type="button"
                  >
                    <span>继续</span>
                  </button>
                  <button
                    className="secondary-button"
                    disabled={automationBusy !== null || !activeExtensionCommand}
                    onClick={() => void stopAllAutomationCommands()}
                    type="button"
                  >
                    <span>{automationBusy === "stop-all" ? "停止中" : "停止全部"}</span>
                  </button>
                </div>
              </div>
              {automationNotice && <div className="automation-notice">{automationNotice}</div>}
              <div className="loop-control-card">
                <div>
                  <span className={data?.chatLoop.running ? "status-pill active" : "status-pill"}>
                    {data?.chatLoop.running ? "自动循环运行中" : "自动循环已暂停"}
                  </span>
                  <h3>未读新招呼循环索要简历</h3>
                  <p>
                    每批最多处理 20 个未读/红点会话，实际发送后计入每日 50 次额度；批次之间使用随机间隔。
                  </p>
                </div>
                <dl className="loop-meta">
                  <div>
                    <dt>最近状态</dt>
                    <dd>{data?.chatLoop.last_message ?? "未启动"}</dd>
                  </div>
                  <div>
                    <dt>下一批</dt>
                    <dd>
                      {data?.chatLoop.next_enqueue_at
                        ? new Date(data.chatLoop.next_enqueue_at).toLocaleString("zh-CN")
                        : "未安排"}
                    </dd>
                  </div>
                  <div>
                    <dt>最近任务</dt>
                    <dd>{data?.chatLoop.last_command_id ? `#${data.chatLoop.last_command_id}` : "暂无"}</dd>
                  </div>
                </dl>
                <div className="loop-actions">
                  <button
                    className="primary-button"
                    disabled={chatLoopBusy !== null || !data?.extension.connected}
                    onClick={() => void controlChatLoop("start")}
                    type="button"
                  >
                    <Bot size={16} />
                    <span>{chatLoopBusy === "start" ? "启动中" : "启动循环"}</span>
                  </button>
                  <button
                    className="secondary-button"
                    disabled={chatLoopBusy !== null || !data?.chatLoop.running}
                    onClick={() => void controlChatLoop("pause")}
                    type="button"
                  >
                    <span>{chatLoopBusy === "pause" ? "暂停中" : "暂停循环"}</span>
                  </button>
                </div>
              </div>
              <div className="safety-strip">
                <ShieldCheck size={18} />
                <span>受控写入：批量索要简历仅发送固定话术，不发送自由文本；其它回复和约面仍进入人工确认。</span>
              </div>
            </article>
            <article className="panel full">
              <div className="panel-header">
                <div>
                  <h2>底层执行记录</h2>
                  <p>这里是扩展命令日志：记录控制台下发给 BOSS 页面执行的任务、状态、参数、结果和失败原因。</p>
                </div>
                <ClipboardList size={20} />
              </div>
              <div className="section-band">
                <div>
                  <span>底层日志层</span>
                  <strong>用于排查“为什么没动、为什么失败、当前执行到哪一步”。</strong>
                </div>
                <small>全局审计请看左侧“审计日志”，这里聚焦 BOSS 扩展任务。</small>
              </div>
              {data?.extension.recent_commands.length ? (
                <div className="execution-log-layout">
                  <div>
                    <div className="audit-summary">
                      <strong>共 {extensionCommands.length} 条</strong>
                      <span>第 {extensionCommandPageIndex + 1} 页，每页 {EXTENSION_COMMAND_PAGE_SIZE} 条</span>
                    </div>
                    <div className="audit-list paged">
                      {pagedExtensionCommands.map((command) => (
                        <button
                          className={`audit-row ${selectedExtensionCommand?.id === command.id ? "selected" : ""}`}
                          key={command.id}
                          onClick={() => setSelectedExtensionCommandId(command.id)}
                          type="button"
                        >
                          <span className={`audit-status ${command.status === "completed" ? "ok" : ""}`} />
                          <div>
                            <strong>#{command.id} {extensionCommandLabel(command.command_type)}</strong>
                            <small>{command.error_message ?? `状态：${command.status}`}</small>
                          </div>
                          <time>{new Date(command.created_at).toLocaleTimeString("zh-CN")}</time>
                        </button>
                      ))}
                    </div>
                    <div className="pagination-bar">
                      <button
                        className="secondary-button"
                        disabled={extensionCommandPageIndex === 0}
                        onClick={() => setExtensionCommandPage((page) => Math.max(0, page - 1))}
                        type="button"
                      >
                        上一页
                      </button>
                      <span>{extensionCommandPageIndex + 1} / {extensionCommandPageCount}</span>
                      <button
                        className="secondary-button"
                        disabled={extensionCommandPageIndex >= extensionCommandPageCount - 1}
                        onClick={() => setExtensionCommandPage((page) => Math.min(extensionCommandPageCount - 1, page + 1))}
                        type="button"
                      >
                        下一页
                      </button>
                    </div>
                  </div>
                  <ExtensionCommandDetails command={selectedExtensionCommand} />
                </div>
              ) : (
                <div className="empty-state">
                  扩展安装完成后，在 BOSS 沟通页点击“扫描沟通列表”；选中某位候选人后点击“读取当前聊天”。
                </div>
              )}
            </article>
          </section>
        )}

        {activeView === "workflows" && (
          <WorkflowView
            busy={workflowBusy}
            notice={workflowNotice}
            runs={data?.workflows.items ?? []}
            onRefresh={() => void loadDashboard()}
            onRetry={(runId) => void rerunWorkflow(runId)}
            onReview={(runId, decision) => void decideWorkflow(runId, decision)}
          />
        )}

        {activeView === "audit" && (
          <section className="single-view">
            <article className="panel full audit-panel">
              <div className="panel-header">
                <div>
                  <h2>审计日志</h2>
                  <p>浏览器、扩展、简历解析、每日推荐和循环调度都会写入 PostgreSQL。</p>
                </div>
                <div className="audit-tools">
                  <select
                    aria-label="日志状态筛选"
                    value={auditStatus}
                    onChange={(event) => {
                      setAuditStatus(event.target.value);
                      setAuditPage(0);
                      setSelectedAuditLog(null);
                    }}
                  >
                    <option value="all">全部状态</option>
                    <option value="ok">成功</option>
                    <option value="failed">失败</option>
                  </select>
                  <button
                    className="secondary-button"
                    disabled={auditLoading}
                    onClick={() => void loadAuditLogs()}
                    type="button"
                  >
                    <RefreshCw size={16} />
                    <span>刷新</span>
                  </button>
                </div>
              </div>
              {auditNotice && <div className="automation-notice">{auditNotice}</div>}
              {(auditLogs?.items.length ?? data?.auditLogs.items.length) ? (
                <div className="audit-layout">
                  <div>
                    <div className="audit-summary">
                      <strong>共 {auditLogs?.total ?? data?.auditLogs.total ?? 0} 条</strong>
                      <span>第 {auditPage + 1} 页，每页 {AUDIT_PAGE_SIZE} 条</span>
                    </div>
                    <div className="audit-list paged">
                      {(auditLogs?.items ?? data?.auditLogs.items ?? []).map((entry) => (
                        <button
                          className={selectedAuditLog?.id === entry.id ? "audit-row selected" : "audit-row"}
                          key={entry.id}
                          onClick={() => void openAuditLog(entry)}
                          type="button"
                        >
                          <span className={`audit-status ${entry.status}`} />
                          <div>
                            <strong>{auditActionLabel(entry.action_type)}</strong>
                            <small>{entry.detail ?? "无附加说明"}</small>
                          </div>
                          <time>{new Date(entry.created_at).toLocaleString("zh-CN")}</time>
                        </button>
                      ))}
                    </div>
                    <div className="pagination-bar">
                      <button
                        className="secondary-button"
                        disabled={auditPage === 0 || auditLoading}
                        onClick={() => setAuditPage((page) => Math.max(0, page - 1))}
                        type="button"
                      >
                        上一页
                      </button>
                      <span>
                        {Math.min(
                          (auditPage + 1) * AUDIT_PAGE_SIZE,
                          auditLogs?.total ?? data?.auditLogs.total ?? 0
                        )}{" "}
                        / {auditLogs?.total ?? data?.auditLogs.total ?? 0}
                      </span>
                      <button
                        className="secondary-button"
                        disabled={
                          auditLoading ||
                          (auditPage + 1) * AUDIT_PAGE_SIZE >= (auditLogs?.total ?? data?.auditLogs.total ?? 0)
                        }
                        onClick={() => setAuditPage((page) => page + 1)}
                        type="button"
                      >
                        下一页
                      </button>
                    </div>
                  </div>
                  <aside className="audit-detail-panel">
                    {selectedAuditLog ? (
                      <>
                        <div className="audit-detail-header">
                          <div>
                            <span className={`status-pill ${selectedAuditLog.status === "ok" ? "active" : "danger"}`}>
                              {selectedAuditLog.status === "ok" ? "成功" : selectedAuditLog.status}
                            </span>
                            <h3>#{selectedAuditLog.id} {auditActionLabel(selectedAuditLog.action_type)}</h3>
                          </div>
                          <time>{new Date(selectedAuditLog.created_at).toLocaleString("zh-CN")}</time>
                        </div>
                        <dl className="audit-detail-list">
                          <div>
                            <dt>动作类型</dt>
                            <dd>{selectedAuditLog.action_type}</dd>
                          </div>
                          <div>
                            <dt>关联实体</dt>
                            <dd>
                              {selectedAuditLog.entity_type
                                ? `${selectedAuditLog.entity_type} #${selectedAuditLog.entity_id ?? "-"}`
                                : "无"}
                            </dd>
                          </div>
                          <div>
                            <dt>截图路径</dt>
                            <dd>{selectedAuditLog.screenshot_path ?? "无"}</dd>
                          </div>
                          <div>
                            <dt>说明</dt>
                            <dd>{selectedAuditLog.detail ?? "无附加说明"}</dd>
                          </div>
                        </dl>
                        <pre className="payload-view">
                          {JSON.stringify(selectedAuditLog.payload ?? {}, null, 2)}
                        </pre>
                      </>
                    ) : (
                      <div className="empty-state compact">点击左侧任意日志查看 payload、截图路径和关联实体。</div>
                    )}
                  </aside>
                </div>
              ) : (
                <div className="empty-state">{auditLoading ? "正在读取审计日志..." : "暂无自动化审计事件。"}</div>
              )}
            </article>
          </section>
        )}

        {activeView === "settings" && (
          <section className="settings-layout">
            <article className="settings-section">
              <div className="settings-heading">
                <div>
                  <h2>运行状态</h2>
                  <p>检查本地 API、PostgreSQL 和 Chrome 扩展是否可用。</p>
                </div>
                <Database size={19} />
              </div>
              <dl className="settings-list">
                <div>
                  <dt>后端 API</dt>
                  <dd className={error ? "value-error" : "value-ok"}>{error ? "连接异常" : "运行正常"}</dd>
                </div>
                <div>
                  <dt>PostgreSQL</dt>
                  <dd className={data?.databaseStatus === "ok" ? "value-ok" : "value-error"}>
                    {data?.databaseStatus === "ok" ? "已连接" : "未连接"}
                  </dd>
                </div>
                <div>
                  <dt>Chrome 扩展</dt>
                  <dd className={data?.extension.connected ? "value-ok" : "value-error"}>
                    {data?.extension.connected ? "已连接" : "未连接"}
                  </dd>
                </div>
                <div>
                  <dt>当前 BOSS 页面</dt>
                  <dd>{data?.extension.page_type ?? "未检测"}</dd>
                </div>
                <div>
                  <dt>最近扩展任务</dt>
                  <dd>{data?.extension.recent_commands[0]?.status ?? "暂无任务"}</dd>
                </div>
              </dl>
            </article>

            <article className="settings-section">
              <div className="settings-heading">
                <div>
                  <h2>采集与发送策略</h2>
                  <p>批量任务可暂停、继续和停止，发送行为只使用固定话术。</p>
                </div>
                <ShieldCheck size={19} />
              </div>
              <dl className="settings-list">
                <div>
                  <dt>沟通页批量处理</dt>
                  <dd>每批最多 20 个未读会话</dd>
                </div>
                <div>
                  <dt>索要简历话术</dt>
                  <dd>固定常用语</dd>
                </div>
                <div>
                  <dt>推荐牛人触达上限</dt>
                  <dd>50 次</dd>
                </div>
                <div>
                  <dt>验证码或账号异常</dt>
                  <dd>立即停止</dd>
                </div>
                <div>
                  <dt>约面及发送动作</dt>
                  <dd>人工确认</dd>
                </div>
                <div>
                  <dt>审计日志敏感信息</dt>
                  <dd>自动脱敏</dd>
                </div>
              </dl>
            </article>

            <article className="settings-section full">
              <div className="settings-heading">
                <div>
                  <h2>AI 能力</h2>
                  <p>简历解析会优先使用 PDF 原生文本，必要时走 OCR，并可用 LLM 增强画像。</p>
                </div>
                <Activity size={19} />
              </div>
              <dl className="settings-list horizontal">
                <div>
                  <dt>OCR</dt>
                  <dd className={data?.aiHealth.ocr.available ? "value-ok" : "value-error"}>
                    {data?.aiHealth.ocr.available ? "Tesseract 可用" : "未检测到"}
                  </dd>
                </div>
                <div>
                  <dt>OCR 语言</dt>
                  <dd>{data?.aiHealth.ocr.languages ?? "chi_sim+eng"}</dd>
                </div>
                <div>
                  <dt>LLM</dt>
                  <dd className={data?.aiHealth.llm.enabled && data.aiHealth.llm.configured ? "value-ok" : "value-error"}>
                    {data?.aiHealth.llm.enabled && data.aiHealth.llm.configured ? data.aiHealth.llm.model : "未启用"}
                  </dd>
                </div>
              </dl>
            </article>

            <article className="settings-section full">
              <div className="settings-heading">
                <div>
                  <h2>本地数据</h2>
                  <p>业务数据进入 PostgreSQL，简历和临时文件保存在本地运行目录。</p>
                </div>
                <FileText size={19} />
              </div>
              <dl className="settings-list horizontal">
                <div>
                  <dt>数据库</dt>
                  <dd>PostgreSQL / recruitment_agent</dd>
                </div>
                <div>
                  <dt>浏览器登录态</dt>
                  <dd>使用当前普通 Chrome，不保存账号密码</dd>
                </div>
                <div>
                  <dt>简历文件</dt>
                  <dd>data/resumes</dd>
                </div>
              </dl>
            </article>

            <article className="settings-section full">
              <div className="settings-heading">
                <div>
                  <h2>数据库表</h2>
                  <p>当前 public schema 下的核心业务表和系统表。</p>
                </div>
                <ClipboardList size={19} />
              </div>
              <div className="settings-table-list">
                {databaseTables.map((table) => (
                  <div key={table.name}>
                    <strong>{table.name}</strong>
                    <span>{table.description}</span>
                  </div>
                ))}
              </div>
            </article>
          </section>
        )}
      </main>
    </div>
  );
}

function CandidateDetailPanel({
  detail,
  jobs,
  selectedJobId,
  resumeFile,
  resumeBusy,
  deleteBusy,
  notice,
  onFileChange,
  onJobChange,
  onProcess,
  onDelete
}: {
  detail: CandidateDetail;
  jobs: Job[];
  selectedJobId: number | null;
  resumeFile: File | null;
  resumeBusy: boolean;
  deleteBusy: boolean;
  notice: string | null;
  onFileChange: (file: File | null) => void;
  onJobChange: (jobId: number | null) => void;
  onProcess: () => void;
  onDelete: () => void;
}) {
  const { candidate, profile, resumes, scores } = detail;
  const latestScore = scores[0];
  const projects = profile?.profile_json.projects ?? [];

  return (
    <article className="candidate-detail">
      <div className="candidate-detail-header">
        <div>
          <h2>{candidate.name ?? "未命名候选人"}</h2>
          <p>{candidate.profile_summary ?? "上传简历后生成候选人画像和岗位评分。"}</p>
        </div>
        <div className="candidate-detail-actions">
          {latestScore && (
            <div className="score-total">
              <strong>{Number(latestScore.total_score).toFixed(0)}</strong>
              <span>岗位匹配分</span>
            </div>
          )}
          <button
            className="danger-button"
            disabled={deleteBusy}
            onClick={onDelete}
            type="button"
          >
            <Trash2 size={16} />
            <span>{deleteBusy ? "删除中" : "删除候选人"}</span>
          </button>
        </div>
      </div>

      <div className="resume-upload">
        <label className="file-control">
          <FileUp size={17} />
          <span>{resumeFile?.name ?? "选择 PDF 简历"}</span>
          <input
            accept="application/pdf,.pdf"
            onChange={(event) => onFileChange(event.target.files?.[0] ?? null)}
            type="file"
          />
        </label>
        <select
          aria-label="评分岗位"
          onChange={(event) => onJobChange(event.target.value ? Number(event.target.value) : null)}
          value={selectedJobId ?? ""}
        >
          <option value="">仅解析，不评分</option>
          {jobs.map((job) => (
            <option key={job.id} value={job.id}>{job.title}</option>
          ))}
        </select>
        <button
          className="primary-button"
          disabled={!resumeFile || resumeBusy}
          onClick={onProcess}
          type="button"
        >
          <FileText size={16} />
          <span>{resumeBusy ? "处理中" : "解析并评分"}</span>
        </button>
      </div>
      {notice && <div className="automation-notice">{notice}</div>}

      <div className="profile-summary-grid">
        <div><span>学历</span><strong>{candidate.education_level ?? "未识别"}</strong></div>
        <div><span>学校</span><strong>{candidate.school ?? "未识别"}</strong></div>
        <div><span>专业</span><strong>{candidate.major ?? "未识别"}</strong></div>
        <div><span>候选类型</span><strong>{candidate.candidate_type ?? "未识别"}</strong></div>
        <div><span>毕业年份</span><strong>{candidate.graduation_year ?? "未识别"}</strong></div>
        <div>
          <span>简历状态</span>
          <strong>{resumes[0] ? (resumes[0].parse_status === "ok" ? "解析完成" : "待复核") : "未上传"}</strong>
        </div>
      </div>

      <div className="candidate-detail-grid">
        <section>
          <h3>技能</h3>
          <div className="tag-list">
            {profile?.skills.length
              ? profile.skills.map((skill) => <span key={skill}>{skill}</span>)
              : <em>暂无技能数据</em>}
          </div>
        </section>
        <section>
          <h3>亮点与风险</h3>
          <ul className="profile-points">
            {profile?.highlights.map((item) => <li className="positive" key={item}>{item}</li>)}
            {profile?.risks.map((item) => <li className="risk" key={item}>{item}</li>)}
            {!profile && <li>上传简历后生成。</li>}
          </ul>
        </section>
        <section className="full">
          <h3>项目经历</h3>
          <div className="project-list">
            {projects.length
              ? projects.map((project, index) => <p key={`${project}-${index}`}>{project}</p>)
              : <p>暂无项目经历数据。</p>}
          </div>
        </section>
        {latestScore && (
          <section className="full">
            <h3>评分说明</h3>
            <div className="dimension-grid">
              {scoreDimensionOrder
                .filter((key) => latestScore.dimensions[key])
                .map((key) => {
                  const dimension = latestScore.dimensions[key];
                  return (
                    <div key={key}>
                      <span>{scoreDimensionLabel(key)}</span>
                      <strong>{dimension.score ?? 0} / {dimension.max ?? 0}</strong>
                    </div>
                  );
                })}
            </div>
            <p className="score-rationale">{latestScore.rationale}</p>
          </section>
        )}
      </div>
    </article>
  );
}

const scoreDimensionOrder = [
  "skills",
  "education",
  "projects_experience",
  "completeness",
  "basic_fit"
];

function scoreDimensionLabel(key: string): string {
  const labels: Record<string, string> = {
    skills: "技能匹配",
    education: "学历要求",
    projects_experience: "项目与经验",
    completeness: "信息完整度",
    basic_fit: "基础匹配"
  };
  return labels[key] ?? key;
}

function TalentView({
  jobs,
  selectedJobId,
  city,
  education,
  experience,
  intention,
  salary,
  keywords,
  quota,
  result,
  busy,
  notice,
  onJobChange,
  onCityChange,
  onEducationChange,
  onExperienceChange,
  onIntentionChange,
  onSalaryChange,
  onKeywordsChange,
  onScan
}: {
  jobs: Job[];
  selectedJobId: number | null;
  city: string;
  education: string;
  experience: string;
  intention: string;
  salary: string;
  keywords: string;
  quota?: GreetingQuota;
  result: TalentScanResult | null;
  busy: boolean;
  notice: string | null;
  onJobChange: (jobId: number | null) => void;
  onCityChange: (value: string) => void;
  onEducationChange: (value: string) => void;
  onExperienceChange: (value: string) => void;
  onIntentionChange: (value: string) => void;
  onSalaryChange: (value: string) => void;
  onKeywordsChange: (value: string) => void;
  onScan: () => void;
}) {
  return (
    <section className="single-view">
      <article className="panel full">
        <div className="talent-header">
          <div>
            <h2>推荐牛人筛选</h2>
            <p>读取当前推荐页后在本地筛选，不执行打招呼或消息发送。</p>
          </div>
          <div className="quota-summary">
            <strong>{quota?.available_count ?? 50}</strong>
            <span>今日可用草稿额度</span>
          </div>
        </div>

        <div className="talent-filter-grid">
          <label>
            <span>岗位</span>
            <select
              onChange={(event) => onJobChange(event.target.value ? Number(event.target.value) : null)}
              value={selectedJobId ?? ""}
            >
              <option value="">请选择岗位</option>
              {jobs.map((job) => <option key={job.id} value={job.id}>{job.title}</option>)}
            </select>
          </label>
          <label>
            <span>城市</span>
            <input onChange={(event) => onCityChange(event.target.value)} value={city} />
          </label>
          <label>
            <span>学历</span>
            <input onChange={(event) => onEducationChange(event.target.value)} value={education} />
          </label>
          <label>
            <span>经验</span>
            <input onChange={(event) => onExperienceChange(event.target.value)} value={experience} />
          </label>
          <label>
            <span>求职意向</span>
            <input
              onChange={(event) => onIntentionChange(event.target.value)}
              placeholder="Python开发、后端开发"
              value={intention}
            />
          </label>
          <label>
            <span>薪资关键词</span>
            <input
              onChange={(event) => onSalaryChange(event.target.value)}
              placeholder="10-15K、200-250元/天"
              value={salary}
            />
          </label>
          <label className="wide">
            <span>岗位关键词</span>
            <input onChange={(event) => onKeywordsChange(event.target.value)} value={keywords} />
          </label>
          <button
            className="primary-button talent-scan-button"
            disabled={busy || !selectedJobId}
            onClick={onScan}
            type="button"
          >
            <ScanLine size={16} />
            <span>{busy ? "扫描中" : "扫描并生成草稿"}</span>
          </button>
        </div>
        {notice && <div className="automation-notice">{notice}</div>}
        <div className="safety-strip">
          <ShieldCheck size={18} />
          <span>
            自动发送关闭。待确认和已通过草稿共占用额度，只有未来真实发送成功才计入已使用。
          </span>
        </div>
      </article>

      <article className="panel full">
        <div className="panel-header">
          <div>
            <h2>扫描结果</h2>
            <p>
              {result
                ? `读取 ${result.total_read}，匹配 ${result.matched_count}，去重 ${result.duplicate_count}，草稿 ${result.drafted_count}。`
                : "启动浏览器并手工登录 BOSS 后读取推荐牛人页面。"}
            </p>
          </div>
          <Users size={20} />
        </div>
        {result?.cards.length ? (
          <div className="talent-card-list">
            {result.cards.map((card) => (
              <div className="talent-result-row" key={card.boss_uid}>
                <div>
                  <strong>{card.name}</strong>
                  <span>
                    {[card.city, card.education_level, card.school, card.experience]
                      .filter(Boolean)
                      .join(" / ") || "卡片信息待补充"}
                  </span>
                </div>
                <div className="tag-list">
                  {card.skills.slice(0, 8).map((skill) => <span key={skill}>{skill}</span>)}
                </div>
                <span>{card.intention ?? card.expected_salary ?? "未识别意向"}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state">暂无匹配卡片。</div>
        )}
      </article>
    </section>
  );
}

function RecommendationView({
  recommendations,
  jobs,
  selectedJobId,
  busy,
  notice,
  onJobChange,
  onGenerate
}: {
  recommendations: Recommendation[];
  jobs: Job[];
  selectedJobId: number | null;
  busy: boolean;
  notice: string | null;
  onJobChange: (jobId: number | null) => void;
  onGenerate: () => void;
}) {
  const visible = selectedJobId
    ? recommendations.filter((item) => item.job_id === selectedJobId)
    : recommendations;

  return (
    <section className="single-view">
      <article className="panel full">
        <div className="recommendation-toolbar">
          <div>
            <h2>岗位候选人推荐</h2>
            <p>根据已入库评分生成排名，约面话术只进入待确认队列。</p>
          </div>
          <div className="recommendation-controls">
            <select
              aria-label="推荐岗位"
              onChange={(event) => onJobChange(event.target.value ? Number(event.target.value) : null)}
              value={selectedJobId ?? ""}
            >
              <option value="">全部岗位</option>
              {jobs.map((job) => (
                <option key={job.id} value={job.id}>{job.title}</option>
              ))}
            </select>
            <button
              className="primary-button"
              disabled={busy || !jobs.length}
              onClick={onGenerate}
              type="button"
            >
              <Award size={16} />
              <span>{busy ? "生成中" : "生成今日推荐"}</span>
            </button>
          </div>
        </div>
        {notice && <div className="automation-notice">{notice}</div>}
      </article>

      {visible.length ? (
        <div className="recommendation-list">
          {visible.map((item) => (
            <article className="recommendation-item" key={item.id}>
              <div className="recommendation-rank">{item.rank}</div>
              <div className="recommendation-body">
                <div className="recommendation-title">
                  <div>
                    <h2>{item.candidate_name}</h2>
                    <span>{item.job_title}</span>
                  </div>
                  <strong>{item.total_score.toFixed(0)} 分</strong>
                </div>
                <p className="recommendation-reason">{item.reason}</p>
                <div className="recommendation-notes">
                  <div>
                    <span>亮点</span>
                    <p>{item.highlights.length ? item.highlights.join("；") : "暂无额外亮点"}</p>
                  </div>
                  <div>
                    <span>风险</span>
                    <p>{item.risks.length ? item.risks.join("；") : "暂无明显风险"}</p>
                  </div>
                </div>
                {item.interview_draft && (
                  <div className="draft-preview">
                    <div>
                      <strong>约面草稿</strong>
                      <span>{actionStatusLabel(item.action_status)}</span>
                    </div>
                    <p>{item.interview_draft}</p>
                  </div>
                )}
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="empty-state">当前岗位暂无今日推荐。先完成简历评分，再生成推荐。</div>
      )}
    </section>
  );
}

function actionStatusLabel(status?: string | null): string {
  const labels: Record<string, string> = {
    pending: "待确认",
    approved: "已通过，未发送",
    rejected: "已拒绝",
    executed: "已执行",
    failed: "执行失败"
  };
  return status ? labels[status] ?? status : "未生成";
}

function ActionQueuePanel({
  actions,
  busyId,
  onDecision,
  full = false
}: {
  actions: ActionQueueEntry[];
  busyId: number | null;
  onDecision: (actionId: number, decision: "approve" | "reject") => void;
  full?: boolean;
}) {
  return (
    <article className={full ? "panel full" : "panel"}>
      <div className="panel-header">
        <div>
          <h2>待确认动作</h2>
          <p>涉及发送、约面等动作默认先进入确认队列。</p>
        </div>
        <AlertTriangle size={20} />
      </div>
      {actions.length ? (
        <div className="action-list">
          {actions.map((item) => (
            <div className="action-review-row" key={item.id}>
              <FileText size={18} />
              <div>
                <strong>
                  {item.action_type === "interview_invite"
                    ? "约面邀请"
                    : ["request_resume_greeting", "request_resume_chat"].includes(item.action_type)
                      ? "索要简历"
                      : item.action_type === "resume_attachment_detected"
                        ? "发现简历附件"
                      : item.action_type}
                </strong>
                <span>{item.candidate_name ?? "未知候选人"} / {item.job_title ?? "未关联岗位"}</span>
                {item.draft_message && <p>{item.draft_message}</p>}
              </div>
              <div className="action-review-status">
                <span>{actionStatusLabel(item.status)}</span>
                {item.status === "pending" && (
                  <div>
                    <button
                      disabled={busyId !== null}
                      onClick={() => onDecision(item.id, "approve")}
                      title="通过草稿"
                      type="button"
                    >
                      <ThumbsUp size={15} />
                    </button>
                    <button
                      disabled={busyId !== null}
                      onClick={() => onDecision(item.id, "reject")}
                      title="拒绝草稿"
                      type="button"
                    >
                      <ThumbsDown size={15} />
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="empty-state">暂无待确认动作。</div>
      )}
    </article>
  );
}

function RuntimePanel() {
  return (
    <article className="panel full">
      <div className="panel-header">
        <div>
          <h2>运行信息</h2>
          <p>当前已启用的数据接口和采集能力。</p>
        </div>
        <Database size={20} />
      </div>
      <div className="check-grid">
        <span>数据库连接正常</span>
        <span>浏览器会话管理</span>
        <span>沟通页采集与索要简历</span>
        <span>操作记录可追溯</span>
      </div>
    </article>
  );
}
