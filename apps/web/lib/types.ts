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
