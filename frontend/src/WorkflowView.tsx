import { Check, GitBranch, Play, RefreshCw, RotateCcw, X } from "lucide-react";
import { useMemo, useState } from "react";

import type { Candidate, Job, WorkflowRun, WorkflowStartInput } from "./types";

type WorkflowViewProps = {
  candidates: Candidate[];
  jobs: Job[];
  runs: WorkflowRun[];
  busy: string | null;
  notice: string | null;
  onStart: (input: WorkflowStartInput) => void;
  onReview: (runId: number, decision: "approved" | "rejected") => void;
  onRetry: (runId: number) => void;
  onRefresh: () => void;
};

const workflowLabels: Record<WorkflowRun["workflow_name"], string> = {
  chat_resume: "沟通页简历处理",
  recommend_talent: "推荐牛人触达",
  daily_recommendation: "每日候选人推荐"
};

const statusLabels: Record<string, string> = {
  running: "执行中",
  waiting_review: "等待人工确认",
  completed: "已完成",
  rejected: "已拒绝",
  failed: "执行失败"
};

const nodeLabels: Record<string, string> = {
  load_conversation: "读取沟通记录",
  extract_candidate: "提取候选人",
  detect_resume: "检查简历",
  parse_resume: "解析简历",
  profile_candidate: "生成画像",
  score_candidate: "岗位评分",
  decide_action: "生成下一步建议",
  load_recommend_page: "读取推荐页",
  apply_filters: "应用筛选条件",
  extract_cards: "提取牛人卡片",
  dedupe: "候选人去重",
  pre_score: "卡片预评分",
  quota_check: "检查触达额度",
  draft_greeting: "生成招呼草稿",
  load_candidates: "载入候选人",
  rank: "候选人排序",
  generate_reasons: "生成推荐理由",
  draft_interview_invites: "生成约面草稿",
  save_report: "保存日报",
  human_review: "人工确认",
  record_result: "记录结果",
  notify: "完成通知"
};

export function WorkflowView({
  candidates,
  jobs,
  runs,
  busy,
  notice,
  onStart,
  onReview,
  onRetry,
  onRefresh
}: WorkflowViewProps) {
  const [workflowName, setWorkflowName] = useState<WorkflowRun["workflow_name"]>("chat_resume");
  const [candidateId, setCandidateId] = useState<number | undefined>(candidates[0]?.id);
  const [jobId, setJobId] = useState<number | undefined>(jobs[0]?.id);
  const selectedRun = useMemo(() => runs[0] ?? null, [runs]);

  const requiresCandidate = workflowName === "chat_resume";
  const requiresJob = workflowName !== "chat_resume";
  const canStart = (!requiresCandidate || candidateId) && (!requiresJob || jobId);

  return (
    <section className="single-view">
      {notice ? <div className="automation-notice">{notice}</div> : null}
      <article className="panel full workflow-launcher">
        <div className="panel-header">
          <div>
            <h2>启动工作流</h2>
            <p>每个节点完成后写入 PostgreSQL，涉及消息和约面时暂停等待人工确认。</p>
          </div>
          <GitBranch size={20} />
        </div>
        <div className="workflow-controls">
          <label>
            <span>流程</span>
            <select
              value={workflowName}
              onChange={(event) => setWorkflowName(event.target.value as WorkflowRun["workflow_name"])}
            >
              {Object.entries(workflowLabels).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </label>
          <label>
            <span>候选人</span>
            <select
              disabled={!requiresCandidate}
              value={candidateId ?? ""}
              onChange={(event) => setCandidateId(Number(event.target.value) || undefined)}
            >
              <option value="">请选择</option>
              {candidates.filter((item) => item.id).map((candidate) => (
                <option key={candidate.id} value={candidate.id}>{candidate.name}</option>
              ))}
            </select>
          </label>
          <label>
            <span>岗位</span>
            <select
              disabled={!requiresJob}
              value={jobId ?? ""}
              onChange={(event) => setJobId(Number(event.target.value) || undefined)}
            >
              <option value="">请选择</option>
              {jobs.map((job) => <option key={job.id} value={job.id}>{job.title}</option>)}
            </select>
          </label>
          <button
            className="primary-button"
            disabled={!canStart || busy === "start"}
            onClick={() => onStart({
              workflow_name: workflowName,
              candidate_id: requiresCandidate ? candidateId : undefined,
              job_id: requiresJob ? jobId : undefined
            })}
            type="button"
          >
            <Play size={16} />
            {busy === "start" ? "启动中" : "启动"}
          </button>
          <button className="icon-button" onClick={onRefresh} title="刷新工作流" type="button">
            <RefreshCw size={16} />
          </button>
        </div>
      </article>

      <div className="workflow-layout">
        <article className="panel workflow-list-panel">
          <div className="panel-header">
            <div>
              <h2>运行记录</h2>
              <p>共 {runs.length} 条，最新记录显示在最上方。</p>
            </div>
          </div>
          <div className="workflow-list">
            {runs.length === 0 ? (
              <div className="empty-state">尚未启动工作流。</div>
            ) : runs.map((run) => (
              <div className="workflow-run-row" key={run.id}>
                <div>
                  <strong>{workflowLabels[run.workflow_name]}</strong>
                  <span>#{run.id} · {run.candidate_name ?? run.job_title ?? "系统任务"}</span>
                </div>
                <div>
                  <span className={`workflow-status status-${run.status}`}>
                    {statusLabels[run.status] ?? run.status}
                  </span>
                  <small>{nodeLabels[run.current_node ?? ""] ?? run.current_node ?? "已结束"}</small>
                </div>
                <div className="workflow-row-actions">
                  {run.status === "waiting_review" ? (
                    <>
                      <button
                        className="icon-button approve"
                        disabled={busy === `review:${run.id}`}
                        onClick={() => onReview(run.id, "approved")}
                        title="批准并继续"
                        type="button"
                      >
                        <Check size={16} />
                      </button>
                      <button
                        className="icon-button reject"
                        disabled={busy === `review:${run.id}`}
                        onClick={() => onReview(run.id, "rejected")}
                        title="拒绝并结束"
                        type="button"
                      >
                        <X size={16} />
                      </button>
                    </>
                  ) : null}
                  {run.status === "failed" ? (
                    <button
                      className="icon-button"
                      disabled={busy === `retry:${run.id}`}
                      onClick={() => onRetry(run.id)}
                      title="从失败节点重试"
                      type="button"
                    >
                      <RotateCcw size={16} />
                    </button>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        </article>

        <article className="panel workflow-trace-panel">
          <div className="panel-header">
            <div>
              <h2>最新执行轨迹</h2>
              <p>{selectedRun ? `工作流 #${selectedRun.id}` : "等待运行记录"}</p>
            </div>
          </div>
          <div className="workflow-trace">
            {selectedRun?.history.map((step, index) => (
              <div className="workflow-step" key={`${step.node}-${step.at}-${index}`}>
                <span className="workflow-step-index">{index + 1}</span>
                <div>
                  <strong>{nodeLabels[step.node] ?? step.node}</strong>
                  <small>
                    {step.status === "waiting_review" ? "等待处理 · " : ""}
                    {new Date(step.at).toLocaleString("zh-CN")}
                  </small>
                </div>
              </div>
            ))}
            {selectedRun?.error_message ? (
              <div className="workflow-error">{selectedRun.error_message}</div>
            ) : null}
            {!selectedRun ? <div className="empty-state">启动流程后可查看节点轨迹。</div> : null}
          </div>
        </article>
      </div>
    </section>
  );
}
