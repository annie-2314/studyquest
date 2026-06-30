"""Persist materials + embedded chunks, and retrieve by cosine similarity.

The "vector store" is just the relational `MaterialChunk` table plus NumPy cosine
ranking — zero-ops, no server, no build tools. It's fronted by `search()` so a
real vector DB (Chroma/Qdrant) could be swapped in behind the same interface.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.config import settings
from app.models.material import Material, MaterialChunk
from app.rag import embeddings

_PGVECTOR = settings.vector_backend == "pgvector"


def _store_value(vec: list[float]):
    # pgvector accepts a Python list directly; numpy backend persists JSON text.
    return vec if _PGVECTOR else json.dumps(vec)


def add_material(db: Session, user_id: str, title: str, chunks: list[dict],
                 kind: str = "text") -> Material:
    """chunks: [{content, page}] — embeds and stores them. Returns the Material."""
    mat = Material(user_id=user_id, title=title, kind=kind)
    db.add(mat)
    db.flush()
    vectors = embeddings.embed_documents([c["content"] for c in chunks])
    for i, (c, vec) in enumerate(zip(chunks, vectors)):
        page = int(c.get("page", 0) or 0)
        source = f"{title} p.{page}" if page else f"{title} ¶{i + 1}"
        db.add(MaterialChunk(
            material_id=mat.id, ordinal=i, content=c["content"], page=page,
            source=source, concept_tags=c.get("concept_tags", ""),
            embedding=_store_value(vec),
        ))
    db.commit()
    db.refresh(mat)
    return mat


def _cosine_topk(query_vec, rows: list[MaterialChunk], k: int):
    import numpy as np

    if not rows:
        return []
    q = np.asarray(query_vec, dtype="float32")
    qn = np.linalg.norm(q) or 1.0
    mat = np.asarray([json.loads(r.embedding) for r in rows], dtype="float32")
    mn = np.linalg.norm(mat, axis=1)
    mn[mn == 0] = 1.0
    scores = (mat @ q) / (mn * qn)
    order = np.argsort(-scores)[:k]
    return [(rows[i], float(scores[i])) for i in order]


def _search_pgvector(db: Session, user_id: str, query: str, k: int, material_id):
    """Top-k via pgvector's cosine distance operator (`<=>`), pushed to Postgres."""
    from sqlalchemy import select

    qvec = embeddings.embed_query(query)
    dist = MaterialChunk.embedding.cosine_distance(qvec).label("dist")
    stmt = (select(MaterialChunk, dist).join(Material)
            .where(Material.user_id == user_id))
    if material_id:
        stmt = stmt.where(MaterialChunk.material_id == material_id)
    stmt = stmt.order_by(dist).limit(k)
    # cosine_distance ∈ [0,2] (0 = identical) → similarity score = 1 - dist.
    return [(row[0], 1.0 - float(row[1])) for row in db.execute(stmt).all()]


def search(db: Session, user_id: str, query: str, k: int = 4,
           material_id: str | None = None) -> list[tuple[MaterialChunk, float]]:
    """Top-k (chunk, score) for the user, optionally scoped to one material."""
    if _PGVECTOR:
        return _search_pgvector(db, user_id, query, k, material_id)
    q = db.query(MaterialChunk).join(Material).filter(Material.user_id == user_id)
    if material_id:
        q = q.filter(MaterialChunk.material_id == material_id)
    rows = q.all()
    if not rows:
        return []
    return _cosine_topk(embeddings.embed_query(query), rows, k)
