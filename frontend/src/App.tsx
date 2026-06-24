import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  Bot,
  BriefcaseBusiness,
  CheckCircle2,
  ClipboardList,
  Database,
  FileText,
  LayoutDashboard,
  ListChecks,
  LogIn,
  Paperclip,
  Play,
  RefreshCw,
  ScanLine,
  ShieldCheck,
  Square,
  Users
} from "lucide-react";
import {
  fetchDashboardData,
  openChat,
  scanChats,
  startBrowser,
  stopBrowser,
  type DashboardData
} from "./api";
import { actionQueue, candidates as fallbackCandidates, runEvents } from "./data";
import type { BrowserStatus, Candidate, ChatScanResult, Job, Metric, PipelineStage } from "./types";

type ViewId = "dashboard" | "jobs" | "candidates" | "actions" | "automation" | "audit";

const navItems: Array<{ id: ViewId; label: string; icon: typeof LayoutDashboard }> = [
  { id: "dashboard", label: "控制台", icon: LayoutDashboard },
  { id: "jobs", label: "岗位", icon: BriefcaseBusiness },
  { id: "candidates", label: "候选人", icon: Users },
  { id: "actions", label: "待确认", icon: ListChecks },
  { id: "automation", label: "自动化", icon: Bot },
  { id: "audit", label: "审计日志", icon: ClipboardList }
];

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
    chat_open: "读取聊天详情"
  };
  return labels[actionType] ?? actionType;
}

function CandidateTable({ candidates }: { candidates: Candidate[] }) {
  return (
    <div className="candidate-table">
      <div className="table-head">
        <span>候选人</span>
        <span>学历/学校</span>
        <span>技能/专业</span>
        <span>来源</span>
        <span>状态</span>
      </div>
      {candidates.map((candidate, index) => (
        <div className="table-row" key={candidate.id ?? `${candidate.name}-${index}`}>
          <strong>{candidate.name ?? "未命名"}</strong>
          <span>{candidateEducation(candidate)}</span>
          <span className="skill-list">{candidateSkills(candidate)}</span>
          <span>{sourceLabel(candidate.source)}</span>
          <span>{statusLabel(candidate.status)}</span>
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
          <div className="brand-mark">RA</div>
          <div>
            <strong>招聘 Agent</strong>
            <span>本地控制台</span>
          </div>
        </div>

        <nav className="nav-list">
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

        <div className="sidebar-status">
          <ShieldCheck size={18} />
          <div>
            <strong>受控自动化</strong>
            <span>发送动作默认进入确认队列</span>
          </div>
        </div>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div>
            <h1>招聘 Agent 控制台</h1>
            <p>Phase 4 已接入 BOSS 沟通页只读扫描，所有发送动作仍需人工确认。</p>
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
                    <h2>自动化健康状态</h2>
                    <p>后端服务与后续自动化模块接入状态。</p>
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

              <ActionQueuePanel />
              <SelfCheckPanel />
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
              <CandidateTable candidates={visibleCandidates} />
            </article>
          </section>
        )}

        {activeView === "actions" && (
          <section className="single-view">
            <ActionQueuePanel full />
          </section>
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
      </main>
    </div>
  );
}

function ActionQueuePanel({ full = false }: { full?: boolean }) {
  return (
    <article className={full ? "panel full" : "panel"}>
      <div className="panel-header">
        <div>
          <h2>待确认动作</h2>
          <p>涉及发送、约面等动作默认先进入确认队列。</p>
        </div>
        <AlertTriangle size={20} />
      </div>
      <div className="action-list">
        {actionQueue.map((item) => (
          <div className="action-row" key={`${item.title}-${item.candidate}`}>
            <FileText size={18} />
            <div>
              <strong>{item.title}</strong>
              <span>
                {item.candidate} / {item.risk}
              </span>
            </div>
            <time>{item.time}</time>
          </div>
        ))}
      </div>
    </article>
  );
}

function SelfCheckPanel() {
  return (
    <article className="panel full">
      <div className="panel-header">
        <div>
          <h2>Phase 4 自检</h2>
          <p>验证浏览器状态、只读扫描、附件识别和审计日志链路。</p>
        </div>
        <Database size={20} />
      </div>
      <div className="check-grid">
        <span>GET /api/health/database</span>
        <span>GET /api/automation/browser/status</span>
        <span>POST /api/automation/chat/scan</span>
        <span>GET /api/audit-logs</span>
      </div>
    </article>
  );
}
