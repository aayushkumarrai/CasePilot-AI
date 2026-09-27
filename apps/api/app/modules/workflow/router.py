from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.dependencies import CurrentUser, get_current_user, get_user_gateway
from app.integrations.supabase_gateway import SupabaseGateway

from .schemas import (
    FieldReviewRequest,
    FieldReviewResponse,
    ManualTaskCreateRequest,
    PartyReviewRequest,
    PartyReviewResponse,
    TaskMutationResponse,
    TaskUpdateRequest,
)
from .service import create_manual_task, review_field, review_party, update_task

router = APIRouter(tags=["workflow"])
RESPONSES = {
    401: {"description": "Missing or invalid Supabase bearer token."},
    404: {"description": "Case or review item is absent, archived, or not owned by the caller."},
    422: {"description": "Review input or task status transition is invalid."},
    503: {"description": "Supabase is unavailable."},
}


@router.patch("/v1/cases/{case_id}/fields/{field_id}", response_model=FieldReviewResponse, responses=RESPONSES)
async def review_field_route(case_id: UUID, field_id: UUID, payload: FieldReviewRequest, user: CurrentUser = Depends(get_current_user), gateway: SupabaseGateway = Depends(get_user_gateway)) -> FieldReviewResponse:
    return await review_field(gateway, user, case_id, field_id, payload)


@router.patch("/v1/cases/{case_id}/parties/{party_id}", response_model=PartyReviewResponse, responses=RESPONSES)
async def review_party_route(case_id: UUID, party_id: UUID, payload: PartyReviewRequest, user: CurrentUser = Depends(get_current_user), gateway: SupabaseGateway = Depends(get_user_gateway)) -> PartyReviewResponse:
    return await review_party(gateway, user, case_id, party_id, payload)


@router.post("/v1/cases/{case_id}/tasks", response_model=TaskMutationResponse, status_code=status.HTTP_201_CREATED, responses=RESPONSES)
async def create_manual_task_route(case_id: UUID, payload: ManualTaskCreateRequest, user: CurrentUser = Depends(get_current_user), gateway: SupabaseGateway = Depends(get_user_gateway)) -> TaskMutationResponse:
    return await create_manual_task(gateway, user, case_id, payload)


@router.patch("/v1/tasks/{task_id}", response_model=TaskMutationResponse, responses=RESPONSES)
async def update_task_route(task_id: UUID, payload: TaskUpdateRequest, user: CurrentUser = Depends(get_current_user), gateway: SupabaseGateway = Depends(get_user_gateway)) -> TaskMutationResponse:
    return await update_task(gateway, user, task_id, payload)
