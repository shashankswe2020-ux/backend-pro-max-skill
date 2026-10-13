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
import sys
from pathlib import Path
from typing import Any

# Lazy-loaded optional deps
_sentence_transformers = None
_np = None
_model = None
_model_identity = None

_CACHE_DIR = Path(os.environ.get("BACKENDPRO_CACHE_DIR") or (Path.home() / ".backendpro_cache"))
_MODEL_NAME = "all-MiniLM-L6-v2"
_MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"

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
    global _model, _model_identity
    identity = (_MODEL_NAME, _MODEL_REVISION)
    if _model is not None and _model_identity == identity:
        return _model
    if not _load_deps():
        return None
    _model = _sentence_transformers.SentenceTransformer(
        model_snapshot(f"sentence-transformers/{_MODEL_NAME}", _MODEL_REVISION),
    )
    _model_identity = identity
    return _model


def model_snapshot(name: str, revision: str) -> str:
    """Resolve pinned data files without relying on version-specific model constructors."""
    from huggingface_hub import snapshot_download

    return snapshot_download(
        repo_id=name, revision=revision,
        allow_patterns=["*.json", "*.txt", "*.safetensors", "pytorch_model.bin", "*.model"],
        ignore_patterns=["onnx/*", "openvino/*"],
    )


def _cache_key(filepath: Path, search_cols: list[str]) -> str:
    """Bind row order and searchable fields to corpus content and the pinned model."""
    identity = {
        "format": "embeddings-v2", "corpus_sha256": hashlib.sha256(filepath.read_bytes()).hexdigest(),
        "columns": search_cols, "model": _MODEL_NAME, "revision": _MODEL_REVISION,
    }
    return hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()


def _disk_cache_path(key: str, ext: str = ".json") -> Path:
    return _CACHE_DIR / f"embed_{key}{ext}"


def _save_to_disk(key: str, embeddings, texts: list[str]):
    """Persist embeddings to disk cache using numpy + JSON (no pickle)."""
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
        # Save embeddings as .npy (numpy binary, no pickle)
        npy_path = _disk_cache_path(key, ".npy")
        _np.save(str(npy_path), embeddings)
        # Save texts as JSON
        json_path = _disk_cache_path(key, ".json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(texts, f)
    except OSError as error:
        print(f"Warning: cannot persist embedding cache: {error}", file=sys.stderr)


def _load_from_disk(key: str):
    """Load embeddings from disk cache if available (numpy + JSON)."""
    npy_path = _disk_cache_path(key, ".npy")
    json_path = _disk_cache_path(key, ".json")
    if not npy_path.exists() or not json_path.exists():
        return None
    try:
        if not _load_deps():
            return None
        embeddings = _np.load(str(npy_path), allow_pickle=False)
        with open(json_path, encoding="utf-8") as f:
            texts = json.load(f)
        if (
            not isinstance(texts, list) or not all(isinstance(text, str) for text in texts)
            or embeddings.ndim != 2 or embeddings.shape[0] != len(texts)
            or embeddings.dtype.kind != "f" or not _np.isfinite(embeddings).all()
        ):
            raise ValueError("Embedding cache shape or content is invalid")
        return {"embeddings": embeddings, "texts": texts}
    except (OSError, ValueError, EOFError) as error:
        print(f"Warning: invalid embedding cache; rebuilding: {error}", file=sys.stderr)
        return None


def build_index(data: list[dict], search_cols: list[str], filepath: Path) -> str | None:
    """Build an embedding index for the given CSV data.

    Returns the cache key, or None if sentence-transformers is not available.
    """
    model = _get_model()
    if model is None:
        return None

    texts = [" ".join(str(row.get(col, "")) for col in search_cols) for row in data]
    # Opt-in source supplements share a CSV path but must never reuse its base-only vectors.
    key = hashlib.sha256(
        (_cache_key(filepath, search_cols) + json.dumps(texts, ensure_ascii=False)).encode("utf-8")
    ).hexdigest()

    # Check memory cache
    if key in _EMBED_CACHE:
        return key

    # Check disk cache
    cached = _load_from_disk(key)
    if cached is not None and cached["texts"] == texts:
        _EMBED_CACHE[key] = cached
        return key
    if cached is not None:
        print("Warning: embedding cache text mismatch; rebuilding.", file=sys.stderr)

    # Build from scratch
    print("Building semantic index…", file=sys.stderr)
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
        raise RuntimeError("Semantic search requires a loaded model and valid index")

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
