"""Transcription for Video RAG.

Two paths, both returning segments [{text, start, duration}]:
  1. YouTube URL  -> youtube-transcript-api (no heavy deps; works out of the box)
  2. Uploaded file -> faster-whisper (OPTIONAL heavy dep; lazy-imported)

If faster-whisper isn't installed we raise TranscribeError with guidance rather
than forcing every user to install a multi-hundred-MB model toolchain.
"""
from __future__ import annotations

import re

from app.youtube import YouTubeError, fetch_transcript


class TranscribeError(Exception):
    pass


_YT_PATTERNS = [
    r"youtu\.be/([A-Za-z0-9_-]{6,})",
    r"[?&]v=([A-Za-z0-9_-]{6,})",
    r"youtube\.com/embed/([A-Za-z0-9_-]{6,})",
]


def youtube_video_id(url: str) -> str | None:
    for pat in _YT_PATTERNS:
        m = re.search(pat, url)
        if m:
            return m.group(1)
    # Bare id?
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", url.strip()):
        return url.strip()
    return None


def transcribe_youtube(url: str) -> list[dict]:
    vid = youtube_video_id(url)
    if not vid:
        raise TranscribeError("Couldn't parse a YouTube video id from that URL.")
    try:
        return fetch_transcript(vid)
    except YouTubeError as e:
        raise TranscribeError(str(e)) from e


def transcribe_file(path: str, model_size: str = "base") -> list[dict]:
    """Transcribe a local audio/video file with faster-whisper (if installed)."""
    try:
        from faster_whisper import WhisperModel
    except ImportError as e:
        raise TranscribeError(
            "File transcription needs faster-whisper. Install it with "
            "`pip install faster-whisper`, or use the YouTube-URL option."
        ) from e
    try:
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        segments, _ = model.transcribe(path)
        return [{"text": s.text, "start": s.start, "duration": s.end - s.start} for s in segments]
    except Exception as e:  # model download / decode errors
        raise TranscribeError(f"Transcription failed: {e}") from e
