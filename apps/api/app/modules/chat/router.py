from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.config import Settings, get_settings
from app.core.dependencies import CurrentUser, get_current_user, get_user_gateway
from app.integrations.supabase_gateway import SupabaseGateway

from .schemas import ChatExchangeResponse, ChatMessageResponse, ChatSendRequest
from .service import get_chat_history, send_chat_message

router = APIRouter(prefix="/v1/cases", tags=["chat"])
RESPONSES = {
    401: {"description": "Missing or invalid Supabase bearer token."},
    404: {"description": "Case is absent, archived, or not owned by the caller."},
    422: {"description": "Chat message is invalid."},
    503: {"description": "Chat provider, validation, or persistence is unavailable."},
}


@router.get("/{case_id}/chat", response_model=list[ChatMessageResponse], responses=RESPONSES)
async def chat_history_route(
    case_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    gateway: SupabaseGateway = Depends(get_user_gateway),
) -> list[ChatMessageResponse]:
    return await get_chat_history(gateway, user, case_id)


@router.post(
    "/{case_id}/chat",
    response_model=ChatExchangeResponse,
    status_code=status.HTTP_201_CREATED,
    responses=RESPONSES,
)
async def send_chat_route(
    case_id: UUID,
    payload: ChatSendRequest,
    user: CurrentUser = Depends(get_current_user),
    gateway: SupabaseGateway = Depends(get_user_gateway),
    settings: Settings = Depends(get_settings),
) -> ChatExchangeResponse:
    return await send_chat_message(gateway, user, case_id, payload, settings)
