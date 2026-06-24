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
    return settings.openrouter_model_smart if tier == SMART else settings.openrouter_model_fast


def get_llm(tier: str = FAST, temperature: float = 0.3):
    """Return a cached LangChain chat model bound to OpenRouter, or None if no key.

    Callers should check `settings.has_llm` (or a None return) and use the mock
    helpers below when the model is unavailable.
    """
    if not settings.has_llm:
        return None

    cache_key = (tier, temperature, _model_for(tier))
    if cache_key in _llm_cache:
        return _llm_cache[cache_key]

    # Imported lazily so the app imports cleanly even if langchain isn't present.
    from langchain_openai import ChatOpenAI

    model = ChatOpenAI(
        model=_model_for(tier),
        temperature=temperature,
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
        max_retries=3,  # ride out transient proxy/network hiccups
        # OpenRouter recommends these headers for attribution; harmless if unused.
        default_headers={
            "HTTP-Referer": "https://studyquest.ai",
            "X-Title": "StudyQuest AI",
        },
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
