"""Free local text embeddings for grounded RAG.

Real path: `fastembed` running BAAI/bge-small-en-v1.5 as ONNX (no PyTorch, no
build tools — onnxruntime is already a dependency). The model file (~130 MB)
downloads on first use and is then cached.

Mock path: a deterministic hash-bag embedding with the SAME dimensionality, used
when EMBEDDINGS_MOCK=1 (tests/offline) or if fastembed isn't importable. It needs
no network, so the test suite never downloads a model, and cosine similarity over
it still rewards keyword overlap — enough to exercise the retrieval/citation path.
"""
from __future__ import annotations

import hashlib
import os
import re

DIM = 384  # bge-small-en-v1.5 output dim (kept identical for the mock)
_MODEL_NAME = "BAAI/bge-small-en-v1.5"

_model = None  # cached fastembed model


def _use_mock() -> bool:
    if os.getenv("EMBEDDINGS_MOCK") == "1":
        return True
    try:
        import fastembed  # noqa: F401
        return False
    except Exception:
        return True


def _mock_vector(text: str) -> list[float]:
    import numpy as np

    v = np.zeros(DIM, dtype="float32")
    for tok in re.findall(r"[a-z0-9]+", text.lower()):
        idx = int(hashlib.md5(tok.encode()).hexdigest(), 16) % DIM
        v[idx] += 1.0
    norm = float(np.linalg.norm(v))
    return (v / norm).tolist() if norm else v.tolist()


def _get_model():
    global _model
    if _model is None:
        from fastembed import TextEmbedding
        _model = TextEmbedding(model_name=_MODEL_NAME)
    return _model


def embed_documents(texts: list[str]) -> list[list[float]]:
    """Embed a list of passages."""
    if not texts:
        return []
    if _use_mock():
        return [_mock_vector(t) for t in texts]
    return [list(map(float, vec)) for vec in _get_model().embed(texts)]


def embed_query(text: str) -> list[float]:
    """Embed a single search query."""
    if _use_mock():
        return _mock_vector(text)
    # fastembed exposes query_embed for query-side encoding (bge query prefix).
    return [list(map(float, v)) for v in _get_model().query_embed([text])][0]
