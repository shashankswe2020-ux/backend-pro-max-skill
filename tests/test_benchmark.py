"""Regression checks for retrieval measurement, not model quality claims."""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest
from backendpro.scripts import benchmark


def test_perfect_metrics():
    assert benchmark.ranking_metrics(["A", "B"], ["A", "B"], 2) == {"recall": 1, "precision": 1, "mrr": 1, "ndcg": 1}


def test_partial_metrics_and_rank_discount():
    metrics = benchmark.ranking_metrics(["wrong", "A"], ["A", "B"], 2)
    assert metrics["recall"] == 0.5
    assert metrics["mrr"] == 0.5
    assert metrics["ndcg"] == pytest.approx((1 / math.log2(3)) / (1 + 1 / math.log2(3)))


def test_duplicate_results_do_not_inflate_recall():
    metrics = benchmark.ranking_metrics(["A", "A"], ["A", "B"], 2)
    assert metrics["recall"] == 0.5


def test_cutoff_and_no_matches():
    assert benchmark.ranking_metrics(["wrong", "A"], ["A"], 1) == {"recall": 0, "precision": 0, "mrr": 0, "ndcg": 0}


def test_unknown_labels_fail():
    with pytest.raises(ValueError, match="Unknown relevant rows"):
        benchmark.validate_cases([{"query": "x", "domain": "pattern", "relevant": ["missing"]}])


def test_empty_dataset_fails():
    with pytest.raises(ValueError, match="At least one"):
        benchmark.evaluate([])


def test_bm25_diagnostic_runs():
    dataset = json.loads(Path(__file__).with_name("retrieval-benchmark.json").read_text())
    report = benchmark.evaluate(dataset["queries"], modes=["bm25"], repeats=1)
    assert len(report["modes"]["bm25"]["queries"]) == 8
    for metric in ("recall", "mrr", "ndcg"):
        assert 0 <= report["modes"]["bm25"][metric] <= 1


def test_model_benchmark_refuses_silent_fallback(monkeypatch):
    monkeypatch.setattr(benchmark.semantic, "_get_model", lambda: None)
    with pytest.raises(RuntimeError, match="must not silently fall back"):
        benchmark.evaluate([{"query": "saga", "domain": "pattern", "relevant": ["Saga"]}], modes=["hybrid"])


def test_precision_denominator_is_requested_k_not_number_of_returned_rows():
    assert benchmark.ranking_metrics(["A"], ["A"], 5)["precision"] == .2


def test_unanswerable_abstention_is_reported_separately():
    result = benchmark.evaluate([
        {"query": "saga", "domain": "pattern", "relevant": ["Saga"]},
        {"query": "zzzz-not-a-term-qqq", "domain": "auth", "relevant": [], "answerable": False},
    ], modes=["bm25-no-expand", "bm25"], repeats=1)
    for mode in result["modes"].values():
        assert mode["answerable_cases"] == mode["unanswerable_cases"] == 1
        assert mode["false_no_match_rate"] == 0
        assert mode["unanswerable_abstention_rate"] == 1
    assert not result["quality_gates_demonstrated"]


def test_benchmark_measures_shared_pipeline(monkeypatch):
    original = benchmark.core.search
    calls = []
    def search(*args, **kwargs):
        calls.append(kwargs)
        return original(*args, **kwargs)
    monkeypatch.setattr(benchmark.core, "search", search)
    benchmark.evaluate([{"query": "saga", "domain": "pattern", "relevant": ["Saga"]}],
                       modes=["bm25"], top_k=5, candidates=50, repeats=1)
    assert all(call["max_results"] == 5 and call["candidate_pool"] == 50 for call in calls)


def test_benchmark_runtime_fallback_blocks_report(monkeypatch):
    original = benchmark.core.search
    def search(*args, **kwargs):
        result = original(*args, **kwargs)
        result["retrieval"]["fallbacks"] = ["fixture failure"]
        return result
    monkeypatch.setattr(benchmark.core, "search", search)
    with pytest.raises(RuntimeError, match="must not silently fall back"):
        benchmark.evaluate([{"query": "saga", "domain": "pattern", "relevant": ["Saga"]}], modes=["bm25"])
