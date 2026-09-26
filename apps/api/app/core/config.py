from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CasePilot API"
    app_env: str = "development"
    allowed_origins: str = "http://localhost:3000"
    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    groq_api_key: str | None = None
    groq_model: str | None = None
    groq_base_url: str = "https://api.groq.com/openai/v1"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def supabase_is_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_anon_key)

    @property
    def groq_is_configured(self) -> bool:
        return bool(self.groq_api_key and self.groq_model)


@lru_cache
def get_settings() -> Settings:
    return Settings()
