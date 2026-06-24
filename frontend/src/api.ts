import type {
  AuditLog,
  BrowserStatus,
  Candidate,
  CandidateDetail,
  ChatScanResult,
  Job,
  PageResponse,
  ResumeProcessResult
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
  jobs: PageResponse<Job>;
  candidates: PageResponse<Candidate>;
  browser: BrowserStatus;
  auditLogs: PageResponse<AuditLog>;
};

export async function fetchDashboardData(): Promise<DashboardData> {
  const [databaseHealth, jobs, candidates, browser, auditLogs] = await Promise.all([
    request<{ status: string }>("/health/database"),
    request<PageResponse<Job>>("/jobs?limit=20"),
    request<PageResponse<Candidate>>("/candidates?limit=20"),
    request<BrowserStatus>("/automation/browser/status"),
    request<PageResponse<AuditLog>>("/audit-logs?limit=30")
  ]);

  return {
    databaseStatus: databaseHealth.status,
    jobs,
    candidates,
    browser,
    auditLogs
  };
}

export function startBrowser(): Promise<BrowserStatus> {
  return request<BrowserStatus>("/automation/browser/start", { method: "POST" });
}

export function stopBrowser(): Promise<BrowserStatus> {
  return request<BrowserStatus>("/automation/browser/stop", { method: "POST" });
}

export function scanChats(limit = 10): Promise<ChatScanResult> {
  return request<ChatScanResult>("/automation/chat/scan", {
    method: "POST",
    body: JSON.stringify({ limit, capture_screenshot: true })
  });
}

export function openChat(candidateName: string): Promise<ChatScanResult> {
  return request<ChatScanResult>("/automation/chat/open", {
    method: "POST",
    body: JSON.stringify({ candidate_name: candidateName, capture_screenshot: true })
  });
}

export function fetchCandidateDetail(candidateId: number): Promise<CandidateDetail> {
  return request<CandidateDetail>(`/candidates/${candidateId}/detail`);
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
