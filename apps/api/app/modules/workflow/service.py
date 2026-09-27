from __future__ import annotations

from uuid import UUID

from app.core.dependencies import CurrentUser
from app.integrations.supabase_gateway import SupabaseGateway

from .repository import WorkflowRepository
from .schemas import (
    FieldReviewRequest,
    FieldReviewResponse,
    ManualTaskCreateRequest,
    PartyReviewRequest,
    PartyReviewResponse,
    TaskMutationResponse,
    TaskUpdateRequest,
)


def _field_response(row: dict) -> FieldReviewResponse:
    suggested = row["value"]
    reviewed = row.get("reviewed_value")
    return FieldReviewResponse(
        id=row["id"], field_key=row["field_key"], label=row["label"], suggested_value=suggested,
        reviewed_value=reviewed, value=reviewed or suggested, status=row["status"], reviewed_at=row.get("reviewed_at"),
    )


def _party_response(row: dict) -> PartyReviewResponse:
    suggested_name, suggested_role = row["name"], row["role"]
    reviewed_name, reviewed_role = row.get("reviewed_name"), row.get("reviewed_role")
    return PartyReviewResponse(
        id=row["id"], suggested_name=suggested_name, suggested_role=suggested_role,
        reviewed_name=reviewed_name, reviewed_role=reviewed_role,
        name=reviewed_name or suggested_name, role=reviewed_role or suggested_role,
        status=row["status"], reviewed_at=row.get("reviewed_at"),
    )


def _task_response(row: dict, source: str) -> TaskMutationResponse:
    return TaskMutationResponse(
        id=row["id"], case_id=row.get("case_id"), source=source, title=row["title"], description=row["description"],
        status=row["status"], updated_at=row["updated_at"],
    )


async def review_field(gateway: SupabaseGateway, user: CurrentUser, case_id: UUID, field_id: UUID, payload: FieldReviewRequest) -> FieldReviewResponse:
    row = await WorkflowRepository(gateway).mutation(
        "review_case_field_with_activity",
        {"p_case_id": str(case_id), "p_field_id": str(field_id), "p_action": payload.action, "p_reviewed_value": payload.value},
    )
    return _field_response(row)


async def review_party(gateway: SupabaseGateway, user: CurrentUser, case_id: UUID, party_id: UUID, payload: PartyReviewRequest) -> PartyReviewResponse:
    row = await WorkflowRepository(gateway).mutation(
        "review_case_party_with_activity",
        {"p_case_id": str(case_id), "p_party_id": str(party_id), "p_action": payload.action,
         "p_reviewed_name": payload.name, "p_reviewed_role": payload.role},
    )
    return _party_response(row)


async def create_manual_task(gateway: SupabaseGateway, user: CurrentUser, case_id: UUID, payload: ManualTaskCreateRequest) -> TaskMutationResponse:
    row = await WorkflowRepository(gateway).mutation(
        "create_manual_task_with_activity", {"p_case_id": str(case_id), "p_title": payload.title, "p_description": payload.description},
    )
    return _task_response(row, "manual")


async def update_task(gateway: SupabaseGateway, user: CurrentUser, task_id: UUID, payload: TaskUpdateRequest) -> TaskMutationResponse:
    repository = WorkflowRepository(gateway)
    source = await repository.task_source(str(task_id))
    if source is None:
        # mutation provides the same owner-safe 404 for absent or inaccessible task IDs.
        source = "ai"
    if source == "manual":
        row = await repository.mutation(
            "update_manual_task_with_activity",
            {"p_task_id": str(task_id), "p_title": payload.title, "p_description": payload.description, "p_new_status": payload.status},
        )
    else:
        if payload.status is None:
            from app.core.errors import unprocessable
            raise unprocessable("AI-proposed task wording cannot be edited")
        row = await repository.mutation("transition_ai_task_with_activity", {"p_task_id": str(task_id), "p_new_status": payload.status})
    return _task_response(row, source)
