from app.core.dependencies import CurrentUser
from app.core.errors import unavailable
from app.integrations.supabase_gateway import SupabaseError, SupabaseGateway

from .schemas import MeResponse


async def get_me(gateway: SupabaseGateway, user: CurrentUser) -> MeResponse:
    try:
        profile = await gateway.select(
            "profiles", {"select": "id,email,display_name,created_at", "id": f"eq.{user.id}"}, single=True
        )
    except SupabaseError as exc:
        raise unavailable() from exc
    if not profile:
        raise unavailable("Profile is missing. Verify the Supabase user-profile trigger.")
    return MeResponse.model_validate(profile)
