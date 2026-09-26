from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, status

from app.core.config import Settings, get_settings
from app.core.dependencies import CurrentUser, get_current_user, get_user_gateway
from app.integrations.supabase_gateway import SupabaseGateway

from .schemas import AnalysisRunResponse, AnalysisStatusResponse, StartAnalysisRequest
from .service import get_analysis_status, start_analysis

router = APIRouter(prefix="/v1/cases", tags=["analysis"])


@router.post(
    "/{case_id}/analysis",
    response_model=AnalysisRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        401: {"description": "Missing or invalid Supabase bearer token."},
        404: {"description": "Case is absent, archived, or not owned by the caller."},
        409: {"description": "Another analysis run is queued or processing."},
        422: {"description": "Invalid context, no ready evidence, or evidence exceeds the analysis limit."},
        503: {"description": "Supabase or server-side Groq configuration is unavailable."},
    },
)
async def start_analysis_route(
    case_id: UUID,
    payload: StartAnalysisRequest,
    background_tasks: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user),
    gateway: SupabaseGateway = Depends(get_user_gateway),
    settings: Settings = Depends(get_settings),
) -> AnalysisRunResponse:
    return await start_analysis(gateway, user, case_id, payload, background_tasks, settings)


@router.get(
    "/{case_id}/analysis",
    response_model=AnalysisStatusResponse,
    responses={
        401: {"description": "Missing or invalid Supabase bearer token."},
        404: {"description": "Case is absent, archived, or not owned by the caller."},
        503: {"description": "Supabase is unavailable."},
    },
)
async def analysis_status_route(
    case_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    gateway: SupabaseGateway = Depends(get_user_gateway),
) -> AnalysisStatusResponse:
    return await get_analysis_status(gateway, user, case_id)
