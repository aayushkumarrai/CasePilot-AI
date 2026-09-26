from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.modules.auth.router import router as auth_router
from app.modules.cases.router import router as cases_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.documents.router import router as documents_router

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """Deployment and local-development health check."""
    return {"status": "ok", "environment": settings.app_env, "name": settings.app_name}


@app.get("/health/ready", tags=["system"])
async def readiness() -> dict[str, str]:
    from app.core.errors import unavailable
    from app.integrations.supabase_gateway import SupabaseError, SupabaseGateway

    if not settings.supabase_is_configured:
        raise unavailable("Supabase URL and anonymous key are not configured")
    gateway = SupabaseGateway(settings.supabase_url or "", settings.supabase_anon_key or "")
    try:
        await gateway.ready()
    except SupabaseError as exc:
        raise unavailable() from exc
    finally:
        await gateway.close()
    return {"status": "ready"}


app.include_router(auth_router)
app.include_router(cases_router)
app.include_router(dashboard_router)
app.include_router(documents_router)
