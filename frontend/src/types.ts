export type Metric = {
  label: string;
  value: string;
  detail: string;
};

export type PipelineStage = {
  label: string;
  count: number;
};

export type Candidate = {
  id?: number;
  boss_uid?: string | null;
  source?: string;
  name: string;
  current_role?: string | null;
  education_level?: string | null;
  school?: string | null;
  major?: string | null;
  graduation_year?: number | null;
  candidate_type?: string | null;
  status: string;
  raw_card?: Record<string, unknown>;
};

export type ActionItem = {
  title: string;
  candidate: string;
  risk: string;
  time: string;
};

export type RunEvent = {
  label: string;
  status: "ready" | "planned" | "warning";
  detail: string;
};

export type Job = {
  id: number;
  title: string;
  city?: string | null;
  keywords: string[];
  is_active: boolean;
};

export type PageResponse<T> = {
  items: T[];
  total: number;
  limit: number;
  offset: number;
};
