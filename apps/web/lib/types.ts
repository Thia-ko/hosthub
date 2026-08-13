export type InstanceStatus = "active" | "paused" | "archived";

export interface Instance {
  id: string;
  name: string;
  slug: string;
  status: InstanceStatus;
  owner_user_id: string;
  owner_email: string;
  created_at: string;
}

export interface InstanceDetail extends Instance {
  ai_assist_daily_token_limit: number | null;
  webhook_token: string;
}

export interface InstanceCreateResponse {
  instance: InstanceDetail;
  client_email: string;
  generated_password: string | null;
}

export type PromptVersionSource = "manual" | "ai_assist" | "template";

export interface PromptVersionSummary {
  id: string;
  version_number: number;
  source: PromptVersionSource;
  change_note: string | null;
  created_by_user_id: string;
  created_at: string;
}

export interface PromptVersionDetail extends PromptVersionSummary {
  content: string;
}

export interface PromptVersionDiffResponse {
  from: { version_number: number; content: string };
  to: { version_number: number; content: string };
}

export interface AiAssistUsage {
  used_today: number;
  limit: number;
  resets_at: string;
}

export interface AiAssistSuggestResponse {
  ai_assist_request_id: string;
  suggested_content: string;
  prompt_tokens: number;
  completion_tokens: number;
}

export interface WebhookEvent {
  id: string;
  payload_json: unknown;
  received_at: string;
}

export interface DashboardSummary {
  date: string;
  total_events: number;
  events_by_hour: { hour: number; count: number }[];
  prompt_versions_count: number;
  ai_assist_usage_today: number;
  ai_assist_daily_limit: number;
}
