import type {
  AuditLog,
  ActionQueueEntry,
  AiHealth,
  Candidate,
  CandidateDeleteResult,
  ChatLoopStatus,
  CandidateDetail,
  ExtensionCommand,
  ExtensionCommandType,
  ExtensionStatus,
  GreetingQuota,
  Job,
  PageResponse,
  Recommendation,
  RecommendationRun,
  ResumeProcessResult,
  WorkflowRun,
  WorkflowStartInput
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const isFormData = init?.body instanceof FormData;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: init?.body && !isFormData ? { "Content-Type": "application/json", ...init.headers } : init?.headers,
    ...init
  });
  if (!response.ok) {
    const errorBody = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(errorBody?.detail ?? `${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

export type DashboardData = {
  databaseStatus: string;
  aiHealth: AiHealth;
  jobs: PageResponse<Job>;
  candidates: PageResponse<Candidate>;
  extension: ExtensionStatus;
  auditLogs: PageResponse<AuditLog>;
  recommendations: Recommendation[];
  actions: PageResponse<ActionQueueEntry>;
  greetingQuota: GreetingQuota;
  workflows: PageResponse<WorkflowRun>;
  chatLoop: ChatLoopStatus;
};

export async function fetchDashboardData(): Promise<DashboardData> {
  const [
    databaseHealth,
    aiHealth,
    jobs,
    candidates,
    extension,
    auditLogs,
    recommendations,
    actions,
    greetingQuota,
    workflows,
    chatLoop
  ] = await Promise.all([
    request<{ status: string }>("/health/database"),
    request<AiHealth>("/health/ai"),
    request<PageResponse<Job>>("/jobs?limit=20"),
    request<PageResponse<Candidate>>("/candidates?limit=20"),
    request<ExtensionStatus>("/extension/status"),
    request<PageResponse<AuditLog>>("/audit-logs?limit=30"),
    request<Recommendation[]>("/recommendations/today"),
    request<PageResponse<ActionQueueEntry>>("/actions?limit=50"),
    request<GreetingQuota>("/quota/greetings"),
    request<PageResponse<WorkflowRun>>("/workflows?limit=50"),
    request<ChatLoopStatus>("/automation/chat-loop/status")
  ]);

  return {
    databaseStatus: databaseHealth.status,
    aiHealth,
    jobs,
    candidates,
    extension,
    auditLogs,
    recommendations,
    actions,
    greetingQuota,
    workflows,
    chatLoop
  };
}

export function fetchAuditLogs(
  limit = 12,
  offset = 0,
  status?: string
): Promise<PageResponse<AuditLog>> {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset)
  });
  if (status && status !== "all") {
    params.set("status", status);
  }
  return request<PageResponse<AuditLog>>(`/audit-logs?${params.toString()}`);
}

export function fetchAuditLog(auditLogId: number): Promise<AuditLog> {
  return request<AuditLog>(`/audit-logs/${auditLogId}`);
}

export function startChatLoop(): Promise<ChatLoopStatus> {
  return request<ChatLoopStatus>("/automation/chat-loop/start", { method: "POST" });
}

export function pauseChatLoop(): Promise<ChatLoopStatus> {
  return request<ChatLoopStatus>("/automation/chat-loop/pause", { method: "POST" });
}

export function queueExtensionCommand(
  commandType: ExtensionCommandType,
  payload: Record<string, unknown> = {}
): Promise<ExtensionCommand> {
  return request<ExtensionCommand>("/extension/commands", {
    method: "POST",
    body: JSON.stringify({ command_type: commandType, payload })
  });
}

export function controlExtensionCommand(
  commandId: number,
  control: "running" | "paused" | "stopped"
): Promise<ExtensionCommand> {
  return request<ExtensionCommand>(`/extension/commands/${commandId}/control`, {
    method: "POST",
    body: JSON.stringify({ control })
  });
}

export function fetchCandidateDetail(candidateId: number): Promise<CandidateDetail> {
  return request<CandidateDetail>(`/candidates/${candidateId}/detail`);
}

export function deleteCandidate(candidateId: number): Promise<CandidateDeleteResult> {
  return request<CandidateDeleteResult>(`/candidates/${candidateId}?confirm=true`, {
    method: "DELETE"
  });
}

export function uploadResume(
  candidateId: number,
  file: File,
  jobId?: number
): Promise<ResumeProcessResult> {
  const formData = new FormData();
  formData.append("file", file);
  const query = jobId ? `?job_id=${jobId}` : "";
  return request<ResumeProcessResult>(`/candidates/${candidateId}/resumes${query}`, {
    method: "POST",
    body: formData
  });
}

export function generateRecommendations(
  jobId?: number,
  topN = 5
): Promise<RecommendationRun> {
  return request<RecommendationRun>("/recommendations/generate", {
    method: "POST",
    body: JSON.stringify({
      job_id: jobId,
      top_n: topN,
      create_interview_drafts: true
    })
  });
}

export function decideAction(
  actionId: number,
  decision: "approve" | "reject",
  note?: string
): Promise<ActionQueueEntry> {
  return request<ActionQueueEntry>(`/actions/${actionId}/${decision}`, {
    method: "POST",
    body: JSON.stringify({ note: note ?? null })
  });
}

export function startWorkflow(input: WorkflowStartInput): Promise<WorkflowRun> {
  return request<WorkflowRun>("/workflows", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export function reviewWorkflow(
  runId: number,
  decision: "approved" | "rejected",
  note?: string
): Promise<WorkflowRun> {
  return request<WorkflowRun>(`/workflows/${runId}/review`, {
    method: "POST",
    body: JSON.stringify({ decision, note: note ?? null })
  });
}

export function retryWorkflow(runId: number): Promise<WorkflowRun> {
  return request<WorkflowRun>(`/workflows/${runId}/retry`, { method: "POST" });
}
