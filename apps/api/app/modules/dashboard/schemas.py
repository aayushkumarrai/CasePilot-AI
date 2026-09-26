from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.modules.cases.schemas import CaseResponse


class ActivityResponse(BaseModel):
    id: UUID
    action: str
    actor_type: str
    details: dict
    created_at: datetime


class DashboardMetrics(BaseModel):
    total_cases: int
    draft_cases: int
    in_review: int
    ready_cases: int
    pending_tasks: int = 0
    unresolved_issues: int = 0


class DashboardResponse(BaseModel):
    metrics: DashboardMetrics
    cases: list[CaseResponse]
    recent_activity: list[ActivityResponse]
