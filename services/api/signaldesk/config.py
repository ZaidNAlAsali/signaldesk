from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SignalDesk API"
    environment: str = "development"
    database_url: str = "sqlite:///./signaldesk.db"
    auto_create_schema: bool = True
    ai_provider: str = "demo"
    openai_api_key: str | None = Field(default=None, repr=False)
    openai_model: str = "gpt-5-mini"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_mode: str = "responses"
    provider_label: str = "openai"
    provider_timeout_seconds: float = Field(default=30.0, ge=1, le=120)
    provider_max_retries: int = Field(default=2, ge=0, le=5)
    provider_retry_backoff_seconds: float = Field(default=0.5, ge=0, le=10)
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    seed_demo_data: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_prefix="SIGNALDESK_", extra="ignore")

    @field_validator("ai_provider")
    @classmethod
    def supported_provider(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"demo", "openai"}:
            raise ValueError("ai_provider must be 'demo' or 'openai'")
        return normalized

    @field_validator("openai_api_mode")
    @classmethod
    def supported_api_mode(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"responses", "chat_completions"}:
            raise ValueError("openai_api_mode must be 'responses' or 'chat_completions'")
        return normalized

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip().rstrip("/") for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def policy_dir(self) -> Path:
        return Path(__file__).resolve().parent.parent / "data" / "policies"


@lru_cache
def get_settings() -> Settings:
    return Settings()
