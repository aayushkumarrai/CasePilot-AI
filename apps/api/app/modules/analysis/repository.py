from __future__ import annotations

from uuid import UUID

from app.core.errors import unavailable
from app.core.dependencies import CurrentUser
from app.integrations.supabase_gateway import SupabaseError, SupabaseGateway
from app.modules.cases.repository import CaseRepository


class AnalysisRepository:
    """Owner-safe reads used to assemble analysis evidence."""

    def __init__(self, gateway: SupabaseGateway, user: CurrentUser) -> None:
        self.gateway = gateway
        self.user = user

    async def ready_documents_with_passages(self, case_id: UUID) -> list[dict]:
        # The case repository applies the caller's JWT and excludes archived
        # cases, so every later evidence read inherits the same owner boundary.
        await CaseRepository(self.gateway, self.user).get(case_id)
        try:
            documents = await self.gateway.select(
                "documents",
                {
                    "select": "id,case_id,file_name,content_type,created_at",
                    "case_id": f"eq.{case_id}",
                    "status": "eq.ready",
                    "order": "created_at.asc",
                },
            )
            result: list[dict] = []
            for document in documents:  # type: ignore[union-attr]
                passages = await self.gateway.select(
                    "document_passages",
                    {
                        "select": "id,document_id,sequence_number,page_number,passage_label,content",
                        "document_id": f"eq.{document['id']}",
                        "order": "sequence_number.asc",
                    },
                )
                result.append({**document, "passages": passages})
            return result
        except SupabaseError as exc:
            raise unavailable() from exc
