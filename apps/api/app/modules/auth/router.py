from fastapi import APIRouter, Depends

from app.core.dependencies import CurrentUser, get_current_user, get_user_gateway
from app.integrations.supabase_gateway import SupabaseGateway

from .schemas import MeResponse
from .service import get_me

router = APIRouter(prefix="/v1", tags=["auth"])


@router.get("/me", response_model=MeResponse)
async def me(
    user: CurrentUser = Depends(get_current_user), gateway: SupabaseGateway = Depends(get_user_gateway)
) -> MeResponse:
    return await get_me(gateway, user)
