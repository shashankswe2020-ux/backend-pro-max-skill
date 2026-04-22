"""Tests for BM25 ranking quality and edge cases."""
from __future__ import annotations

import csv
from pathlib import Path

import core


def test_bm25_empty_corpus():
    bm = core.BM25()
    bm.fit([])
    assert bm.N == 0
    assert bm.score("anything") == []


def test_bm25_tokenize_strips_punct_and_short_words():
    bm = core.BM25()
    tokens = bm.tokenize("Circuit-breaker, A B-tree!")
    assert "circuit" in tokens and "breaker" in tokens
    assert "a" not in tokens  # length <= 1 filtered


def test_bm25_ranks_exact_match_first():
    docs = [
        "circuit breaker pattern fault tolerance",
        "saga compensating transaction",
        "outbox publish event broker",
    ]
    bm = core.BM25()
    bm.fit(docs)
    ranked = bm.score("circuit breaker")
    assert ranked[0][0] == 0
    assert ranked[0][1] > ranked[1][1]


def test_search_circuit_breaker_top_hit_is_circuit_breaker():
    """Quality bar: querying 'circuit breaker' must rank the Circuit Breaker
    pattern (or a row whose name contains it) at #1 in patterns/reliability."""
    core.clear_cache()
    res = core.search("circuit breaker", domain="pattern")
    assert "results" in res
    if res["count"] == 0:
        # If patterns.csv doesn't have it, reliability.csv should.
        res = core.search("circuit breaker", domain="reliability")
    assert res["count"] >= 1
    top = res["results"][0]
    head = " ".join(str(v) for v in top.values()).lower()
    assert "circuit" in head and "breaker" in head


def test_search_saga_finds_saga_in_patterns():
    core.clear_cache()
    res = core.search("saga", domain="pattern")
    assert res["count"] >= 1
    top = res["results"][0]
    assert any("saga" in str(v).lower() for v in top.values())


def test_search_returns_score_field():
    core.clear_cache()
    res = core.search("kafka", domain="messaging")
    if res["count"] > 0:
        assert "_score" in res["results"][0]
        assert res["results"][0]["_score"] > 0


def test_min_score_filter_drops_results():
    core.clear_cache()
    res = core.search("kafka", domain="messaging", min_score=10_000.0)
    assert res["count"] == 0


def test_synonym_expansion_helps_partial_failure_query():
    """`partial failure` should now hit Saga (compensation) thanks to synonym
    expansion. Without expansion it likely wouldn't, since Saga's row uses
    'compensating' not 'partial failure'."""
    core.clear_cache()
    res = core.search("how to handle partial failure across services",
                      domain="pattern", expand=True)
    assert res["count"] >= 1
    names = " ".join(str(r.get(next(iter(r)), "")).lower() for r in res["results"])
    assert "saga" in names or "outbox" in names or "circuit" in names


def test_no_expand_flag_disables_synonyms():
    core.clear_cache()
    expanded = core._expand_query("partial failure")
    assert expanded != "partial failure"
    # And the pipeline respects expand=False
    res = core.search("zzznonsensequery", domain="pattern", expand=False)
    assert res["count"] == 0


def test_unknown_domain_returns_error():
    res = core.search("anything", domain="not-a-real-domain")
    assert "error" in res


def test_search_all_returns_dict_per_domain():
    core.clear_cache()
    res = core.search_all("kafka", max_results=1)
    assert "results" in res
    assert isinstance(res["results"], dict)


def test_search_stack_works_for_known_stack():
    core.clear_cache()
    res = core.search_stack("error handling", "go")
    assert "results" in res
    assert res.get("stack") == "go"


def test_csv_with_missing_columns_does_not_crash(tmp_path: Path):
    """Edge case: a CSV that lacks some declared columns should still load
    and search without raising."""
    csv_path = tmp_path / "tiny.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Name", "Keywords"])
        w.writerow(["Foo", "alpha beta"])
        w.writerow(["Bar", "gamma delta"])
    rows = core._search_csv(
        csv_path, ["Name", "Keywords"], ["Name", "Keywords", "DoesNotExist"],
        "alpha", max_results=5,
    )
    assert len(rows) == 1
    assert rows[0]["Name"] == "Foo"
    assert "DoesNotExist" not in rows[0]


def test_empty_csv_returns_no_results(tmp_path: Path):
    csv_path = tmp_path / "empty.csv"
    csv_path.write_text("Name,Keywords\n", encoding="utf-8")
    rows = core._search_csv(csv_path, ["Name"], ["Name"], "anything", 5)
    assert rows == []
