import type { Candidate, Job, PageResponse } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api";

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

export type DashboardData = {
  databaseStatus: string;
  jobs: PageResponse<Job>;
  candidates: PageResponse<Candidate>;
};

export async function fetchDashboardData(): Promise<DashboardData> {
  const [databaseHealth, jobs, candidates] = await Promise.all([
    request<{ status: string }>("/health/database"),
    request<PageResponse<Job>>("/jobs?limit=20"),
    request<PageResponse<Candidate>>("/candidates?limit=20")
  ]);

  return {
    databaseStatus: databaseHealth.status,
    jobs,
    candidates
  };
}

