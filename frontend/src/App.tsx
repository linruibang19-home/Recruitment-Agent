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
  RefreshCw,
  ShieldCheck,
  Users
} from "lucide-react";
import { fetchDashboardData, type DashboardData } from "./api";
import { actionQueue, candidates as fallbackCandidates, runEvents } from "./data";
import type { Candidate, Metric, PipelineStage } from "./types";

const navItems = [
  { label: "Dashboard", icon: LayoutDashboard, active: true },
  { label: "Jobs", icon: BriefcaseBusiness },
  { label: "Candidates", icon: Users },
  { label: "Action Queue", icon: ListChecks },
  { label: "Automation", icon: Bot },
  { label: "Audit Logs", icon: ClipboardList }
];

function candidateEducation(candidate: Candidate): string {
  const parts = [candidate.education_level, candidate.school].filter(Boolean);
  return parts.length ? parts.join(" · ") : "未录入";
}

function candidateSkills(candidate: Candidate): string {
  const skills = candidate.raw_card?.skills;
  if (Array.isArray(skills) && skills.length > 0) {
    return skills.map(String).join(" / ");
  }
  return candidate.major ?? "待解析";
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
    { label: "候选人总数", value: String(data?.candidates.total ?? candidates.length), detail: "PostgreSQL" },
    { label: "岗位配置", value: String(data?.jobs.total ?? 0), detail: "已入库岗位" },
    { label: "主动触达额度", value: "0 / 50", detail: "今日已使用" },
    {
      label: "数据库状态",
      value: data?.databaseStatus === "ok" ? "OK" : "待连接",
      detail: "health/database"
    }
  ];
}

export function App() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  const visibleCandidates = data?.candidates.items.length ? data.candidates.items : fallbackCandidates;
  const metrics = useMemo(() => buildMetrics(data, visibleCandidates), [data, visibleCandidates]);
  const pipeline = useMemo(() => buildPipeline(visibleCandidates), [visibleCandidates]);
  const healthEvents = useMemo(
    () => [
      {
        label: "PostgreSQL",
        status: data?.databaseStatus === "ok" ? "ready" : "warning",
        detail: data?.databaseStatus === "ok" ? "连接正常" : "等待连接"
      },
      ...runEvents.filter((event) => event.label !== "PostgreSQL")
    ],
    [data]
  );

  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="主导航">
        <div className="brand">
          <div className="brand-mark">RA</div>
          <div>
            <strong>Recruitment Agent</strong>
            <span>Local Control Plane</span>
          </div>
        </div>

        <nav className="nav-list">
          {navItems.map((item) => (
            <button className={item.active ? "nav-item active" : "nav-item"} key={item.label}>
              <item.icon size={18} />
              <span>{item.label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-status">
          <ShieldCheck size={18} />
          <div>
            <strong>受控自动化</strong>
            <span>发送动作默认人工确认</span>
          </div>
        </div>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div>
            <h1>招聘 Agent 控制台</h1>
            <p>Phase 3 正在接入真实 API 数据，自动化能力将按阶段逐步打开。</p>
          </div>
          <div className="topbar-actions">
            <div className={error ? "status-strip warning" : "status-strip"}>
              <span className="status-dot" />
              <span>{error ? "API Error" : "API Ready"}</span>
              <strong>主动触达 0 / 50</strong>
            </div>
            <button className="refresh-button" onClick={loadDashboard} disabled={isLoading}>
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
                <p>按当前候选人状态实时汇总。</p>
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
                <h2>自动化健康</h2>
                <p>显示后端服务和后续自动化模块状态。</p>
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
                <p>{data ? "来自 PostgreSQL 的真实数据。" : "后端不可用时展示本地兜底数据。"}</p>
              </div>
              <Users size={20} />
            </div>
            <div className="candidate-table">
              <div className="table-head">
                <span>候选人</span>
                <span>学历</span>
                <span>技能</span>
                <span>来源</span>
                <span>状态</span>
              </div>
              {visibleCandidates.map((candidate, index) => (
                <div className="table-row" key={candidate.id ?? `${candidate.name}-${index}`}>
                  <strong>{candidate.name ?? "未命名"}</strong>
                  <span>{candidateEducation(candidate)}</span>
                  <span className="skill-list">{candidateSkills(candidate)}</span>
                  <span>{candidate.source ?? "manual"}</span>
                  <span>{statusLabel(candidate.status)}</span>
                </div>
              ))}
            </div>
          </article>

          <article className="panel">
            <div className="panel-header">
              <div>
                <h2>待确认动作</h2>
                <p>高风险写动作默认进入队列。</p>
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
                      {item.candidate} · {item.risk}
                    </span>
                  </div>
                  <time>{item.time}</time>
                </div>
              ))}
            </div>
          </article>

          <article className="panel full">
            <div className="panel-header">
              <div>
                <h2>Phase 3 自检范围</h2>
                <p>本阶段验证前端能读取真实后端 API，并保留失败兜底状态。</p>
              </div>
              <Database size={20} />
            </div>
            <div className="check-grid">
              <span>GET /api/health/database</span>
              <span>GET /api/jobs</span>
              <span>GET /api/candidates</span>
              <span>Refresh interaction</span>
            </div>
          </article>
        </section>
      </main>
    </div>
  );
}
