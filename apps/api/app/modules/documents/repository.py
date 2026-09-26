from __future__ import annotations

from uuid import UUID

from app.core.dependencies import CurrentUser
from app.core.errors import conflict, not_found, unavailable
from app.integrations.supabase_gateway import SupabaseError, SupabaseGateway


class DocumentRepository:
    def __init__(self, gateway: SupabaseGateway, user: CurrentUser) -> None:
        self.gateway = gateway
        self.user = user

    async def list(self, case_id: UUID) -> list[dict]:
        try:
            return await self.gateway.select(
                "documents",
                {"select": "*", "case_id": f"eq.{case_id}", "order": "created_at.desc"},
            )  # type: ignore[return-value]
        except SupabaseError as exc:
            raise unavailable() from exc

    async def get(self, document_id: UUID) -> dict:
        try:
            document = await self.gateway.select("documents", {"select": "*", "id": f"eq.{document_id}"}, single=True)
        except SupabaseError as exc:
            raise unavailable() from exc
        if not document:
            raise not_found("Document not found")
        return document  # type: ignore[return-value]

    async def passages(self, document_id: UUID) -> list[dict]:
        try:
            return await self.gateway.select(
                "document_passages",
                {"select": "*", "document_id": f"eq.{document_id}", "order": "sequence_number.asc"},
            )  # type: ignore[return-value]
        except SupabaseError as exc:
            raise unavailable() from exc

    async def mutate(self, function: str, payload: dict) -> dict:
        try:
            result = await self.gateway.rpc(function, payload)
        except SupabaseError as exc:
            payload_data = exc.payload if isinstance(exc.payload, dict) else {}
            if exc.status_code == 409 or payload_data.get("code") == "23505":
                raise conflict("A case can contain at most 50 documents") from exc
            if exc.status_code in {401, 403, 404}:
                raise not_found("Document or case not found") from exc
            raise unavailable() from exc
        if not result:
            raise not_found("Document or case not found")
        return result[0] if isinstance(result, list) else result
