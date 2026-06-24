"""Chunking + BM25 retrieval over a user's stored documents.

Deliberately dependency-light: chunk on paragraphs/length, rank with BM25 built
on the fly. Fine for the demo-scale corpora here; swap in Qdrant/pgvector later
behind this same `search()` interface without touching callers.
"""
from __future__ import annotations

import re

from rank_bm25 import BM25Okapi
from sqlalchemy.orm import Session

from app.models.rag import DocChunk, Document

_WORD = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _WORD.findall(text.lower())


def chunk_text(text: str, max_chars: int = 600) -> list[str]:
    """Split into ~max_chars chunks on paragraph boundaries."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    buf = ""
    for p in paras:
        if len(buf) + len(p) + 2 <= max_chars:
            buf = f"{buf}\n\n{p}".strip()
        else:
            if buf:
                chunks.append(buf)
            # A single oversized paragraph gets hard-split.
            while len(p) > max_chars:
                chunks.append(p[:max_chars])
                p = p[max_chars:]
            buf = p
    if buf:
        chunks.append(buf)
    return chunks or [text.strip()]


def add_document(db: Session, user_id: str, title: str, text: str,
                 kind: str = "text", source_prefix: str = "") -> Document:
    """Store a document and its chunks. Returns the Document."""
    doc = Document(user_id=user_id, title=title, kind=kind)
    db.add(doc)
    db.flush()  # get doc.id before adding chunks
    for i, c in enumerate(chunk_text(text)):
        ref = f"{source_prefix}#{i}" if source_prefix else f"{title} ¶{i + 1}"
        db.add(DocChunk(document_id=doc.id, ordinal=i, content=c, source_ref=ref))
    db.commit()
    db.refresh(doc)
    return doc


def search(db: Session, user_id: str, query: str, k: int = 4,
           document_id: str | None = None) -> list[DocChunk]:
    """Return the top-k most relevant chunks for the user (optionally scoped to
    one document) using BM25."""
    q = db.query(DocChunk).join(Document).filter(Document.user_id == user_id)
    if document_id:
        q = q.filter(DocChunk.document_id == document_id)
    chunks = q.all()
    if not chunks:
        return []
    corpus = [_tokenize(c.content) for c in chunks]
    bm25 = BM25Okapi(corpus)
    scores = bm25.get_scores(_tokenize(query))
    ranked = sorted(zip(chunks, scores), key=lambda cs: cs[1], reverse=True)
    return [c for c, s in ranked[:k] if s > 0] or [ranked[0][0]]
