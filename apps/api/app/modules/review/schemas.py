from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.cases.schemas import CaseResponse


class CitationResponse(BaseModel):
    document_id: UUID
    document_name: str
    passage_id: UUID
    passage_label: str
    page_number: int | None = None
    quote: str


class CompletedRunResponse(BaseModel):
    id: UUID
    completed_at: datetime | None = None


class DocumentSummaryResponse(BaseModel):
    id: UUID
    document_id: UUID
    document_name: str
    summary: str
    citations: list[CitationResponse] = Field(default_factory=list)


class ReviewFieldResponse(BaseModel):
    id: UUID
    field_key: str
    label: str
    value: str
    status: Literal["pending", "confirmed", "rejected"]
    citations: list[CitationResponse] = Field(default_factory=list)


class ReviewPartyResponse(BaseModel):
    id: UUID
    name: str
    role: str
    status: Literal["pending", "confirmed", "rejected"]
    citations: list[CitationResponse] = Field(default_factory=list)


class TimelineEventResponse(BaseModel):
    id: UUID
    event_date_text: str
    date_confidence: Literal["exact", "month", "year", "unknown"]
    title: str
    description: str
    citations: list[CitationResponse] = Field(default_factory=list)


class FindingResponse(BaseModel):
    id: UUID
    kind: Literal["conflict", "gap"]
    title: str
    description: str
    citations: list[CitationResponse] = Field(default_factory=list)


class ReviewTaskResponse(BaseModel):
    id: UUID
    finding_id: UUID | None = None
    title: str
    description: str
    status: str
    citations: list[CitationResponse] = Field(default_factory=list)


class FieldGroupsResponse(BaseModel):
    pending: list[ReviewFieldResponse] = Field(default_factory=list)
    confirmed: list[ReviewFieldResponse] = Field(default_factory=list)
    rejected: list[ReviewFieldResponse] = Field(default_factory=list)


class OverviewCountsResponse(BaseModel):
    document_summaries: int = 0
    pending_fields: int = 0
    confirmed_fields: int = 0
    rejected_fields: int = 0
    parties: int = 0
    issues: int = 0
    pending_tasks: int = 0


class OverviewResponse(BaseModel):
    case: CaseResponse
    analysis_run: CompletedRunResponse | None = None
    lawyer_context: str | None = None
    case_summary: str | None = None
    case_summary_citations: list[CitationResponse] = Field(default_factory=list)
    document_summaries: list[DocumentSummaryResponse] = Field(default_factory=list)
    fields: FieldGroupsResponse = Field(default_factory=FieldGroupsResponse)
    parties: list[ReviewPartyResponse] = Field(default_factory=list)
    latest_issues: list[FindingResponse] = Field(default_factory=list)
    pending_tasks: list[ReviewTaskResponse] = Field(default_factory=list)
    counts: OverviewCountsResponse = Field(default_factory=OverviewCountsResponse)


class ActivityResponse(BaseModel):
    id: UUID
    action: str
    actor_type: str
    details: dict
    created_at: datetime
