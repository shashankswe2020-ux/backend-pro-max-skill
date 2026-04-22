"""
Optional cross-encoder re-ranking for Backend Pro Max.

Takes BM25 top-K results and re-scores them using a cross-encoder model
for dramatically improved precision on ambiguous queries.

Requires `sentence-transformers` (install via `pip install backendpro[rerank]`).
Falls back gracefully when not installed.
"""
from __future__ import annotations

import sys
from typing import Any

_cross_encoder = None
_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"


def is_available() -> bool:
    """Check if the cross-encoder can be loaded."""
    try:
        from sentence_transformers import CrossEncoder  # noqa: F401
        return True
    except ImportError:
        return False


def _get_model():
    """Lazy-load the cross-encoder model."""
    global _cross_encoder
    if _cross_encoder is not None:
        return _cross_encoder
    try:
        from sentence_transformers import CrossEncoder
        _cross_encoder = CrossEncoder(_MODEL_NAME)
        return _cross_encoder
    except ImportError:
        return None


def rerank(query: str, rows: list[dict], top_k: int = 5,
           text_key: str | None = None) -> list[dict]:
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
    model = _get_model()
    if model is None:
        print(
            "ℹ️  Cross-encoder not installed — returning BM25 results. "
            "Install with: pip install backendpro[rerank]",
            file=sys.stderr,
        )
        return rows[:top_k]

    if not rows:
        return []

    # Build text pairs for cross-encoder
    pairs = []
    for row in rows:
        if text_key and text_key in row:
            text = str(row[text_key])
        else:
            text = " ".join(
                str(v).strip() for k, v in row.items()
                if k not in ("_score", "_constraints", "_rerank_score") and str(v).strip()
            )
        pairs.append((query, text))

    scores = model.predict(pairs)

    # Attach scores and sort
    scored_rows = []
    for row, score in zip(rows, scores):
        row_copy = dict(row)
        row_copy["_rerank_score"] = round(float(score), 4)
        scored_rows.append(row_copy)

    scored_rows.sort(key=lambda r: r["_rerank_score"], reverse=True)
    return scored_rows[:top_k]
