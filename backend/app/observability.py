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


_langfuse_cb = None  # cached handler


def langfuse_callbacks() -> list:
    """LangChain callbacks for Langfuse tracing, or [] when not configured.

    Env-gated and fully optional: if LANGFUSE_* keys aren't set (or the langfuse
    package isn't installed) this is a no-op, so the app runs unchanged. Pass the
    result to `model.invoke(..., config={"callbacks": langfuse_callbacks()})`.
    """
    global _langfuse_cb
    if not settings.langfuse_enabled:
        return []
    if _langfuse_cb is not None:
        return [_langfuse_cb]
    try:  # newer (langfuse>=2) then older import path
        try:
            from langfuse.langchain import CallbackHandler
        except Exception:
            from langfuse.callback import CallbackHandler
        _langfuse_cb = CallbackHandler(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
        return [_langfuse_cb]
    except Exception:
        return []
