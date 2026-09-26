from fastapi import APIRouter, Depends

from app.core.dependencies import CurrentUser, get_current_user, get_user_gateway
from app.integrations.supabase_gateway import SupabaseGateway

from .schemas import DashboardResponse
from .service import get_dashboard

router = APIRouter(prefix="/v1", tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardResponse)
async def dashboard(
    user: CurrentUser = Depends(get_current_user), gateway: SupabaseGateway = Depends(get_user_gateway)
) -> DashboardResponse:
    return await get_dashboard(gateway, user)
