"""Ingestion for grounded RAG: PDF / pasted text → token-aware chunks.

We approximate tokens as words (~0.75 word/token), so ~500 tokens ≈ ~380 words,
with ~50-token (~40-word) overlap so a concept that straddles a boundary is still
retrievable. Each chunk records its source page for citations.
"""
from __future__ import annotations

import re

_WORDS_PER_CHUNK = 380      # ~500 tokens
_OVERLAP_WORDS = 40         # ~50 tokens


def _chunk_words(text: str, page: int) -> list[dict]:
    words = text.split()
    if not words:
        return []
    chunks: list[dict] = []
    step = _WORDS_PER_CHUNK - _OVERLAP_WORDS
    for start in range(0, len(words), step):
        piece = " ".join(words[start:start + _WORDS_PER_CHUNK]).strip()
        if piece:
            chunks.append({"content": piece, "page": page})
        if start + _WORDS_PER_CHUNK >= len(words):
            break
    return chunks


def chunk_text(text: str) -> list[dict]:
    """Chunk pasted text into [{content, page}] (page 0 — no pagination)."""
    # Respect paragraph breaks loosely by normalising whitespace first.
    text = re.sub(r"[ \t]+", " ", text).strip()
    return _chunk_words(text, page=0)


def chunk_pdf(data: bytes) -> list[dict]:
    """Extract text per page from a PDF and chunk it, tagging each chunk's page."""
    import fitz  # PyMuPDF

    out: list[dict] = []
    with fitz.open(stream=data, filetype="pdf") as doc:
        for pno in range(doc.page_count):
            page_text = doc.load_page(pno).get_text("text")
            out.extend(_chunk_words(re.sub(r"[ \t]+", " ", page_text).strip(), page=pno + 1))
    return out
