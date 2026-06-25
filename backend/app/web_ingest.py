"""Fetch a web page and extract readable text for the RAG knowledge base.

Deliberately dependency-light: no headless browser or readability lib. We strip
scripts/styles/tags with regex and collapse whitespace — good enough to turn an
article or a W3Schools-style tutorial page into study material the same way a
pasted note is handled. `extract_text` is pure (no network) so it stays unit
testable offline; `fetch_url_text` adds the HTTP fetch on top.

TLS NOTE: httpx uses Python's default SSL context, which `pip-system-certs`
patches to read the OS trust store — so this works behind a TLS-inspecting
proxy, same as the rest of the app.
"""
from __future__ import annotations

import html as html_lib
import re

_SCRIPT_STYLE = re.compile(r"<(script|style|noscript|svg|head)[^>]*>.*?</\1>",
                           re.IGNORECASE | re.DOTALL)
_TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_BLOCK_END = re.compile(r"(?i)</(p|div|h[1-6]|li|tr|section|article|header|footer)>|<br\s*/?>")
_TAG = re.compile(r"<[^>]+>")
_INLINE_WS = re.compile(r"[ \t\f\v]+")
_MANY_BLANKS = re.compile(r"\n\s*\n\s*\n+")

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/123.0 Safari/537.36")


def extract_text(raw: str, content_type: str = "text/html") -> tuple[str, str]:
    """Return (title, text) from raw page content. Pure — no network."""
    title = ""
    m = _TITLE.search(raw)
    if m:
        title = html_lib.unescape(_TAG.sub("", m.group(1))).strip()

    looks_html = "html" in content_type.lower() or "<" in raw[:200]
    if looks_html:
        body = _SCRIPT_STYLE.sub(" ", raw)
        body = _BLOCK_END.sub("\n", body)   # keep block boundaries as line breaks
        text = _TAG.sub(" ", body)
    else:
        text = raw

    text = html_lib.unescape(text)
    # Normalise whitespace: tidy each line, drop runs of blank lines.
    text = "\n".join(_INLINE_WS.sub(" ", line).strip() for line in text.splitlines())
    text = _MANY_BLANKS.sub("\n\n", text).strip()
    return title, text


def fetch_url_text(url: str, max_chars: int = 20000) -> tuple[str, str]:
    """Fetch a URL and return (title, text). Raises ValueError on any failure so
    the API layer can turn it into a clean 400."""
    url = url.strip()
    if not re.match(r"^https?://", url, re.IGNORECASE):
        raise ValueError("URL must start with http:// or https://")

    import httpx

    try:
        resp = httpx.get(url, follow_redirects=True, timeout=20.0,
                         headers={"User-Agent": _UA, "Accept": "text/html,*/*"})
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise ValueError(f"The page returned an error ({e.response.status_code}).") from e
    except httpx.HTTPError as e:
        raise ValueError(f"Could not fetch that page ({e.__class__.__name__}).") from e

    title, text = extract_text(resp.text, resp.headers.get("content-type", ""))
    if not text:
        raise ValueError("No readable text was found on that page.")
    return (title or url), text[:max_chars]
