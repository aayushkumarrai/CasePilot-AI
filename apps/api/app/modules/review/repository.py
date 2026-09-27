from __future__ import annotations

from collections import defaultdict
from typing import Any
from uuid import UUID

from app.core.dependencies import CurrentUser
from app.core.errors import not_found, unavailable
from app.integrations.supabase_gateway import SupabaseError, SupabaseGateway


class ReviewRepository:
    """Owner-safe persisted review reads. Every request uses the caller JWT/RLS."""

    _PARENT_COLUMNS = {
        "document_summaries": "document_summary_id",
        "case_fields": "case_field_id",
        "case_parties": "case_party_id",
        "timeline_events": "timeline_event_id",
        "findings": "finding_id",
        "tasks": "task_id",
    }
    _OUTPUT_SELECTS = {
        "document_summaries": "id,analysis_run_id,document_id,summary,created_at",
        "case_fields": "id,analysis_run_id,field_key,label,value,reviewed_value,status,reviewed_at,created_at",
        "case_parties": "id,analysis_run_id,name,role,reviewed_name,reviewed_role,status,reviewed_at,created_at",
        "timeline_events": "id,analysis_run_id,event_date_text,date_confidence,title,description,created_at",
        "findings": "id,analysis_run_id,kind,title,description,created_at",
        "tasks": "id,analysis_run_id,finding_id,title,description,status,created_at,updated_at",
    }

    def __init__(self, gateway: SupabaseGateway, user: CurrentUser) -> None:
        self.gateway = gateway
        self.user = user

    async def active_case(self, case_id: UUID) -> dict[str, Any]:
        try:
            case = await self.gateway.select(
                "cases",
                {
                    "select": "id,external_case_id,case_name,status,created_at,updated_at,archived_at,lawyer_context",
                    "id": f"eq.{case_id}",
                    "owner_id": f"eq.{self.user.id}",
                    "archived_at": "is.null",
                },
                single=True,
            )
        except SupabaseError as exc:
            raise unavailable() from exc
        if not case:
            raise not_found("Case not found")
        return case

    async def latest_completed_run(self, case_id: UUID) -> dict[str, Any] | None:
        try:
            return await self.gateway.select(
                "analysis_runs",
                {
                    "select": "id,case_id,status,case_summary,completed_at,created_at",
                    "case_id": f"eq.{case_id}",
                    "status": "eq.completed",
                    "order": "completed_at.desc,created_at.desc",
                    "limit": "1",
                },
                single=True,
            )
        except SupabaseError as exc:
            raise unavailable() from exc

    async def outputs(self, run_id: UUID) -> dict[str, list[dict[str, Any]]]:
        try:
            result: dict[str, list[dict[str, Any]]] = {}
            for table, select in self._OUTPUT_SELECTS.items():
                rows = await self.gateway.select(
                    table,
                    {"select": select, "analysis_run_id": f"eq.{run_id}", "order": "created_at.asc"},
                )
                result[table] = list(rows or [])
            return result
        except SupabaseError as exc:
            raise unavailable() from exc

    async def fill_missing_outputs(
        self, case_id: UUID, outputs: dict[str, list[dict[str, Any]]]
    ) -> dict[str, list[dict[str, Any]]]:
        """Fill omitted categories from their newest grounded completed-run output.

        Completed runs remain immutable. This keeps a narrow rerun from making
        previously persisted review sections disappear from the workspace.
        """
        try:
            runs = await self.gateway.select(
                "analysis_runs",
                {"select": "id", "case_id": f"eq.{case_id}", "status": "eq.completed", "order": "completed_at.desc,created_at.desc"},
            )
            for table, select in self._OUTPUT_SELECTS.items():
                merge_review_history = table in {"case_fields", "case_parties"}
                if outputs[table] and not merge_review_history:
                    continue
                candidates = list(outputs[table])
                for run in runs or []:
                    rows = await self.gateway.select(
                        table,
                        {"select": select, "analysis_run_id": f"eq.{run['id']}", "order": "created_at.asc"},
                    )
                    if rows:
                        candidates.extend(
                            row for row in rows
                            if all(str(existing["id"]) != str(row["id"]) for existing in candidates)
                        )
                        if not merge_review_history:
                            break
                if merge_review_history:
                    selected: dict[str, dict[str, Any]] = {}
                    for row in candidates:
                        if table == "case_fields":
                            key = str(row.get("field_key") or row.get("label") or row["id"]).strip().casefold()
                        else:
                            key = str(row.get("role") or row.get("name") or row["id"]).strip().casefold()
                        current = selected.get(key)
                        if current is None or (
                            current.get("status") == "pending" and row.get("status") in {"confirmed", "rejected"}
                        ):
                            selected[key] = row
                    outputs[table] = list(selected.values())
                elif candidates:
                    outputs[table] = candidates
            return outputs
        except SupabaseError as exc:
            raise unavailable() from exc

    async def resolve_citations(
        self, run_id: UUID, outputs: dict[str, list[dict[str, Any]]]
    ) -> tuple[list[dict[str, Any]], dict[tuple[str, str], list[dict[str, Any]]]]:
        """Return summary citations and citations keyed by (output table, output id)."""
        try:
            summary_rows = await self.gateway.select(
                "analysis_citations",
                {
                    "select": "id,passage_id,quote,created_at",
                    "analysis_run_id": f"eq.{run_id}",
                    "target_type": "eq.case_summary",
                    "order": "created_at.asc,id.asc",
                },
            )
            grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
            all_rows: list[tuple[str, str, dict[str, Any]]] = []
            for table, parent_column in self._PARENT_COLUMNS.items():
                ids = [str(row["id"]) for row in outputs[table]]
                if not ids:
                    continue
                rows = await self.gateway.select(
                    "analysis_citations",
                    {
                        "select": "id,passage_id,quote,created_at," + parent_column,
                        parent_column: "in.(" + ",".join(ids) + ")",
                        "order": "created_at.asc,id.asc",
                    },
                )
                for row in rows or []:
                    parent_id = str(row[parent_column])
                    grouped[(table, parent_id)].append(row)
                    all_rows.append((table, parent_id, row))
            all_citations = list(summary_rows or []) + [row for _, _, row in all_rows]
            resolved = await self._citation_details(all_citations)
            summary = [resolved[str(row["id"])] for row in summary_rows or []]
            result: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
            for table, parent_id, row in all_rows:
                result[(table, parent_id)].append(resolved[str(row["id"])])
            return summary, result
        except SupabaseError as exc:
            raise unavailable() from exc

    async def _citation_details(self, citations: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        if not citations:
            return {}
        passage_ids = sorted({str(row["passage_id"]) for row in citations})
        passages = await self.gateway.select(
            "document_passages",
            {
                "select": "id,document_id,page_number,passage_label",
                "id": "in.(" + ",".join(passage_ids) + ")",
            },
        )
        passage_by_id = {str(row["id"]): row for row in passages or []}
        document_ids = sorted({str(row["document_id"]) for row in passage_by_id.values()})
        documents = []
        if document_ids:
            documents = await self.gateway.select(
                "documents",
                {"select": "id,file_name", "id": "in.(" + ",".join(document_ids) + ")"},
            )
        document_names = {str(row["id"]): row["file_name"] for row in documents or []}
        result: dict[str, dict[str, Any]] = {}
        for citation in citations:
            passage = passage_by_id.get(str(citation["passage_id"]))
            if not passage:
                continue
            name = document_names.get(str(passage["document_id"]))
            if not name:
                continue
            result[str(citation["id"])] = {
                "document_id": passage["document_id"],
                "document_name": name,
                "passage_id": passage["id"],
                "passage_label": passage["passage_label"],
                "page_number": passage["page_number"],
                "quote": citation["quote"],
            }
        return result

    async def document_names(self, document_ids: list[str]) -> dict[str, str]:
        if not document_ids:
            return {}
        try:
            rows = await self.gateway.select(
                "documents", {"select": "id,file_name", "id": "in.(" + ",".join(document_ids) + ")"}
            )
            return {str(row["id"]): row["file_name"] for row in rows or []}
        except SupabaseError as exc:
            raise unavailable() from exc

    async def manual_tasks(self, case_id: UUID) -> list[dict[str, Any]]:
        try:
            rows = await self.gateway.select(
                "manual_tasks",
                {"select": "id,case_id,title,description,status,created_at,updated_at", "case_id": f"eq.{case_id}", "order": "created_at.asc"},
            )
            return list(rows or [])
        except SupabaseError as exc:
            raise unavailable() from exc

    async def activity(self, case_id: UUID) -> list[dict[str, Any]]:
        try:
            rows = await self.gateway.select(
                "activity_events",
                {
                    "select": "id,action,actor_type,details,created_at",
                    "case_id": f"eq.{case_id}",
                    "order": "created_at.desc",
                    "limit": "50",
                },
            )
            return list(rows or [])
        except SupabaseError as exc:
            raise unavailable() from exc
