import type {
  AuditLog,
  BrowserStatus,
  Candidate,
  ChatScanResult,
  Job,
  PageResponse
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: init?.body ? { "Content-Type": "application/json", ...init.headers } : init?.headers,
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
