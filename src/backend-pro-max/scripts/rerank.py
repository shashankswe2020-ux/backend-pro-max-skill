"""
Optional cross-encoder re-ranking for Backend Pro Max.

Takes BM25 top-K results and re-scores them using a cross-encoder model
to evaluate precision on ambiguous queries.

Requires `sentence-transformers` (install via `pip install backendpro[rerank]`).
Falls back gracefully when not installed.
"""
from __future__ import annotations

import sys
from math import isfinite

try:
    from .semantic import model_snapshot
except ImportError:
    from semantic import model_snapshot

_cross_encoder = None
_model_identity = None
_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"
_MODEL_REVISION = "233902d25c440f23af6f7d6e94d2946bac0bee0a"


def is_available() -> bool:
    """Check if the cross-encoder can be loaded."""
    try:
        from sentence_transformers import CrossEncoder  # noqa: F401
        return True
    except ImportError:
        return False


def _get_model():
    """Lazy-load the cross-encoder model."""
    global _cross_encoder, _model_identity
    identity = (_MODEL_NAME, _MODEL_REVISION)
    if _cross_encoder is not None and _model_identity == identity:
        return _cross_encoder
    try:
        from sentence_transformers import CrossEncoder
    except ImportError:
        return None
    _cross_encoder = CrossEncoder(model_snapshot(_MODEL_NAME, _MODEL_REVISION))
    _model_identity = identity
    return _cross_encoder


def rerank(query: str, rows: list[dict], top_k: int = 5,
           text_key: str | None = None, *, strict: bool = False) -> list[dict]:
    """Re-rank rows using a cross-encoder.

    Args:
        query: The search query.
        rows: List of result dicts from BM25 search.
        top_k: Number of results to return after re-ranking.
        text_key: Key to use for the text representation of each row.
                  If None, concatenates all non-score values.

    Returns:
        Re-ranked list of rows with `_rerank_score` added.
        If the cross-encoder is not available, returns rows unchanged
        with a warning printed to stderr.
    """
    if not rows:
        return []
    model = _get_model()
    if model is None:
        if strict:
            raise RuntimeError("Reranker unavailable after capability check")
        print(
            "ℹ️  Cross-encoder not installed — returning BM25 results. "
            "Install with: pip install backendpro[rerank]",
            file=sys.stderr,
        )
        return rows[:top_k]

    # Build text pairs for cross-encoder
    pairs = []
    for row in rows:
        if text_key and text_key in row:
            text = str(row[text_key])
        else:
            text = " ".join(
                str(v).strip() for k, v in row.items()
                if not k.startswith("_") and str(v).strip()
            )
        pairs.append((query, text))

    scores = model.predict(pairs)
    if len(scores) != len(rows) or any(not isfinite(float(score)) for score in scores):
        raise ValueError("Reranker returned an invalid number of finite scores")

    # Attach scores and sort
    scored_rows = []
    for row, score in zip(rows, scores):
        row_copy = dict(row)
        row_copy["_rerank_score"] = round(float(score), 4)
        scored_rows.append(row_copy)

    scored_rows.sort(key=lambda r: r["_rerank_score"], reverse=True)
    return scored_rows[:top_k]
