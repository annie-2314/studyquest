"""Application settings loaded from environment / .env (pydantic-settings)."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # SQLite for dev (zero install); swap to a Postgres URL in prod, no code change.
    database_url: str = "sqlite:///./studyquest.db"
    secret_key: str = "dev-insecure-change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    frontend_origin: str = "http://localhost:3000"

    # --- OpenRouter (OpenAI-compatible) LLM access ---
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    # Model slugs are OpenRouter ids; override in .env as you like.
    openrouter_model_fast: str = "anthropic/claude-3.5-haiku"
    openrouter_model_smart: str = "anthropic/claude-3.5-sonnet"

    # --- Optional observability (Phase 10) ---
    langchain_api_key: str = ""
    langchain_tracing_v2: bool = False
    langchain_project: str = "studyquest-ai"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def has_llm(self) -> bool:
        """True when a real LLM is configured. When False, agents fall back to
        a deterministic mock so the app still runs without a key."""
        return bool(self.openrouter_api_key)


settings = Settings()
