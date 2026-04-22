"""
Optional semantic search module for Backend Pro Max.

Provides embedding-based search and reciprocal rank fusion (RRF) with BM25.
Requires `sentence-transformers` (install via `pip install backendpro[semantic]`).

Falls back gracefully to BM25 when dependencies are not installed.
"""
from __future__ import annotations

import hashlib
import json
import os
import pickle
import sys
from pathlib import Path
from typing import Any

# Lazy-loaded optional deps
_sentence_transformers = None
_np = None
_model = None

_CACHE_DIR = Path(os.environ.get("BACKENDPRO_CACHE_DIR", "")) or (Path.home() / ".backendpro_cache")
_MODEL_NAME = "all-MiniLM-L6-v2"

# Embedding index cache: {cache_key: {"embeddings": ndarray, "texts": list}}
_EMBED_CACHE: dict[str, Any] = {}


def is_available() -> bool:
    """Check if sentence-transformers is installed."""
    try:
        import sentence_transformers  # noqa: F401
        return True
    except ImportError:
        return False


def _load_deps():
    """Lazy-load sentence_transformers and numpy."""
    global _sentence_transformers, _np
    if _sentence_transformers is not None:
        return True
    try:
        import numpy as np
        import sentence_transformers as st
        _sentence_transformers = st
        _np = np
        return True
    except ImportError:
        return False


def _get_model():
    """Lazy-load the sentence-transformer model."""
    global _model
    if _model is not None:
        return _model
    if not _load_deps():
        return None
    _model = _sentence_transformers.SentenceTransformer(_MODEL_NAME)
    return _model


def _cache_key(filepath: Path, search_cols: list[str]) -> str:
    """Generate a cache key from filepath + mtime + column list."""
    try:
        mtime = str(filepath.stat().st_mtime)
    except OSError:
        mtime = "0"
    raw = f"{filepath}:{mtime}:{','.join(search_cols)}"
    return hashlib.md5(raw.encode()).hexdigest()


def _disk_cache_path(key: str) -> Path:
    return _CACHE_DIR / f"embed_{key}.pkl"


def _save_to_disk(key: str, embeddings, texts: list[str]):
    """Persist embeddings to disk cache."""
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(_disk_cache_path(key), "wb") as f:
            pickle.dump({"embeddings": embeddings, "texts": texts}, f)
    except OSError:
        pass  # Non-critical — we can rebuild next time


def _load_from_disk(key: str):
    """Load embeddings from disk cache if available."""
    path = _disk_cache_path(key)
    if not path.exists():
        return None
    try:
        with open(path, "rb") as f:
            return pickle.load(f)  # noqa: S301
    except (OSError, pickle.UnpicklingError, EOFError):
        return None


def build_index(data: list[dict], search_cols: list[str], filepath: Path) -> str | None:
    """Build an embedding index for the given CSV data.

    Returns the cache key, or None if sentence-transformers is not available.
    """
    model = _get_model()
    if model is None:
        return None

    key = _cache_key(filepath, search_cols)

    # Check memory cache
    if key in _EMBED_CACHE:
        return key

    # Check disk cache
    cached = _load_from_disk(key)
    if cached is not None:
        _EMBED_CACHE[key] = cached
        return key

    # Build from scratch
    print("Building semantic index…", file=sys.stderr)
    texts = [" ".join(str(row.get(col, "")) for col in search_cols) for row in data]
    embeddings = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
    _EMBED_CACHE[key] = {"embeddings": embeddings, "texts": texts}
    _save_to_disk(key, embeddings, texts)
    return key


def semantic_search(query: str, cache_key: str, top_k: int = 20) -> list[tuple[int, float]]:
    """Search by embedding similarity.

    Returns list of (index, cosine_similarity_score) sorted descending.
    """
    model = _get_model()
    if model is None or cache_key not in _EMBED_CACHE:
        return []

    cached = _EMBED_CACHE[cache_key]
    embeddings = cached["embeddings"]

    query_embedding = model.encode([query], show_progress_bar=False, convert_to_numpy=True)[0]

    # Cosine similarity
    norms = _np.linalg.norm(embeddings, axis=1) * _np.linalg.norm(query_embedding)
    norms = _np.where(norms == 0, 1, norms)  # avoid division by zero
    scores = _np.dot(embeddings, query_embedding) / norms

    # Top-K indices
    top_indices = _np.argsort(scores)[::-1][:top_k]
    return [(int(idx), float(scores[idx])) for idx in top_indices if scores[idx] > 0]


def reciprocal_rank_fusion(
    bm25_ranking: list[tuple[int, float]],
    embed_ranking: list[tuple[int, float]],
    k: int = 60,
) -> list[tuple[int, float]]:
    """Merge BM25 and embedding rankings using Reciprocal Rank Fusion.

    RRF score = sum(1 / (k + rank)) across ranking lists.
    k=60 is the standard constant from Cormack et al. (2009).
    """
    rrf_scores: dict[int, float] = {}

    for rank, (idx, _score) in enumerate(bm25_ranking):
        rrf_scores[idx] = rrf_scores.get(idx, 0.0) + 1.0 / (k + rank + 1)

    for rank, (idx, _score) in enumerate(embed_ranking):
        rrf_scores[idx] = rrf_scores.get(idx, 0.0) + 1.0 / (k + rank + 1)

    return sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)


def clear_cache():
    """Clear in-memory embedding cache."""
    _EMBED_CACHE.clear()
