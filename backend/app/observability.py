"""LangSmith tracing — fully env-gated.

When LANGCHAIN_API_KEY + LANGCHAIN_TRACING_V2 are set, LangChain/LangGraph emit
a trace of every LLM call and agent step to LangSmith automatically. We just
push the configured values into the process environment at startup. With
nothing configured, the app runs normally with tracing OFF (no-op)."""
from __future__ import annotations

import os

from app.config import settings


def init_tracing() -> dict:
    """Enable LangSmith if configured. Returns a status dict for /api/obs/status."""
    if settings.langchain_api_key and settings.langchain_tracing_v2:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
        os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
        return {"tracing": True, "project": settings.langchain_project}
    return {"tracing": False, "project": None}
