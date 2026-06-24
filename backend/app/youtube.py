"""YouTube playlist + transcript access — NO API key required.

We use yt-dlp (flat extraction) for playlist metadata and
youtube-transcript-api for captions. Both need network access to YouTube; all
calls raise YouTubeError on failure so the API can respond gracefully (bad
link, private playlist, no captions, offline, etc.).
"""
from __future__ import annotations

import functools
import os
import tempfile
from dataclasses import dataclass

from app.config import settings


class YouTubeError(Exception):
    pass


def _cookie_opts() -> dict:
    """yt-dlp options to authenticate via the browser's YouTube cookies, when
    configured. Bypasses the 'Please sign in' anti-bot block on flagged IPs."""
    browser = settings.ytdlp_cookies_from_browser.strip()
    if settings.youtube_cookies_file:
        return {"cookiefile": settings.youtube_cookies_file}
    if browser:
        return {"cookiesfrombrowser": (browser,)}
    return {}


@functools.lru_cache(maxsize=1)
def _transcript_cookie_file() -> str | None:
    """youtube-transcript-api takes a cookies.txt path (not a browser). If an
    explicit file is set, use it; else try to extract one from the browser via
    yt-dlp. Returns None (run without cookies) if unavailable."""
    if settings.youtube_cookies_file:
        return settings.youtube_cookies_file
    browser = settings.ytdlp_cookies_from_browser.strip()
    if not browser:
        return None
    try:
        from yt_dlp.cookies import extract_cookies_from_browser

        jar = extract_cookies_from_browser(browser)
        path = os.path.join(tempfile.gettempdir(), "sq_youtube_cookies.txt")
        jar.save(path, ignore_discard=True, ignore_expires=True)
        return path
    except Exception:
        return None


@dataclass
class PlaylistVideo:
    video_id: str
    title: str
    duration_seconds: int


def format_duration(seconds: int) -> str:
    """Human-friendly duration, e.g. 95 -> '1m 35s', 3725 -> '1h 2m'."""
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m}m"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


def fetch_playlist(url: str) -> tuple[str, list[PlaylistVideo]]:
    """Return (playlist_title, videos). Raises YouTubeError on failure."""
    import yt_dlp

    opts = {"quiet": True, "extract_flat": "in_playlist", "skip_download": True,
            "ignoreerrors": True, **_cookie_opts()}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:  # yt-dlp raises many error types
        raise YouTubeError(f"Could not read playlist: {e}") from e

    if not info or "entries" not in info:
        raise YouTubeError("That link doesn't look like a playlist, or it's private/empty.")

    videos: list[PlaylistVideo] = []
    for entry in info["entries"]:
        if not entry:
            continue
        videos.append(PlaylistVideo(
            video_id=entry.get("id", ""),
            title=entry.get("title") or "Untitled video",
            duration_seconds=int(entry.get("duration") or 0),
        ))
    if not videos:
        raise YouTubeError("No videos found in that playlist.")
    return info.get("title") or "YouTube Course", videos


def fetch_transcript(video_id: str) -> list[dict]:
    """Return transcript segments [{text, start, duration}]. Raises YouTubeError."""
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import (NoTranscriptFound,
                                                TranscriptsDisabled)
    try:
        cookies = _transcript_cookie_file()
        if cookies:
            return YouTubeTranscriptApi.get_transcript(video_id, cookies=cookies)
        return YouTubeTranscriptApi.get_transcript(video_id)
    except (TranscriptsDisabled, NoTranscriptFound):
        raise YouTubeError("This video has no available transcript/captions.")
    except Exception as e:
        raise YouTubeError(f"Could not fetch transcript: {e}") from e
