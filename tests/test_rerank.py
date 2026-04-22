"""Tests for cross-encoder re-ranking (Tier 2 — Task 2.3).

Tests that require sentence-transformers/CrossEncoder are skipped if not installed.
"""
from __future__ import annotations

import pytest

try:
    from sentence_transformers import CrossEncoder  # noqa: F401
    HAS_CE = True
except ImportError:
    HAS_CE = False

needs_ce = pytest.mark.skipif(not HAS_CE, reason="sentence-transformers (CrossEncoder) not installed")


class TestRerankModule:
    """Unit tests for rerank module."""

    def test_is_available_matches_import(self):
        from rerank import is_available
        assert is_available() == HAS_CE

    def test_rerank_empty_rows(self):
        from rerank import rerank
        result = rerank("test query", [])
        assert result == []

    def test_rerank_without_deps_returns_original_order(self):
        """Without cross-encoder, rerank should return rows unchanged (truncated to top_k)."""
        if HAS_CE:
            pytest.skip("CrossEncoder is installed — this test is for missing-deps path")
        from rerank import rerank
        rows = [
            {"Name": "A", "_score": 5.0},
            {"Name": "B", "_score": 4.0},
            {"Name": "C", "_score": 3.0},
        ]
        result = rerank("test", rows, top_k=2)
        assert len(result) == 2
        assert result[0]["Name"] == "A"


@needs_ce
class TestRerankWithCrossEncoder:
    """Integration tests when cross-encoder IS installed."""

    def test_rerank_adds_score(self):
        from rerank import rerank
        rows = [
            {"Name": "Circuit Breaker", "Category": "Resilience", "_score": 5.0},
            {"Name": "Saga", "Category": "Transaction", "_score": 4.0},
            {"Name": "Retry", "Category": "Resilience", "_score": 3.0},
        ]
        result = rerank("resilience pattern for failures", rows, top_k=3)
        assert len(result) <= 3
        assert all("_rerank_score" in r for r in result)
        # Results should be sorted by _rerank_score descending
        scores = [r["_rerank_score"] for r in result]
        assert scores == sorted(scores, reverse=True)

    def test_rerank_top_k_limits(self):
        from rerank import rerank
        rows = [{"Name": f"Item{i}", "_score": float(10 - i)} for i in range(10)]
        result = rerank("test query", rows, top_k=3)
        assert len(result) == 3
