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
  Eye,
  FileText,
  FileUp,
  LayoutDashboard,
  ListChecks,
  LogIn,
  Paperclip,
  Play,
  RefreshCw,
  ScanLine,
  Settings,
  ShieldCheck,
  Square,
  ThumbsDown,
  ThumbsUp,
  Users
} from "lucide-react";
import {
  decideAction,
  fetchCandidateDetail,
  fetchDashboardData,
  generateRecommendations,
  openChat,
  scanChats,
  startBrowser,
  stopBrowser,
  uploadResume,
  type DashboardData
} from "./api";
import { candidates as fallbackCandidates, runEvents } from "./data";
import type {
  ActionQueueEntry,
  BrowserStatus,
  Candidate,
  CandidateDetail,
  ChatScanResult,
  Job,
  Metric,
  PipelineStage,
  Recommendation
} from "./types";

type ViewId =
  | "dashboard"
  | "jobs"
  | "candidates"
  | "recommendations"
  | "actions"
  | "automation"
  | "audit"
  | "settings";

const navItems: Array<{ id: ViewId; label: string; icon: typeof LayoutDashboard }> = [
  { id: "dashboard", label: "工作台", icon: LayoutDashboard },
  { id: "jobs", label: "岗位管理", icon: BriefcaseBusiness },
  { id: "candidates", label: "候选人库", icon: Users },
  { id: "recommendations", label: "每日推荐", icon: Award },
  { id: "actions", label: "待确认", icon: ListChecks },
  { id: "automation", label: "沟通采集", icon: Bot },
  { id: "audit", label: "审计日志", icon: ClipboardList }
];

const viewMeta: Record<ViewId, { title: string; description: string }> = {
  dashboard: { title: "招聘工作台", description: "查看岗位、候选人和自动化服务的当前状态。" },
  jobs: { title: "岗位管理", description: "维护招聘岗位及候选人匹配条件。" },
  candidates: { title: "候选人库", description: "查看已采集候选人的基础资料和处理进度。" },
  recommendations: { title: "每日推荐", description: "按岗位查看高匹配候选人和约面建议。" },
  actions: { title: "待确认", description: "审核消息发送、约面等需要人工确认的操作。" },
  automation: { title: "沟通采集", description: "连接 BOSS 沟通页并执行只读信息采集。" },
  audit: { title: "审计日志", description: "查询浏览器会话和采集任务的执行记录。" },
  settings: { title: "系统设置", description: "查看本地服务、数据存储和自动化安全策略。" }
};

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
    { label: "主动触达额度", value: "0 / 50", detail: "今日已使用" },
    {
      label: "数据库",
      value: data?.databaseStatus === "ok" ? "正常" : "离线",
      detail: "health/database"
    }
  ];
}

function browserStateLabel(status?: BrowserStatus | null): string {
  const labels = {
    stopped: "未启动",
    starting: "启动中",
    ready: "可扫描",
    login_required: "等待登录",
    blocked: "已安全停机",
    error: "异常"
  };
  return status ? labels[status.state] : "未知";
}

function auditActionLabel(actionType: string): string {
  const labels: Record<string, string> = {
    browser_start: "启动浏览器",
    browser_stop: "停止浏览器",
    chat_scan: "扫描沟通列表",
    chat_open: "读取聊天详情",
    resume_process: "解析简历",
    candidate_score: "候选人评分",
    daily_recommendation: "生成每日推荐",
    daily_recommendation_schedule: "定时每日推荐",
    action_approved: "通过待确认动作",
    action_rejected: "拒绝待确认动作"
  };
  return labels[actionType] ?? actionType;
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
  const [scanResult, setScanResult] = useState<ChatScanResult | null>(null);
  const [candidateDetail, setCandidateDetail] = useState<CandidateDetail | null>(null);
  const [candidateDetailLoading, setCandidateDetailLoading] = useState(false);
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [selectedJobId, setSelectedJobId] = useState<number | null>(null);
  const [resumeBusy, setResumeBusy] = useState(false);
  const [resumeNotice, setResumeNotice] = useState<string | null>(null);
  const [recommendationJobId, setRecommendationJobId] = useState<number | null>(null);
  const [recommendationBusy, setRecommendationBusy] = useState(false);
  const [recommendationNotice, setRecommendationNotice] = useState<string | null>(null);
  const [actionBusyId, setActionBusyId] = useState<number | null>(null);
  const [actionNotice, setActionNotice] = useState<string | null>(null);

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

  useEffect(() => {
    if (!selectedJobId && data?.jobs.items[0]) {
      setSelectedJobId(data.jobs.items[0].id);
    }
    if (!recommendationJobId && data?.jobs.items[0]) {
      setRecommendationJobId(data.jobs.items[0].id);
    }
  }, [data?.jobs.items, recommendationJobId, selectedJobId]);

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

  const runAutomationAction = useCallback(
    async (action: "start" | "stop" | "scan", candidateName?: string) => {
      setAutomationBusy(candidateName ? `open:${candidateName}` : action);
      setAutomationNotice(null);
      try {
        if (action === "start") {
          const status = await startBrowser();
          setAutomationNotice(status.detail ?? "浏览器已启动");
        } else if (action === "stop") {
          const status = await stopBrowser();
          setScanResult(null);
          setAutomationNotice(status.detail ?? "浏览器已停止");
        } else if (candidateName) {
          const result = await openChat(candidateName);
          setScanResult((current) => ({
            ...result,
            conversations: current?.conversations ?? []
          }));
          setAutomationNotice(`已读取 ${candidateName} 的聊天详情，未执行发送动作。`);
        } else {
          const result = await scanChats();
          setScanResult(result);
          setAutomationNotice(`已读取 ${result.conversations.length} 个会话，未执行发送动作。`);
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

  const visibleCandidates = data?.candidates.items.length ? data.candidates.items : fallbackCandidates;
  const visibleJobs = data?.jobs.items ?? [];
  const metrics = useMemo(() => buildMetrics(data, visibleCandidates), [data, visibleCandidates]);
  const pipeline = useMemo(() => buildPipeline(visibleCandidates), [visibleCandidates]);
  const currentView = viewMeta[activeView];
  const healthEvents = useMemo(
    () => [
      {
        label: "浏览器会话",
        status: data?.browser.state === "ready" ? ("ready" as const) : ("warning" as const),
        detail: data?.browser.detail ?? "尚未启动"
      },
      {
        label: "PostgreSQL",
        status: data?.databaseStatus === "ok" ? ("ready" as const) : ("warning" as const),
        detail: data?.databaseStatus === "ok" ? "已连接" : "等待连接"
      },
      ...runEvents.filter((event) => !["PostgreSQL", "浏览器会话"].includes(event.label))
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

        <button
          className={activeView === "settings" ? "sidebar-settings active" : "sidebar-settings"}
          onClick={() => setActiveView("settings")}
          type="button"
        >
          <Settings size={18} />
          <span>系统设置</span>
        </button>
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
              <strong>主动触达 0 / 50</strong>
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
                notice={resumeNotice}
                onFileChange={setResumeFile}
                onJobChange={setSelectedJobId}
                onProcess={() => void processResume()}
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

        {activeView === "automation" && (
          <section className="single-view">
            <article className="panel full">
              <div className="panel-header">
                <div>
                  <h2>浏览器自动化</h2>
                  <p>使用独立 Chrome 登录态读取沟通列表、聊天详情和 PDF 附件卡片。</p>
                </div>
                <Bot size={20} />
              </div>
              <div className="automation-toolbar">
                <div className={`browser-state state-${data?.browser.state ?? "stopped"}`}>
                  <span className="status-dot" />
                  <div>
                    <strong>{browserStateLabel(data?.browser)}</strong>
                    <small>{data?.browser.detail ?? "点击启动浏览器后手工登录 BOSS 直聘"}</small>
                  </div>
                </div>
                <div className="automation-actions">
                  <button
                    className="secondary-button"
                    disabled={automationBusy !== null || data?.browser.running}
                    onClick={() => void runAutomationAction("start")}
                    type="button"
                  >
                    {data?.browser.state === "login_required" ? <LogIn size={16} /> : <Play size={16} />}
                    <span>启动浏览器</span>
                  </button>
                  <button
                    className="primary-button"
                    disabled={automationBusy !== null || data?.browser.state !== "ready"}
                    onClick={() => void runAutomationAction("scan")}
                    type="button"
                  >
                    <ScanLine size={16} />
                    <span>{automationBusy === "scan" ? "扫描中" : "扫描沟通列表"}</span>
                  </button>
                  <button
                    className="icon-button"
                    disabled={automationBusy !== null || !data?.browser.running}
                    onClick={() => void runAutomationAction("stop")}
                    title="停止浏览器会话"
                    type="button"
                  >
                    <Square size={16} />
                  </button>
                </div>
              </div>
              {automationNotice && <div className="automation-notice">{automationNotice}</div>}
              <div className="safety-strip">
                <ShieldCheck size={18} />
                <span>只读模式：不填写输入框、不发送消息；遇到登录、验证码或账号异常会停止扫描。</span>
              </div>
            </article>
            <article className="panel full">
              <div className="panel-header">
                <div>
                  <h2>沟通页扫描结果</h2>
                  <p>点击候选人可读取当前聊天详情并识别附件，不会发送消息。</p>
                </div>
                <ScanLine size={20} />
              </div>
              {scanResult?.conversations.length ? (
                <div className="conversation-list">
                  {scanResult.conversations.map((conversation, index) => (
                    <div className="conversation-row" key={`${conversation.name}-${index}`}>
                      <div>
                        <strong>{conversation.name}</strong>
                        <span>{conversation.preview ?? conversation.raw_text}</span>
                      </div>
                      <button
                        className="text-button"
                        disabled={automationBusy !== null}
                        onClick={() => void runAutomationAction("scan", conversation.name)}
                        type="button"
                      >
                        {automationBusy === `open:${conversation.name}` ? "读取中" : "读取详情"}
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="empty-state">启动浏览器并手工登录后，可执行只读扫描。</div>
              )}
            </article>
            {scanResult?.detail && (
              <article className="panel full">
                <div className="panel-header">
                  <div>
                    <h2>{scanResult.detail.candidate_name ?? "当前候选人"}的聊天详情</h2>
                    <p>读取到 {scanResult.detail.messages.length} 条消息和 {scanResult.detail.attachments.length} 个附件。</p>
                  </div>
                  <Paperclip size={20} />
                </div>
                <div className="detail-grid">
                  <div>
                    <strong>最近消息</strong>
                    <div className="message-list">
                      {scanResult.detail.messages.slice(-8).map((message, index) => (
                        <span key={`${message}-${index}`}>{message}</span>
                      ))}
                      {!scanResult.detail.messages.length && <span>未识别到消息文本。</span>}
                    </div>
                  </div>
                  <div>
                    <strong>附件识别</strong>
                    <div className="message-list">
                      {scanResult.detail.attachments.map((attachment, index) => (
                        <span key={`${attachment.filename}-${index}`}>
                          {attachment.filename ?? attachment.preview_text ?? "简历附件卡片"}
                        </span>
                      ))}
                      {!scanResult.detail.attachments.length && <span>当前聊天未识别到 PDF 附件。</span>}
                    </div>
                  </div>
                </div>
              </article>
            )}
          </section>
        )}

        {activeView === "audit" && (
          <section className="single-view">
            <article className="panel full">
              <div className="panel-header">
                <div>
                  <h2>审计日志</h2>
                  <p>浏览器启动、停止、扫描和聊天读取均写入 PostgreSQL。</p>
                </div>
                <ClipboardList size={20} />
              </div>
              {data?.auditLogs.items.length ? (
                <div className="audit-list">
                  {data.auditLogs.items.map((entry) => (
                    <div className="audit-row" key={entry.id}>
                      <span className={`audit-status ${entry.status}`} />
                      <div>
                        <strong>{auditActionLabel(entry.action_type)}</strong>
                        <small>{entry.detail ?? "无附加说明"}</small>
                      </div>
                      <time>{new Date(entry.created_at).toLocaleString("zh-CN")}</time>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="empty-state">暂无自动化审计事件。</div>
              )}
            </article>
          </section>
        )}

        {activeView === "settings" && (
          <section className="settings-layout">
            <article className="settings-section">
              <div className="settings-heading">
                <div>
                  <h2>运行环境</h2>
                  <p>当前服务仅在本机运行，登录信息和采集文件不会进入 Git。</p>
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
                  <dt>浏览器会话</dt>
                  <dd>{browserStateLabel(data?.browser)}</dd>
                </div>
              </dl>
            </article>

            <article className="settings-section">
              <div className="settings-heading">
                <div>
                  <h2>自动化策略</h2>
                  <p>外部写操作默认关闭，消息发送必须经过人工确认。</p>
                </div>
                <ShieldCheck size={19} />
              </div>
              <dl className="settings-list">
                <div>
                  <dt>运行模式</dt>
                  <dd>只读采集</dd>
                </div>
                <div>
                  <dt>每日主动触达上限</dt>
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
              </dl>
            </article>

            <article className="settings-section full">
              <div className="settings-heading">
                <div>
                  <h2>本地数据</h2>
                  <p>敏感数据保存在项目的本地运行目录中。</p>
                </div>
                <FileText size={19} />
              </div>
              <dl className="settings-list horizontal">
                <div>
                  <dt>浏览器登录态</dt>
                  <dd>data/profiles/boss-chrome</dd>
                </div>
                <div>
                  <dt>审计截图</dt>
                  <dd>data/screenshots</dd>
                </div>
                <div>
                  <dt>简历文件</dt>
                  <dd>data/resumes</dd>
                </div>
              </dl>
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
  notice,
  onFileChange,
  onJobChange,
  onProcess
}: {
  detail: CandidateDetail;
  jobs: Job[];
  selectedJobId: number | null;
  resumeFile: File | null;
  resumeBusy: boolean;
  notice: string | null;
  onFileChange: (file: File | null) => void;
  onJobChange: (jobId: number | null) => void;
  onProcess: () => void;
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
        {latestScore && (
          <div className="score-total">
            <strong>{Number(latestScore.total_score).toFixed(0)}</strong>
            <span>岗位匹配分</span>
          </div>
        )}
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
                <strong>{item.action_type === "interview_invite" ? "约面邀请" : item.action_type}</strong>
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
        <span>沟通列表只读采集</span>
        <span>操作记录可追溯</span>
      </div>
    </article>
  );
}
