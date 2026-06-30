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

    # --- LLM backend selection ---
    # openrouter (default, cloud) | ollama (local, no key)
    llm_backend: str = "openrouter"

    # --- Vector store for grounded RAG embeddings ---
    # numpy (default; vectors as JSON + NumPy cosine, runs on SQLite) | pgvector (Postgres)
    vector_backend: str = "numpy"
    embedding_dim: int = 384  # bge-small-en-v1.5

    # --- OpenRouter (OpenAI-compatible) LLM access ---
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    # Model slugs are OpenRouter ids; override in .env as you like.
    openrouter_model_fast: str = "anthropic/claude-3.5-haiku"
    openrouter_model_smart: str = "anthropic/claude-3.5-sonnet"

    # --- Ollama (local LLM, OpenAI-compatible at /v1) — used when LLM_BACKEND=ollama ---
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model_fast: str = "llama3.1"
    ollama_model_smart: str = "llama3.1"

    # --- Langfuse tracing (optional, env-gated) ---
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    # --- YouTube auth (optional) — bypass "Please sign in" anti-bot blocking ---
    # Pull cookies from your logged-in browser: "edge" | "chrome" | "firefox".
    ytdlp_cookies_from_browser: str = ""
    # Or point at an exported Netscape cookies.txt instead.
    youtube_cookies_file: str = ""

    # --- Optional observability (Phase 10) ---
    langchain_api_key: str = ""
    langchain_tracing_v2: bool = False
    langchain_project: str = "studyquest-ai"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def has_llm(self) -> bool:
        """True when a real LLM is configured. When False, agents fall back to
        a deterministic mock so the app still runs without a key. Ollama needs
        no key (reachability is checked at call time)."""
        return self.llm_backend == "ollama" or bool(self.openrouter_api_key)

    @property
    def langfuse_enabled(self) -> bool:
        return bool(self.langfuse_public_key and self.langfuse_secret_key)


settings = Settings()
