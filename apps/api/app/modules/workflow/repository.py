from __future__ import annotations

from typing import Any

from app.core.errors import not_found, unprocessable, unavailable
from app.integrations.supabase_gateway import SupabaseError, SupabaseGateway


class WorkflowRepository:
    def __init__(self, gateway: SupabaseGateway) -> None:
        self.gateway = gateway

    async def mutation(self, function: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            result = await self.gateway.rpc(function, payload)
        except SupabaseError as exc:
            body = exc.payload if isinstance(exc.payload, dict) else {}
            message = body.get("message") or body.get("detail") or "The requested review action is invalid"
            if exc.status_code in {400, 409, 422} or body.get("code") in {"22001", "22023", "23514"}:
                raise unprocessable(str(message)) from exc
            if exc.status_code in {401, 403, 404}:
                raise not_found("Case or review item not found") from exc
            raise unavailable() from exc
        if not result:
            raise not_found("Case or review item not found")
        return result[0] if isinstance(result, list) else result

    async def task_source(self, task_id: str) -> str | None:
        try:
            manual = await self.gateway.select("manual_tasks", {"select": "id", "id": f"eq.{task_id}"}, single=True)
            if manual:
                return "manual"
            ai = await self.gateway.select("tasks", {"select": "id", "id": f"eq.{task_id}"}, single=True)
            return "ai" if ai else None
        except SupabaseError as exc:
            raise unavailable() from exc
