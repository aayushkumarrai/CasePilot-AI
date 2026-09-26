from __future__ import annotations

from uuid import UUID

from app.core.errors import conflict, not_found, unavailable
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

    async def start_run(self, case_id: UUID, lawyer_context: str | None) -> dict:
        try:
            result = await self.gateway.rpc(
                "start_analysis_run_with_activity",
                {"p_case_id": str(case_id), "p_lawyer_context": lawyer_context},
            )
        except SupabaseError as exc:
            if self._is_active_run_conflict(exc):
                raise conflict("Analysis is already in progress for this case") from exc
            if self._is_no_ready_document_error(exc):
                # The public service normally catches this in preflight, but
                # retain a safe mapping if document state changes mid-request.
                from fastapi import HTTPException, status

                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="At least one ready document is required for analysis",
                ) from exc
            raise unavailable() from exc
        if not result:
            raise not_found("Case not found")
        return result[0] if isinstance(result, list) else result

    async def latest_run_status(self, case_id: UUID) -> tuple[dict | None, bool]:
        await CaseRepository(self.gateway, self.user).get(case_id)
        try:
            latest = await self.gateway.select(
                "analysis_runs",
                {
                    "select": "id,status,started_at,completed_at,error_message,created_at",
                    "case_id": f"eq.{case_id}",
                    "order": "created_at.desc",
                    "limit": "1",
                },
                single=True,
            )
            completed = await self.gateway.select(
                "analysis_runs",
                {
                    "select": "id",
                    "case_id": f"eq.{case_id}",
                    "status": "eq.completed",
                    "limit": "1",
                },
                single=True,
            )
        except SupabaseError as exc:
            raise unavailable() from exc
        return latest, bool(completed)

    @staticmethod
    def _payload_code(exc: SupabaseError) -> str | None:
        return exc.payload.get("code") if isinstance(exc.payload, dict) else None

    @classmethod
    def _is_active_run_conflict(cls, exc: SupabaseError) -> bool:
        return exc.status_code == 409 or cls._payload_code(exc) == "23505"

    @classmethod
    def _is_no_ready_document_error(cls, exc: SupabaseError) -> bool:
        payload = exc.payload if isinstance(exc.payload, dict) else {}
        return cls._payload_code(exc) == "22023" and "ready document" in str(payload.get("message", "")).lower()
