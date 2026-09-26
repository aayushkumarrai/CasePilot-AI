from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

OutputRef = Annotated[str, Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9._:-]+$")]
CitationTargetType = Literal[
    "case_summary",
    "document_summary",
    "case_field",
    "case_party",
    "timeline_event",
    "finding",
    "task",
]
CASE_SUMMARY_REF = "case_summary"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AnalysisPrompt(StrictModel):
    uploaded_evidence: Annotated[str, Field(min_length=1, max_length=200_000)]
    lawyer_context: Annotated[str | None, Field(max_length=4000)] = None

    @field_validator("lawyer_context")
    @classmethod
    def empty_context_is_none(cls, value: str | None) -> str | None:
        return value or None


AnalysisRunStatus = Literal["queued", "processing", "completed", "failed"]


class StartAnalysisRequest(StrictModel):
    """The optional lawyer assertion saved only when explicit analysis starts."""

    lawyer_context: Annotated[str | None, Field(max_length=4000)] = None

    @field_validator("lawyer_context")
    @classmethod
    def empty_context_is_none(cls, value: str | None) -> str | None:
        return value or None


class AnalysisRunResponse(BaseModel):
    """Safe public lifecycle metadata; never includes prompt or output content."""

    id: UUID
    status: AnalysisRunStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None


class AnalysisStatusResponse(BaseModel):
    run: AnalysisRunResponse | None = None
    has_completed_outputs: bool


class Citation(StrictModel):
    target_type: CitationTargetType
    target_ref: OutputRef
    passage_id: UUID
    quote: Annotated[str, Field(min_length=1, max_length=1000)]


class DocumentSummary(StrictModel):
    ref: OutputRef
    document_id: UUID
    summary: Annotated[str, Field(min_length=1, max_length=10_000)]


class CaseField(StrictModel):
    ref: OutputRef
    field_key: Annotated[str, Field(min_length=1, max_length=100)]
    label: Annotated[str, Field(min_length=1, max_length=160)]
    value: Annotated[str, Field(min_length=1, max_length=10_000)]
    confidence: Annotated[float, Field(ge=0, le=1)]


class CaseParty(StrictModel):
    ref: OutputRef
    name: Annotated[str, Field(min_length=1, max_length=200)]
    role: Annotated[str, Field(min_length=1, max_length=100)]


class TimelineEvent(StrictModel):
    ref: OutputRef
    event_date_text: Annotated[str, Field(min_length=1, max_length=100)]
    date_confidence: Literal["exact", "month", "year", "unknown"]
    title: Annotated[str, Field(min_length=1, max_length=200)]
    description: Annotated[str, Field(min_length=1, max_length=10_000)]


class Finding(StrictModel):
    ref: OutputRef
    kind: Literal["conflict", "gap"]
    title: Annotated[str, Field(min_length=1, max_length=200)]
    description: Annotated[str, Field(min_length=1, max_length=10_000)]


class ProposedTask(StrictModel):
    ref: OutputRef
    finding_ref: OutputRef | None = None
    title: Annotated[str, Field(min_length=1, max_length=200)]
    description: Annotated[str, Field(min_length=1, max_length=10_000)]


class AnalysisResult(StrictModel):
    case_summary: Annotated[str, Field(min_length=1, max_length=10_000)]
    document_summaries: Annotated[list[DocumentSummary], Field(max_length=50)] = Field(default_factory=list)
    case_fields: Annotated[list[CaseField], Field(max_length=50)] = Field(default_factory=list)
    case_parties: Annotated[list[CaseParty], Field(max_length=50)] = Field(default_factory=list)
    timeline_events: Annotated[list[TimelineEvent], Field(max_length=50)] = Field(default_factory=list)
    findings: Annotated[list[Finding], Field(max_length=50)] = Field(default_factory=list)
    tasks: Annotated[list[ProposedTask], Field(max_length=50)] = Field(default_factory=list)
    citations: Annotated[list[Citation], Field(max_length=250)] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_references(self) -> "AnalysisResult":
        refs = {
            "case_summary": {CASE_SUMMARY_REF},
            "document_summary": {item.ref for item in self.document_summaries},
            "case_field": {item.ref for item in self.case_fields},
            "case_party": {item.ref for item in self.case_parties},
            "timeline_event": {item.ref for item in self.timeline_events},
            "finding": {item.ref for item in self.findings},
            "task": {item.ref for item in self.tasks},
        }
        for target_type, values in refs.items():
            # The case summary has one fixed internal reference rather than a
            # collection of generated output records.
            if target_type == "case_summary":
                continue
            if len(values) != sum(1 for item in self._items_for_type(target_type)):
                raise ValueError(f"Duplicate {target_type} refs are not allowed")
        for citation in self.citations:
            if citation.target_ref not in refs[citation.target_type]:
                raise ValueError("Citation target_ref does not exist in the response")
        for task in self.tasks:
            if task.finding_ref and task.finding_ref not in refs["finding"]:
                raise ValueError("Task finding_ref does not exist in the response")
        if len(self.citations) > 5 * sum(len(values) for values in refs.values()):
            raise ValueError("Each output item may have at most five citations")
        return self

    def _items_for_type(self, target_type: CitationTargetType) -> list[StrictModel]:
        return {
            "case_summary": [],
            "document_summary": self.document_summaries,
            "case_field": self.case_fields,
            "case_party": self.case_parties,
            "timeline_event": self.timeline_events,
            "finding": self.findings,
            "task": self.tasks,
        }[target_type]
