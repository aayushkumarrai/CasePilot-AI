from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.dependencies import CurrentUser, get_current_user, get_user_gateway
from app.integrations.supabase_gateway import SupabaseGateway

from .schemas import ActivityResponse, FindingResponse, OverviewResponse, ReviewTaskResponse, TimelineEventResponse
from .service import get_activity, get_issues, get_overview, get_tasks, get_timeline

router = APIRouter(prefix="/v1/cases", tags=["review"])
RESPONSES = {401: {"description": "Missing or invalid Supabase bearer token."}, 404: {"description": "Case is absent, archived, or not owned by the caller."}, 503: {"description": "Supabase is unavailable."}}


@router.get("/{case_id}/overview", response_model=OverviewResponse, responses=RESPONSES)
async def overview_route(case_id: UUID, user: CurrentUser = Depends(get_current_user), gateway: SupabaseGateway = Depends(get_user_gateway)) -> OverviewResponse:
    return await get_overview(gateway, user, case_id)


@router.get("/{case_id}/timeline", response_model=list[TimelineEventResponse], responses=RESPONSES)
async def timeline_route(case_id: UUID, user: CurrentUser = Depends(get_current_user), gateway: SupabaseGateway = Depends(get_user_gateway)) -> list[TimelineEventResponse]:
    return await get_timeline(gateway, user, case_id)


@router.get("/{case_id}/issues", response_model=list[FindingResponse], responses=RESPONSES)
async def issues_route(case_id: UUID, user: CurrentUser = Depends(get_current_user), gateway: SupabaseGateway = Depends(get_user_gateway)) -> list[FindingResponse]:
    return await get_issues(gateway, user, case_id)


@router.get("/{case_id}/tasks", response_model=list[ReviewTaskResponse], responses=RESPONSES)
async def tasks_route(case_id: UUID, user: CurrentUser = Depends(get_current_user), gateway: SupabaseGateway = Depends(get_user_gateway)) -> list[ReviewTaskResponse]:
    return await get_tasks(gateway, user, case_id)


@router.get("/{case_id}/activity", response_model=list[ActivityResponse], responses=RESPONSES)
async def activity_route(case_id: UUID, user: CurrentUser = Depends(get_current_user), gateway: SupabaseGateway = Depends(get_user_gateway)) -> list[ActivityResponse]:
    return await get_activity(gateway, user, case_id)
