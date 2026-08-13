from datetime import date as date_type

from pydantic import BaseModel


class HourlyCount(BaseModel):
    hour: int
    count: int


class DashboardSummary(BaseModel):
    date: date_type
    total_events: int
    events_by_hour: list[HourlyCount]
    prompt_versions_count: int
    ai_assist_usage_today: int
    ai_assist_daily_limit: int
