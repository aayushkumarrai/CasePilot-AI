from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.core.dependencies import CurrentUser, get_current_user, get_user_gateway
from app.integrations.supabase_gateway import SupabaseGateway

from .schemas import CaseResponse, CreateCaseRequest, UpdateCaseRequest
from .service import archive_case, create_case, get_case, list_cases, restore_case, update_case

router = APIRouter(prefix="/v1/cases", tags=["cases"])


@router.get("", response_model=list[CaseResponse])
async def list_case_route(
    include_archived: bool = False,
    user: CurrentUser = Depends(get_current_user),
    gateway: SupabaseGateway = Depends(get_user_gateway),
) -> list[CaseResponse]:
    return await list_cases(gateway, user, include_archived)


@router.post("", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
async def create_case_route(
    payload: CreateCaseRequest,
    user: CurrentUser = Depends(get_current_user),
    gateway: SupabaseGateway = Depends(get_user_gateway),
) -> CaseResponse:
    return await create_case(gateway, user, payload)


@router.get("/{case_id}", response_model=CaseResponse)
async def get_case_route(
    case_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    gateway: SupabaseGateway = Depends(get_user_gateway),
) -> CaseResponse:
    return await get_case(gateway, user, case_id)


@router.patch("/{case_id}", response_model=CaseResponse)
async def update_case_route(
    case_id: UUID,
    payload: UpdateCaseRequest,
    user: CurrentUser = Depends(get_current_user),
    gateway: SupabaseGateway = Depends(get_user_gateway),
) -> CaseResponse:
    return await update_case(gateway, user, case_id, payload)


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_case_route(
    case_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    gateway: SupabaseGateway = Depends(get_user_gateway),
) -> Response:
    await archive_case(gateway, user, case_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{case_id}/restore", response_model=CaseResponse)
async def restore_case_route(
    case_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    gateway: SupabaseGateway = Depends(get_user_gateway),
) -> CaseResponse:
    return await restore_case(gateway, user, case_id)
