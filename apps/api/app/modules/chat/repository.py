from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.dependencies import CurrentUser
from app.core.errors import not_found, unavailable
from app.integrations.supabase_gateway import SupabaseError, SupabaseGateway
from app.modules.cases.repository import CaseRepository


class ChatRepository:
    def __init__(self, gateway: SupabaseGateway, user: CurrentUser) -> None:
        self.gateway = gateway
        self.user = user

    async def active_case(self, case_id: UUID) -> dict[str, Any]:
        return await CaseRepository(self.gateway, self.user).get(case_id)

    async def ready_passages(self, case_id: UUID) -> list[dict[str, Any]]:
        await self.active_case(case_id)
        try:
            documents = await self.gateway.select(
                "documents",
                {
                    "select": "id,file_name,created_at",
                    "case_id": f"eq.{case_id}",
                    "status": "eq.ready",
                    "order": "created_at.asc,id.asc",
                },
            )
            rows: list[dict[str, Any]] = []
            for document in documents or []:
                passages = await self.gateway.select(
                    "document_passages",
                    {
                        "select": "id,document_id,sequence_number,page_number,passage_label,content",
                        "document_id": f"eq.{document['id']}",
                        "order": "sequence_number.asc,id.asc",
                    },
                )
                for passage in passages or []:
                    rows.append({**passage, "document_name": document["file_name"]})
            return rows
        except SupabaseError as exc:
            raise unavailable() from exc

    async def latest_messages(self, case_id: UUID, limit: int = 100) -> list[dict[str, Any]]:
        await self.active_case(case_id)
        try:
            rows = await self.gateway.select(
                "chat_messages",
                {
                    "select": "id,case_id,exchange_id,role,response_type,content,created_at",
                    "case_id": f"eq.{case_id}",
                    "order": "created_at.desc,id.desc",
                    "limit": str(limit),
                },
            )
            chronological = list(reversed(rows or []))
            return sorted(
                chronological,
                key=lambda row: (
                    row["created_at"],
                    row["exchange_id"],
                    0 if row["role"] == "user" else 1,
                ),
            )
        except SupabaseError as exc:
            raise unavailable() from exc

    async def confirmed_details(self, case_id: UUID) -> list[str]:
        await self.active_case(case_id)
        try:
            run = await self.gateway.select(
                "analysis_runs",
                {
                    "select": "id",
                    "case_id": f"eq.{case_id}",
                    "status": "eq.completed",
                    "order": "completed_at.desc,created_at.desc",
                    "limit": "1",
                },
                single=True,
            )
            if not run:
                return []
            fields = await self.gateway.select(
                "case_fields",
                {
                    "select": "label,value,reviewed_value",
                    "analysis_run_id": f"eq.{run['id']}",
                    "status": "eq.confirmed",
                    "order": "created_at.asc,id.asc",
                },
            )
            parties = await self.gateway.select(
                "case_parties",
                {
                    "select": "name,role,reviewed_name,reviewed_role",
                    "analysis_run_id": f"eq.{run['id']}",
                    "status": "eq.confirmed",
                    "order": "created_at.asc,id.asc",
                },
            )
            details = [
                f"Field — {row['label']}: {row.get('reviewed_value') or row['value']}"
                for row in fields or []
            ]
            details.extend(
                f"Party — {row.get('reviewed_name') or row['name']}: {row.get('reviewed_role') or row['role']}"
                for row in parties or []
            )
            return details
        except SupabaseError as exc:
            raise unavailable() from exc

    async def citations_for_messages(self, message_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
        if not message_ids:
            return {}
        try:
            rows = await self.gateway.select(
                "chat_message_citations",
                {
                    "select": "id,assistant_message_id,passage_id,quote,created_at",
                    "assistant_message_id": "in.(" + ",".join(message_ids) + ")",
                    "order": "created_at.asc,id.asc",
                },
            )
            passage_ids = sorted({str(row["passage_id"]) for row in rows or []})
            passages = []
            if passage_ids:
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
            names = {str(row["id"]): row["file_name"] for row in documents or []}
            grouped: dict[str, list[dict[str, Any]]] = {}
            for citation in rows or []:
                passage = passage_by_id.get(str(citation["passage_id"]))
                if not passage or str(passage["document_id"]) not in names:
                    continue
                grouped.setdefault(str(citation["assistant_message_id"]), []).append(
                    {
                        "document_id": passage["document_id"],
                        "document_name": names[str(passage["document_id"])],
                        "passage_id": passage["id"],
                        "passage_label": passage["passage_label"],
                        "page_number": passage["page_number"],
                        "quote": citation["quote"],
                    }
                )
            return grouped
        except SupabaseError as exc:
            raise unavailable() from exc

    async def save_exchange(
        self,
        case_id: UUID,
        question: str,
        answer: str,
        response_type: str,
        citations: list[dict[str, str]],
    ) -> tuple[str, str]:
        try:
            result = await self.gateway.rpc(
                "save_chat_exchange_with_activity",
                {
                    "p_case_id": str(case_id),
                    "p_question": question,
                    "p_answer": answer,
                    "p_response_type": response_type,
                    "p_citations": citations,
                },
            )
        except SupabaseError as exc:
            code = exc.payload.get("code") if isinstance(exc.payload, dict) else None
            if exc.status_code in {400, 422} or code in {"22001", "22023", "22P02"}:
                raise unavailable("Chat response could not be safely saved. Please try again.") from exc
            raise unavailable() from exc
        if not result:
            raise not_found("Case not found")
        row = result[0] if isinstance(result, list) else result
        return str(row["user_message_id"]), str(row["assistant_message_id"])
