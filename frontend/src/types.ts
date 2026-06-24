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
  profile_summary?: string | null;
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

export type CandidateProfile = {
  id: number;
  candidate_id: number;
  skills: string[];
  highlights: string[];
  risks: string[];
  profile_json: {
    projects?: string[];
    work_experience?: number;
    parser?: string;
    [key: string]: unknown;
  };
  created_at: string;
  updated_at: string;
};

export type Resume = {
  id: number;
  candidate_id: number;
  original_filename?: string | null;
  file_path?: string | null;
  parse_status: string;
  created_at: string;
  updated_at: string;
};

export type CandidateScore = {
  id: number;
  candidate_id: number;
  job_id: number;
  total_score: string;
  dimensions: Record<string, {
    score?: number;
    max?: number;
    matched?: string[];
    reason?: string;
    [key: string]: unknown;
  }>;
  rationale?: string | null;
  created_at: string;
  updated_at: string;
};

export type CandidateDetail = {
  candidate: Candidate;
  profile?: CandidateProfile | null;
  resumes: Resume[];
  scores: CandidateScore[];
};

export type ResumeProcessResult = {
  resume: Resume;
  candidate: Candidate;
  profile: CandidateProfile;
  score?: CandidateScore | null;
  parser: string;
  text_length: number;
  ocr_used: boolean;
};

export type Recommendation = {
  id: number;
  job_id: number;
  job_title: string;
  candidate_id: number;
  candidate_name: string;
  recommendation_date: string;
  rank: number;
  total_score: number;
  reason?: string | null;
  highlights: string[];
  risks: string[];
  action_id?: number | null;
  action_status?: string | null;
  interview_draft?: string | null;
};

export type RecommendationRun = {
  recommendation_date: string;
  jobs_processed: number;
  recommendations_created: number;
  drafts_created: number;
  items: Recommendation[];
};

export type ActionQueueEntry = {
  id: number;
  candidate_id?: number | null;
  candidate_name?: string | null;
  job_id?: number | null;
  job_title?: string | null;
  action_type: string;
  status: string;
  risk_level: string;
  draft_message?: string | null;
  payload: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};
