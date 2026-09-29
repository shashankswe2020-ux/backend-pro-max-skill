"""Regression checks for retrieval measurement, not model quality claims."""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest
from backendpro.scripts import benchmark


def test_perfect_metrics():
    assert benchmark.ranking_metrics(["A", "B"], ["A", "B"], 2) == {"recall": 1, "mrr": 1, "ndcg": 1}


def test_partial_metrics_and_rank_discount():
    metrics = benchmark.ranking_metrics(["wrong", "A"], ["A", "B"], 2)
    assert metrics["recall"] == 0.5
    assert metrics["mrr"] == 0.5
    assert metrics["ndcg"] == pytest.approx((1 / math.log2(3)) / (1 + 1 / math.log2(3)))


def test_duplicate_results_do_not_inflate_recall():
    metrics = benchmark.ranking_metrics(["A", "A"], ["A", "B"], 2)
    assert metrics["recall"] == 0.5


def test_cutoff_and_no_matches():
    assert benchmark.ranking_metrics(["wrong", "A"], ["A"], 1) == {"recall": 0, "mrr": 0, "ndcg": 0}


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
