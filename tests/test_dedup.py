"""Tests for the dedup module — near-duplicate detection."""
from __future__ import annotations

import core
from dedup import (
    _is_allowlisted,
    _search_text,
    find_duplicates_bm25,
    find_duplicates_cross_domain,
    format_duplicates,
    format_duplicates_json,
)


def test_find_duplicates_returns_list():
    """Dedup on any domain returns a list (possibly empty)."""
    core.clear_cache()
    result = find_duplicates_bm25("pattern", threshold=0.85)
    assert isinstance(result, list)


def test_find_duplicates_high_threshold_returns_fewer():
    """Higher threshold should return same or fewer results."""
    core.clear_cache()
    low = find_duplicates_bm25("pattern", threshold=0.5)
    high = find_duplicates_bm25("pattern", threshold=0.95)
    assert len(high) <= len(low)


def test_find_duplicates_unknown_domain_returns_empty():
    result = find_duplicates_bm25("nonexistent-domain", threshold=0.5)
    assert result == []


def test_find_duplicates_result_shape():
    """Each duplicate entry has required keys."""
    core.clear_cache()
    result = find_duplicates_bm25("pattern", threshold=0.5)
    for entry in result:
        assert "row_a" in entry
        assert "row_b" in entry
        assert "similarity" in entry
        assert "domain" in entry
        assert 0 <= entry["similarity"] <= 1.1  # allow small float rounding


def test_cross_domain_returns_list():
    core.clear_cache()
    result = find_duplicates_cross_domain(threshold=0.95)
    assert isinstance(result, list)


def test_cross_domain_result_shape():
    core.clear_cache()
    result = find_duplicates_cross_domain(threshold=0.7)
    for entry in result:
        assert "row_a" in entry
        assert "row_b" in entry
        assert "domain_a" in entry
        assert "domain_b" in entry
        assert entry["domain_a"] != entry["domain_b"]


def test_allowlist_suppresses_pairs():
    allowlist = {("circuit breaker", "circuit breaker")}
    assert _is_allowlisted("Circuit Breaker", "circuit breaker", allowlist)
    assert not _is_allowlisted("Saga", "CQRS", allowlist)


def test_format_duplicates_no_dupes():
    assert "No near-duplicates" in format_duplicates([])


def test_format_duplicates_with_entries():
    entries = [{"row_a": "A", "row_b": "B", "similarity": 0.9, "domain": "test"}]
    output = format_duplicates(entries)
    assert "A" in output and "B" in output


def test_format_duplicates_json():
    entries = [{"row_a": "A", "row_b": "B", "similarity": 0.9, "domain": "test"}]
    output = format_duplicates_json(entries)
    import json
    parsed = json.loads(output)
    assert parsed["count"] == 1
    assert len(parsed["duplicates"]) == 1


def test_search_text_extracts_search_cols():
    """_search_text should concatenate search column values."""
    core.clear_cache()
    row = {"Name": "Test", "Category": "Cat", "Problem": "Prob", "Keywords": "kw", "When to Use": "wu"}
    text = _search_text(row, "pattern")
    assert "Test" in text
    assert "Cat" in text
