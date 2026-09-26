from __future__ import annotations

from uuid import UUID

from app.core.dependencies import CurrentUser
from app.core.errors import conflict, not_found, unavailable
from app.integrations.supabase_gateway import SupabaseError, SupabaseGateway


class CaseRepository:
    def __init__(self, gateway: SupabaseGateway, user: CurrentUser) -> None:
        self.gateway = gateway
        self.user = user

    async def list(self, include_archived: bool) -> list[dict]:
        params = {
            "select": "id,external_case_id,case_name,status,created_at,updated_at,archived_at",
            "owner_id": f"eq.{self.user.id}",
            "order": "updated_at.desc",
        }
        if not include_archived:
            params["archived_at"] = "is.null"
        try:
            return await self.gateway.select("cases", params)  # type: ignore[return-value]
        except SupabaseError as exc:
            raise unavailable() from exc

    async def get(self, case_id: UUID, *, include_archived: bool = False) -> dict:
        params = {
            "select": "id,external_case_id,case_name,status,created_at,updated_at,archived_at",
            "id": f"eq.{case_id}",
            "owner_id": f"eq.{self.user.id}",
        }
        if not include_archived:
            params["archived_at"] = "is.null"
        try:
            case = await self.gateway.select("cases", params, single=True)
        except SupabaseError as exc:
            raise unavailable() from exc
        if not case:
            raise not_found("Case not found")
        return case  # type: ignore[return-value]

    async def call_mutation(self, function: str, payload: dict) -> dict:
        try:
            result = await self.gateway.rpc(function, payload)
        except SupabaseError as exc:
            if exc.status_code == 409 or self._is_unique_violation(exc):
                raise conflict("An active case already uses this Case ID") from exc
            if exc.status_code in {401, 403, 404}:
                raise not_found("Case not found") from exc
            raise unavailable() from exc
        if not result:
            raise not_found("Case not found")
        return result[0] if isinstance(result, list) else result

    @staticmethod
    def _is_unique_violation(exc: SupabaseError) -> bool:
        payload = exc.payload if isinstance(exc.payload, dict) else {}
        return payload.get("code") == "23505"
