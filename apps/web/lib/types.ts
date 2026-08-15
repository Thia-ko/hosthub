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
  whatsapp_instance_name: string | null;
  auto_generate_prompt: boolean;
  auto_gen_conversation_threshold: number;
  auto_gen_interval: "off" | "1d" | "3d" | "1w";
  last_auto_gen_at: string | null;
}

export type OutboundWebhookEvent = "message_received" | "thread_escalated" | "prompt_pending";

export interface OutboundWebhookSubscription {
  id: string;
  url: string;
  events: OutboundWebhookEvent[];
  active: boolean;
  created_at: string;
}

export interface InstanceCreateResponse {
  instance: InstanceDetail;
  client_email: string;
  generated_password: string | null;
}

export interface ClientPasswordResetOut {
  client_email: string;
  generated_password: string;
}

export type PromptVersionSource = "manual" | "ai_assist" | "template" | "auto_generated";

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

export interface SandboxMessage {
  role: "user" | "assistant";
  content: string;
}

export interface AiAssistSandboxReplyResponse {
  reply: string;
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
  total_messages: number;
  messages_by_hour: { hour: number; count: number }[];
  prompt_versions_count: number;
  ai_assist_usage_today: number;
  ai_assist_daily_limit: number;
}

export interface PromptTemplate {
  id: string;
  niche: string;
  title: string;
  description: string;
  icon_emoji: string | null;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface ThemeSettings {
  light_primary_color: string;
  light_secondary_color: string;
  dark_primary_color: string;
  dark_secondary_color: string;
}

export interface AiSettings {
  base_url: string;
  model: string;
  transcribe_model: string;
  api_key_source: "database" | "env" | "none";
  updated_at: string | null;
}

export type MessageDirection = "inbound" | "outbound";
export type MessageKind = "text" | "audio" | "image";

export interface ConversationMessage {
  id: string;
  direction: MessageDirection;
  kind: MessageKind;
  text: string;
  media_url: string | null;
  created_at: string;
}

export interface ConversationSummary {
  sender_number: string;
  last_message_text: string;
  last_message_kind: MessageKind;
  last_direction: MessageDirection;
  last_message_at: string;
  message_count: number;
  ai_paused: boolean;
  escalated: boolean;
}

export interface ExtractedData {
  id: string;
  category: string;
  key: string;
  value: string;
  confidence: number;
  occurrences: number;
  source: string | null;
  created_at: string;
  updated_at: string;
}

export interface FaqItem {
  id: string;
  question: string;
  answer: string;
  category: string;
  asked_by: string;
  frequency: number;
  last_seen_at: string;
  created_at: string;
  updated_at: string;
}

export interface AttendantPattern {
  id: string;
  pattern_type: string;
  description: string;
  examples: string[];
  frequency: number;
  created_at: string;
  updated_at: string;
}

export interface AnalyticsOverview {
  analyzed_conversations: number;
  total_faqs: number;
  total_extracted: number;
  total_patterns: number;
  pending_prompt: boolean;
}

export interface AdminDashboardOverview {
  total_instances: number;
  active_instances: number;
  paused_instances: number;
  archived_instances: number;
  pending_prompts: number;
  escalated_threads: number;
  messages_today: number;
  ai_tokens_used_today: number;
}

export interface DataReadiness {
  analyzed_conversations: number;
  total_faqs: number;
  total_extracted: number;
  total_patterns: number;
  ready: boolean;
}

export interface GeneratedPrompt {
  id: string;
  version_number: number;
  content: string;
  change_note: string | null;
  created_at: string;
}
