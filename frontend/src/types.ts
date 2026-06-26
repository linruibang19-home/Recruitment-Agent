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

export type AiHealth = {
  status: string;
  ocr: {
    provider: string;
    available: boolean;
    executable?: string | null;
    tessdata_dir?: string | null;
    languages: string;
  };
  llm: {
    provider: string;
    enabled: boolean;
    configured: boolean;
    model: string;
    base_url: string;
  };
};

export type BrowserState = "stopped" | "starting" | "ready" | "login_required" | "blocked" | "error";

export type BrowserStatus = {
  state: BrowserState;
  running: boolean;
  current_url?: string | null;
  page_title?: string | null;
  detail?: string | null;
  consecutive_failures: number;
  last_error?: string | null;
};

export type ExtensionCommandType =
  | "scan_chats"
  | "scan_chat_details"
  | "request_resumes_batch"
  | "read_current_chat"
  | "scan_talents";

export type ExtensionCommand = {
  id: number;
  extension_id?: string | null;
  command_type: ExtensionCommandType;
  status: "queued" | "running" | "completed" | "failed";
  payload: Record<string, unknown>;
  result: Record<string, unknown>;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
  claimed_at?: string | null;
  completed_at?: string | null;
};

export type ExtensionStatus = {
  connected: boolean;
  extension_id?: string | null;
  status: string;
  page_url?: string | null;
  page_title?: string | null;
  page_type?: string | null;
  last_seen_at?: string | null;
  recent_commands: ExtensionCommand[];
};

export type CandidateDeleteResult = {
  candidate_id: number;
  deleted_resume_files: number;
  deleted: boolean;
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
  entity_type?: string | null;
  entity_id?: number | null;
  status: string;
  detail?: string | null;
  screenshot_path?: string | null;
  payload: Record<string, unknown>;
  created_at: string;
};

export type ChatLoopStatus = {
  running: boolean;
  enabled: boolean;
  next_enqueue_at?: string | null;
  last_enqueue_at?: string | null;
  last_command_id?: number | null;
  last_message: string;
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

export type GreetingQuota = {
  quota_date: string;
  used_count: number;
  max_count: number;
  pending_count: number;
  approved_count: number;
  available_count: number;
};

export type TalentCard = {
  boss_uid: string;
  name: string;
  age?: number | null;
  city?: string | null;
  education_level?: string | null;
  school?: string | null;
  major?: string | null;
  graduation_year?: number | null;
  candidate_type?: string | null;
  experience?: string | null;
  intention?: string | null;
  expected_salary?: string | null;
  skills: string[];
  href?: string | null;
  raw_text: string;
};

export type TalentScanResult = {
  scanned_at: string;
  page_url: string;
  total_read: number;
  matched_count: number;
  duplicate_count: number;
  drafted_count: number;
  cards: TalentCard[];
  screenshot_path?: string | null;
};

export type TalentScanInput = {
  job_id: number;
  city?: string;
  experience: string[];
  education: string[];
  intentions: string[];
  salary_keywords: string[];
  required_keywords: string[];
  limit: number;
  capture_screenshot: boolean;
};

export type WorkflowStep = {
  node: string;
  status: string;
  at: string;
  candidate_id?: number | null;
  job_id?: number | null;
  action_id?: number | null;
};

export type WorkflowRun = {
  id: number;
  workflow_name: "chat_resume" | "recommend_talent" | "daily_recommendation";
  status: string;
  current_node?: string | null;
  candidate_id?: number | null;
  candidate_name?: string | null;
  job_id?: number | null;
  job_title?: string | null;
  action_id?: number | null;
  review_note?: string | null;
  history: WorkflowStep[];
  error_message?: string | null;
  created_at: string;
  updated_at: string;
};

export type WorkflowStartInput = {
  workflow_name: WorkflowRun["workflow_name"];
  candidate_id?: number;
  job_id?: number;
  action_id?: number;
  payload?: Record<string, unknown>;
};
