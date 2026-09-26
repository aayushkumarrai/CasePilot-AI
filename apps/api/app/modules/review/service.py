from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from app.core.dependencies import CurrentUser
from app.integrations.supabase_gateway import SupabaseGateway
from app.modules.cases.schemas import CaseResponse

from .repository import ReviewRepository
from .schemas import (
    ActivityResponse,
    CompletedRunResponse,
    DocumentSummaryResponse,
    FieldGroupsResponse,
    FindingResponse,
    OverviewCountsResponse,
    OverviewResponse,
    ReviewFieldResponse,
    ReviewPartyResponse,
    ReviewTaskResponse,
    TimelineEventResponse,
)


def _case_response(case: dict[str, Any]) -> CaseResponse:
    return CaseResponse.model_validate(case)


def _date_sort_value(event: dict[str, Any]) -> tuple[int, date, str, str]:
    """Parse only for ordering; retain the original evidence text in the response."""
    text = (event.get("event_date_text") or "").strip()
    confidence = event.get("date_confidence")
    parsed: date | None = None
    formats = {
        "exact": ("%Y-%m-%d", "%d %B %Y", "%B %d, %Y", "%B %d %Y"),
        "month": ("%B %Y",),
    }
    if confidence == "year" and text.isdigit() and len(text) == 4:
        try:
            parsed = date(int(text), 1, 1)
        except ValueError:
            parsed = None
    elif confidence in formats:
        for fmt in formats[confidence]:
            try:
                parsed = datetime.strptime(text, fmt).date()
                break
            except ValueError:
                continue
    if parsed is None:
        return (1, date.max, event.get("created_at", ""), str(event["id"]))
    return (0, parsed, event.get("created_at", ""), str(event["id"]))


async def _review_data(gateway: SupabaseGateway, user: CurrentUser, case_id: UUID):
    repository = ReviewRepository(gateway, user)
    case = await repository.active_case(case_id)
    run = await repository.latest_completed_run(case_id)
    if not run:
        return repository, case, None, {}, [], {}
    outputs = await repository.outputs(UUID(str(run["id"])))
    # A narrow later run can omit parties. Fall back to the newest completed
    # evidence-grounded party extraction for this case before resolving citations.
    if not outputs["case_parties"]:
        outputs["case_parties"] = await repository.latest_available_parties(case_id)
    summary_citations, citations = await repository.resolve_citations(UUID(str(run["id"])), outputs)
    return repository, case, run, outputs, summary_citations, citations


def _item_citations(citations: dict, table: str, item: dict) -> list[dict]:
    return citations.get((table, str(item["id"])), [])


async def get_overview(gateway: SupabaseGateway, user: CurrentUser, case_id: UUID) -> OverviewResponse:
    repository, case, run, outputs, summary_citations, citations = await _review_data(gateway, user, case_id)
    base = {"case": _case_response(case), "lawyer_context": case.get("lawyer_context")}
    if not run:
        return OverviewResponse(**base)
    document_names = await repository.document_names([str(x["document_id"]) for x in outputs["document_summaries"]])
    summaries = [
        DocumentSummaryResponse(
            id=row["id"], document_id=row["document_id"], document_name=document_names.get(str(row["document_id"]), "Document"),
            summary=row["summary"], citations=_item_citations(citations, "document_summaries", row),
        ) for row in outputs["document_summaries"]
    ]
    fields = {status: [] for status in ("pending", "confirmed", "rejected")}
    for row in outputs["case_fields"]:
        fields[row["status"]].append(ReviewFieldResponse(**row, citations=_item_citations(citations, "case_fields", row)))
    parties = [ReviewPartyResponse(**row, citations=_item_citations(citations, "case_parties", row)) for row in outputs["case_parties"]]
    issues = [FindingResponse(**row, citations=_item_citations(citations, "findings", row)) for row in outputs["findings"]]
    tasks = [ReviewTaskResponse(**row, citations=_item_citations(citations, "tasks", row)) for row in outputs["tasks"] if row["status"] == "proposed"]
    return OverviewResponse(
        **base,
        analysis_run=CompletedRunResponse(id=run["id"], completed_at=run["completed_at"]),
        case_summary=run.get("case_summary"), case_summary_citations=summary_citations,
        document_summaries=summaries, fields=FieldGroupsResponse(**fields), parties=parties,
        latest_issues=issues, pending_tasks=tasks,
        counts=OverviewCountsResponse(document_summaries=len(summaries), pending_fields=len(fields["pending"]), confirmed_fields=len(fields["confirmed"]), rejected_fields=len(fields["rejected"]), parties=len(parties), issues=len(issues), pending_tasks=len(tasks)),
    )


async def get_timeline(gateway: SupabaseGateway, user: CurrentUser, case_id: UUID) -> list[TimelineEventResponse]:
    _, _, run, outputs, _, citations = await _review_data(gateway, user, case_id)
    if not run:
        return []
    return [TimelineEventResponse(**row, citations=_item_citations(citations, "timeline_events", row)) for row in sorted(outputs["timeline_events"], key=_date_sort_value)]


async def get_issues(gateway: SupabaseGateway, user: CurrentUser, case_id: UUID) -> list[FindingResponse]:
    _, _, run, outputs, _, citations = await _review_data(gateway, user, case_id)
    if not run:
        return []
    return [FindingResponse(**row, citations=_item_citations(citations, "findings", row)) for row in outputs["findings"]]


async def get_tasks(gateway: SupabaseGateway, user: CurrentUser, case_id: UUID) -> list[ReviewTaskResponse]:
    _, _, run, outputs, _, citations = await _review_data(gateway, user, case_id)
    if not run:
        return []
    return [ReviewTaskResponse(**row, citations=_item_citations(citations, "tasks", row)) for row in outputs["tasks"]]


async def get_activity(gateway: SupabaseGateway, user: CurrentUser, case_id: UUID) -> list[ActivityResponse]:
    repository = ReviewRepository(gateway, user)
    await repository.active_case(case_id)
    return [ActivityResponse(**row) for row in await repository.activity(case_id)]
