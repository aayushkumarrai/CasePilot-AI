from __future__ import annotations

from collections.abc import AsyncGenerator
from uuid import UUID

from fastapi import Depends, Header
from pydantic import BaseModel

from app.core.config import Settings, get_settings
from app.core.errors import unavailable, unauthorized
from app.integrations.supabase_gateway import SupabaseError, SupabaseGateway


class CurrentUser(BaseModel):
    id: UUID
    email: str
    access_token: str


def get_access_token(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise unauthorized()
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise unauthorized()
    return token


async def get_current_user(
    access_token: str = Depends(get_access_token), settings: Settings = Depends(get_settings)
) -> CurrentUser:
    if not settings.supabase_is_configured:
        raise unavailable("Supabase URL and anonymous key are not configured")
    gateway = SupabaseGateway(settings.supabase_url or "", settings.supabase_anon_key or "", access_token)
    try:
        user = await gateway.auth_user()
    except SupabaseError as exc:
        if exc.status_code in {401, 403}:
            raise unauthorized() from exc
        raise unavailable() from exc
    finally:
        await gateway.close()
    try:
        return CurrentUser(id=user["id"], email=user["email"], access_token=access_token)
    except (KeyError, ValueError) as exc:
        raise unauthorized("Supabase user response was invalid") from exc


async def get_user_gateway(
    user: CurrentUser = Depends(get_current_user), settings: Settings = Depends(get_settings)
) -> AsyncGenerator[SupabaseGateway, None]:
    gateway = SupabaseGateway(settings.supabase_url or "", settings.supabase_anon_key or "", user.access_token)
    try:
        yield gateway
    finally:
        await gateway.close()
