"""YouTube playlist + transcript access — NO API key required.

We use yt-dlp (flat extraction) for playlist metadata and
youtube-transcript-api for captions. Both need network access to YouTube; all
calls raise YouTubeError on failure so the API can respond gracefully (bad
link, private playlist, no captions, offline, etc.).
"""
from __future__ import annotations

from dataclasses import dataclass


class YouTubeError(Exception):
    pass


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
            "ignoreerrors": True}
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
        return YouTubeTranscriptApi.get_transcript(video_id)
    except (TranscriptsDisabled, NoTranscriptFound):
        raise YouTubeError("This video has no available transcript/captions.")
    except Exception as e:
        raise YouTubeError(f"Could not fetch transcript: {e}") from e
