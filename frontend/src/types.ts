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

export type BrowserState = "stopped" | "starting" | "ready" | "login_required" | "blocked" | "error";

export type BrowserStatus = {
  state: BrowserState;
  running: boolean;
  current_url?: string | null;
  page_title?: string | null;
  detail?: string | null;
};

export type ChatSummary = {
  name: string;
  preview?: string | null;
  unread_count: number;
  href?: string | null;
  raw_text: string;
};

export type AttachmentInfo = {
  filename?: string | null;
  attachment_type: string;
  preview_text?: string | null;
  href?: string | null;
};

export type ChatDetail = {
  candidate_name?: string | null;
  messages: string[];
  attachments: AttachmentInfo[];
};

export type ChatScanResult = {
  scanned_at: string;
  page_url: string;
  conversations: ChatSummary[];
  detail?: ChatDetail | null;
  screenshot_path?: string | null;
};

export type AuditLog = {
  id: number;
  action_type: string;
  status: string;
  detail?: string | null;
  screenshot_path?: string | null;
  payload: Record<string, unknown>;
  created_at: string;
};
