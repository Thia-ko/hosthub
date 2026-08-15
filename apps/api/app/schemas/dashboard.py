from datetime import date as date_type

from pydantic import BaseModel


class HourlyCount(BaseModel):
    hour: int
    count: int


class DashboardSummary(BaseModel):
    date: date_type
    total_messages: int
    messages_by_hour: list[HourlyCount]
    prompt_versions_count: int
    ai_assist_usage_today: int
    ai_assist_daily_limit: int
    csat_average: float | None
    csat_response_count: int


class AdminDashboardOverview(BaseModel):
    total_instances: int
    active_instances: int
    paused_instances: int
    archived_instances: int
    pending_prompts: int
    escalated_threads: int
    messages_today: int
    ai_tokens_used_today: int
