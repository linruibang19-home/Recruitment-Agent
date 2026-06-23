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
  name: string;
  role: string;
  education: string;
  match: number;
  status: string;
  skills: string[];
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

