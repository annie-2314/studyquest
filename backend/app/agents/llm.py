"""Shared LLM access layer.

WHY this layer exists: every agent (supervisor + specialists + CrewAI later)
must reach the model the same way. We use OpenRouter through its
OpenAI-compatible API so a single env var (OPENROUTER_API_KEY) powers all of
them, and model choice is configurable per call tier ("fast" vs "smart").

If no key is configured we return a deterministic MockLLM so the whole app
still runs and can be demoed/tested offline; real responses appear the moment
the key is set in .env.
"""
from __future__ import annotations

from typing import AsyncIterator, Iterable

from app.config import settings

# Tier -> which configured model slug to use.
FAST = "fast"
SMART = "smart"


# Cache model instances per (tier, temperature, model) — building ChatOpenAI
# objects repeatedly is wasteful.
#
# TLS NOTE: we deliberately do NOT pass a custom truststore http_client here.
# `pip-system-certs` (installed for yt-dlp/requests) already patches Python's
# default SSL to use the OS certificate store, so the default OpenAI/httpx
# client verifies correctly behind TLS-inspecting proxies. Layering an explicit
# truststore.SSLContext on top of that patch causes infinite recursion
# (RecursionError) — so we let the default client handle TLS.
_llm_cache: dict = {}


def _model_for(tier: str) -> str:
    if settings.llm_backend == "ollama":
        return settings.ollama_model_smart if tier == SMART else settings.ollama_model_fast
    return settings.openrouter_model_smart if tier == SMART else settings.openrouter_model_fast


def _ollama_up() -> bool:
    """Quick reachability probe so an offline Ollama degrades to mock, not a hang."""
    import socket
    from urllib.parse import urlparse

    netloc = urlparse(settings.ollama_base_url).netloc or "localhost:11434"
    host, _, port = netloc.partition(":")
    try:
        with socket.create_connection((host, int(port or 11434)), timeout=0.5):
            return True
    except OSError:
        return False


def get_llm(tier: str = FAST, temperature: float = 0.3):
    """Return a cached LangChain chat model for the selected backend, or None.

    Backends: OpenRouter (cloud, needs a key) or Ollama (local, no key). When the
    model is unavailable (no key, or Ollama offline) we return None so callers
    fall back to the deterministic mock helpers below.
    """
    if not settings.has_llm:
        return None

    from langchain_openai import ChatOpenAI  # lazy import

    cache_key = (settings.llm_backend, tier, temperature, _model_for(tier))
    if cache_key in _llm_cache:
        return _llm_cache[cache_key]

    if settings.llm_backend == "ollama":
        if not _ollama_up():
            return None  # graceful fallback → mock, no crash/hang
        model = ChatOpenAI(
            model=_model_for(tier), temperature=temperature,
            api_key="ollama",  # Ollama ignores the key but the client requires one
            base_url=settings.ollama_base_url, max_retries=1,
        )
    else:
        model = ChatOpenAI(
            model=_model_for(tier), temperature=temperature,
            api_key=settings.openrouter_api_key, base_url=settings.openrouter_base_url,
            max_retries=3,
            # No app-attribution headers — anonymous in the OpenRouter log ("Unknown").
        )
    _llm_cache[cache_key] = model
    return model


def mock_reply(system: str, user: str) -> str:
    """Deterministic stand-in used when no API key is configured."""
    return (
        "🔧 (StudyQuest mock tutor — no OPENROUTER_API_KEY set, so this is a "
        "canned response.)\n\n"
        f"You asked: \"{user.strip()[:300]}\"\n\n"
        "Once you add your OpenRouter key to backend/.env, a real AI tutor will "
        "answer here with a clear explanation and a real-life example."
    )


async def stream_text(text: str) -> AsyncIterator[str]:
    """Yield a string word-by-word so the mock path can stream like the real one."""
    words: Iterable[str] = text.split(" ")
    for i, w in enumerate(words):
        yield (w if i == 0 else " " + w)
