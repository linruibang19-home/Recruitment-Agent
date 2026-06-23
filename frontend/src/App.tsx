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
  ShieldCheck,
  Users
} from "lucide-react";
import { actionQueue, candidates, metrics, pipeline, runEvents } from "./data";

const navItems = [
  { label: "Dashboard", icon: LayoutDashboard, active: true },
  { label: "Jobs", icon: BriefcaseBusiness },
  { label: "Candidates", icon: Users },
  { label: "Action Queue", icon: ListChecks },
  { label: "Automation", icon: Bot },
  { label: "Audit Logs", icon: ClipboardList }
];

export function App() {
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
            <p>Phase 1 基础骨架已就绪，业务自动化将在后续阶段接入。</p>
          </div>
          <div className="status-strip">
            <span className="status-dot" />
            <span>API Ready</span>
            <strong>主动触达 0 / 50</strong>
          </div>
        </header>

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
                <p>后续接入 PostgreSQL 后展示真实状态机数据。</p>
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
                <p>当前阶段只启用基础服务自检。</p>
              </div>
              <CheckCircle2 size={20} />
            </div>
            <div className="event-list">
              {runEvents.map((event) => (
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
                <h2>每日优秀候选人</h2>
                <p>示例数据用于前端骨架展示。</p>
              </div>
              <Users size={20} />
            </div>
            <div className="candidate-table">
              <div className="table-head">
                <span>候选人</span>
                <span>学历</span>
                <span>技能</span>
                <span>匹配分</span>
                <span>状态</span>
              </div>
              {candidates.map((candidate) => (
                <div className="table-row" key={candidate.name}>
                  <strong>{candidate.name}</strong>
                  <span>{candidate.education}</span>
                  <span className="skill-list">{candidate.skills.join(" / ")}</span>
                  <span className="score">{candidate.match}</span>
                  <span>{candidate.status}</span>
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
                    <span>{item.candidate} · {item.risk}</span>
                  </div>
                  <time>{item.time}</time>
                </div>
              ))}
            </div>
          </article>

          <article className="panel full">
            <div className="panel-header">
              <div>
                <h2>Phase 1 自检范围</h2>
                <p>本阶段验证新架构能启动，业务数据将在 Phase 2 后接入。</p>
              </div>
              <Database size={20} />
            </div>
            <div className="check-grid">
              <span>FastAPI /api/health</span>
              <span>React + Vite build</span>
              <span>Git sensitive-file guard</span>
              <span>Execution docs aligned</span>
            </div>
          </article>
        </section>
      </main>
    </div>
  );
}

