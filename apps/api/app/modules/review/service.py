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
    formats = {"exact": ("%Y-%m-%d", "%d %B %Y", "%B %d, %Y", "%B %d %Y"), "month": ("%B %Y",)}
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
    # A narrow later run can omit parties. Keep the newest cited extraction visible.
    if not outputs["case_parties"]:
        outputs["case_parties"] = await repository.latest_available_parties(case_id)
    summary_citations, citations = await repository.resolve_citations(UUID(str(run["id"])), outputs)
    return repository, case, run, outputs, summary_citations, citations


def _item_citations(citations: dict, table: str, item: dict) -> list[dict]:
    return citations.get((table, str(item["id"])), [])


def _field_response(row: dict[str, Any], citations: list[dict]) -> ReviewFieldResponse:
    suggested = row["value"]
    reviewed = row.get("reviewed_value")
    return ReviewFieldResponse(
        id=row["id"], field_key=row["field_key"], label=row["label"], suggested_value=suggested,
        reviewed_value=reviewed, value=reviewed or suggested, status=row["status"], reviewed_at=row.get("reviewed_at"), citations=citations,
    )


def _party_response(row: dict[str, Any], citations: list[dict]) -> ReviewPartyResponse:
    suggested_name, suggested_role = row["name"], row["role"]
    reviewed_name, reviewed_role = row.get("reviewed_name"), row.get("reviewed_role")
    return ReviewPartyResponse(
        id=row["id"], suggested_name=suggested_name, suggested_role=suggested_role,
        reviewed_name=reviewed_name, reviewed_role=reviewed_role,
        name=reviewed_name or suggested_name, role=reviewed_role or suggested_role,
        status=row["status"], reviewed_at=row.get("reviewed_at"), citations=citations,
    )


def _ai_task_response(row: dict[str, Any], citations: list[dict]) -> ReviewTaskResponse:
    return ReviewTaskResponse(
        id=row["id"], source="ai", finding_id=row.get("finding_id"), title=row["title"], description=row["description"],
        status=row["status"], created_at=row["created_at"], updated_at=row.get("updated_at", row["created_at"]), citations=citations,
    )


def _manual_task_response(row: dict[str, Any]) -> ReviewTaskResponse:
    return ReviewTaskResponse(
        id=row["id"], source="manual", finding_id=None, title=row["title"], description=row["description"],
        status=row["status"], created_at=row["created_at"], updated_at=row.get("updated_at", row["created_at"]), citations=[],
    )


async def get_overview(gateway: SupabaseGateway, user: CurrentUser, case_id: UUID) -> OverviewResponse:
    repository, case, run, outputs, summary_citations, citations = await _review_data(gateway, user, case_id)
    base = {"case": _case_response(case), "lawyer_context": case.get("lawyer_context")}
    manual_tasks = await repository.manual_tasks(case_id)
    if not run:
        return OverviewResponse(**base, pending_tasks=[_manual_task_response(row) for row in manual_tasks if row["status"] == "proposed"])
    document_names = await repository.document_names([str(x["document_id"]) for x in outputs["document_summaries"]])
    summaries = [
        DocumentSummaryResponse(
            id=row["id"], document_id=row["document_id"], document_name=document_names.get(str(row["document_id"]), "Document"),
            summary=row["summary"], citations=_item_citations(citations, "document_summaries", row),
        ) for row in outputs["document_summaries"]
    ]
    fields = {status: [] for status in ("pending", "confirmed", "rejected")}
    for row in outputs["case_fields"]:
        fields[row["status"]].append(_field_response(row, _item_citations(citations, "case_fields", row)))
    parties = [_party_response(row, _item_citations(citations, "case_parties", row)) for row in outputs["case_parties"]]
    issues = [FindingResponse(**row, citations=_item_citations(citations, "findings", row)) for row in outputs["findings"]]
    ai_proposed = [_ai_task_response(row, _item_citations(citations, "tasks", row)) for row in outputs["tasks"] if row["status"] == "proposed"]
    proposed_tasks = ai_proposed + [_manual_task_response(row) for row in manual_tasks if row["status"] == "proposed"]
    return OverviewResponse(
        **base, analysis_run=CompletedRunResponse(id=run["id"], completed_at=run["completed_at"]),
        case_summary=run.get("case_summary"), case_summary_citations=summary_citations,
        document_summaries=summaries, fields=FieldGroupsResponse(**fields), parties=parties,
        latest_issues=issues, pending_tasks=proposed_tasks,
        counts=OverviewCountsResponse(
            document_summaries=len(summaries), pending_fields=len(fields["pending"]), confirmed_fields=len(fields["confirmed"]),
            rejected_fields=len(fields["rejected"]), parties=len(parties), issues=len(issues), pending_tasks=len(proposed_tasks),
        ),
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
    repository, _, run, outputs, _, citations = await _review_data(gateway, user, case_id)
    manual_tasks = [_manual_task_response(row) for row in await repository.manual_tasks(case_id)]
    if not run:
        return sorted(manual_tasks, key=lambda task: task.created_at, reverse=True)
    ai_tasks = [_ai_task_response(row, _item_citations(citations, "tasks", row)) for row in outputs["tasks"]]
    return sorted(ai_tasks + manual_tasks, key=lambda task: task.created_at, reverse=True)


async def get_activity(gateway: SupabaseGateway, user: CurrentUser, case_id: UUID) -> list[ActivityResponse]:
    repository = ReviewRepository(gateway, user)
    await repository.active_case(case_id)
    return [ActivityResponse(**row) for row in await repository.activity(case_id)]
